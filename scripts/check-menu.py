#!/usr/bin/env python3
"""Check the launcher menu overrides in profile/airootfs/usr/local/share/applications (stdlib only).

Every file there is either the hidden Calamares override or a "hide stub": same desktop file id
as the stock entry, NoDisplay=true, Hidden=true, no Exec (so it cannot drift from the package).

Always: stub shape; a hidden id is not a default application in mimeapps.list and not a dock pin.
With --require-file-db (CI, after `pacman -Fy`): the id is shipped by an official package, so a
stub for an entry that no longer exists fails instead of rotting.
"""
import glob
import importlib.util
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "profile", "airootfs", "usr", "local", "share", "applications")
NOT_STUBS = {"calamares.desktop"}   # hidden override with its own rules, checked by check-launchers.py


LAYOUT = os.path.join(ROOT, "profile", "airootfs", "usr", "share", "plasma", "look-and-feel",
                      "org.heiss.%s.desktop", "contents", "layouts", "org.kde.plasma.desktop-layout.js")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def desktop_keys(text):
    """Keys of the [Desktop Entry] group only."""
    out, in_main = {}, False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_main = line == "[Desktop Entry]"
        elif in_main and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out.setdefault(k, v)
    return out


def pinned_ids():
    ids = set()
    for theme in ("dark", "light"):
        with open(LAYOUT % theme, encoding="utf-8") as f:
            m = re.search(r'writeConfig\(\s*"launchers"\s*,\s*\[(.*?)\]\s*\)', f.read(), re.S)
        ids |= {x.split(":", 1)[-1] for x in re.findall(r'"([^"]*)"', m.group(1))} if m else set()
    return ids


def stub_problems(fname, keys):
    problems = []
    if keys.get("Type") != "Application":
        problems.append("%s: Type must be Application" % fname)
    for k in ("NoDisplay", "Hidden"):
        if keys.get(k) != "true":
            problems.append("%s: %s=true is required" % (fname, k))
    if "Exec" in keys:
        problems.append("%s: a hide stub must not have Exec (it would drift from the package)" % fname)
    return problems


def used_ids(mimeapps):
    """Desktop ids that must stay visible: dock pins and default applications."""
    pins = pinned_ids()
    with open(mimeapps.PATH, encoding="utf-8") as f:
        data, _ = mimeapps.parse(f.read())
    return pins | {i for ids in data.values() for i in ids}


def owners(desktop_id):
    r = subprocess.run(["pacman", "-Fx", "--machinereadable", "^usr/share/applications/%s$" % re.escape(desktop_id)],
                       capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
    if r.returncode not in (0, 1):
        return None
    return {line.split("\0")[1] for line in r.stdout.splitlines() if line.count("\0") >= 3}


def main(argv):
    mimeapps = load("check-mimeapps")
    keep = used_ids(mimeapps)
    problems, hidden = [], []
    for path in sorted(glob.glob(os.path.join(DIR, "*.desktop"))):
        fname = os.path.basename(path)
        if fname in NOT_STUBS:
            continue
        with open(path, encoding="utf-8") as f:
            problems += stub_problems(fname, desktop_keys(f.read()))
        hidden.append(fname)
        if fname in keep:
            problems.append("%s is a dock pin or a default application and must stay visible" % fname)
    if "--require-file-db" in argv:
        for fname in hidden:
            pk = owners(fname)
            if pk is None:
                problems.append("pacman file database not available (run pacman -Fy)")
                break
            if not pk:
                problems.append("%s: no official package ships this entry any more, remove the stub" % fname)
            else:
                print("ok  %-34s %s" % (fname, ", ".join(sorted(pk))))
    for p in problems:
        print("PROBLEM:", p)
    print("%d hide stubs" % len(hidden))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
