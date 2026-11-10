#!/usr/bin/env python3
"""Check the dock pins and our own desktop files (stdlib only).

Always:
  * the pinned launchers of the Dark and the Light look-and-feel layouts are the same list,
    every pin is an `applications:<id>.desktop` entry and there are no duplicates;
  * every desktop file we ship that starts Calamares sets StartupWMClass=calamares (so the
    running installer window is matched to ONE entry) and uses an icon we ship;
  * the Calamares override in /usr/local/share/applications is hidden (NoDisplay=true), so
    the menu has one installer entry, not two.

With --require-file-db (CI, archlinux container after `pacman -Fy`): every pinned desktop id is
shipped by a package of the Base profile closure including its dependencies (pacman -F), or is one of our own files.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from heiss_core import manifest as mf  # noqa: E402

AIROOTFS = os.path.join(ROOT, "profile", "airootfs")
LAYOUT = "usr/share/plasma/look-and-feel/org.heiss.%s.desktop/contents/layouts/org.kde.plasma.desktop-layout.js"
OUR_DESKTOP_GLOBS = ["usr/share/applications/*.desktop", "usr/local/share/applications/*.desktop",
                     "home/liveuser/Desktop/*.desktop"]
INSTALLER_ENTRY = "usr/share/applications/heiss-installer.desktop"   # the only visible installer entry


def pins(js_text):
    """The strings of the `launchers` array written for the task manager."""
    m = re.search(r'writeConfig\(\s*"launchers"\s*,\s*\[(.*?)\]\s*\)', js_text, re.S)
    return re.findall(r'"([^"]*)"', m.group(1)) if m else None


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


def shipped_icon(name, airootfs=AIROOTFS):
    return bool(glob.glob(os.path.join(airootfs, "usr/share/icons/hicolor/*/apps/%s.*" % name)))


def pin_problems(dark, light):
    problems = []
    for label, p in (("dark", dark), ("light", light)):
        if p is None:
            problems.append("%s layout: no launchers array found" % label)
            continue
        for item in p:
            if not re.fullmatch(r"applications:[A-Za-z0-9._-]+\.desktop", item):
                problems.append("%s layout: bad pin %r (a comma-joined string is ONE entry)" % (label, item))
        for item in sorted({i for i in p if p.count(i) > 1}):
            problems.append("%s layout: %s is pinned twice" % (label, item))
    if dark is not None and light is not None and dark != light:
        problems.append("dark and light layouts pin different launchers: %s vs %s" % (dark, light))
    return problems


def desktop_problems(relpath, keys, airootfs=AIROOTFS):
    problems = []
    if "calamares" in keys.get("Exec", ""):
        if keys.get("StartupWMClass") != "calamares":
            problems.append("%s: starts Calamares but StartupWMClass is not calamares" % relpath)
        icon = keys.get("Icon", "")
        if not icon or not shipped_icon(icon, airootfs):
            problems.append("%s: icon %r is not shipped in hicolor" % (relpath, icon))
    if relpath.startswith("usr/local/share/applications/") and keys.get("NoDisplay") != "true":
        problems.append("%s: an override in /usr/local/share/applications must be NoDisplay=true "
                        "(otherwise the menu gets a second entry)" % relpath)
    return problems


def owners(desktop_id):
    r = subprocess.run(["pacman", "-Fx", "--machinereadable", "^usr/share/applications/%s$" % re.escape(desktop_id)],
                       capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
    if r.returncode not in (0, 1):
        return None
    return {line.split("\0")[1] for line in r.stdout.splitlines() if line.count("\0") >= 3}


def base_packages():
    """Packages named by the Base closure plus everything they pull in (systemsettings, for
    example, arrives as a dependency of plasma-desktop and is in no manifest)."""
    manifests = mf.load_dir(os.path.join(ROOT, "profiles"))
    named = {p for mid in mf.closure(manifests, ["base"]) for p in manifests[mid].packages}
    return named | dependencies(sorted(named))


def dependencies(names):
    """Names pacman would install for `names` in an empty root, or an empty set if it cannot tell."""
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "db")
        os.makedirs(db)
        os.makedirs(os.path.join(tmp, "root"))
        shutil.copytree("/var/lib/pacman/sync", os.path.join(db, "sync"))
        r = subprocess.run(["pacman", "--root", os.path.join(tmp, "root"), "--dbpath", db, "-Sp", "--print-format", "%n"] + names,
                           capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
    return set(r.stdout.split()) if r.returncode == 0 else set()


def read(rel):
    with open(os.path.join(AIROOTFS, rel), encoding="utf-8") as f:
        return f.read()


def main(argv):
    dark, light = pins(read(LAYOUT % "dark")), pins(read(LAYOUT % "light"))
    problems = pin_problems(dark, light)
    seen = set()
    for pattern in OUR_DESKTOP_GLOBS:
        for path in sorted(glob.glob(os.path.join(AIROOTFS, pattern))):
            rel = os.path.relpath(path, AIROOTFS)
            seen.add(rel)
            problems += desktop_problems(rel, desktop_keys(read(rel)))
    print("checked %d desktop files of ours, %d pins" % (len(seen), len(dark or [])))
    if "--require-file-db" in argv:
        allowed = base_packages()
        for pin in dark or []:
            ident = pin.split(":", 1)[-1]
            if os.path.exists(os.path.join(AIROOTFS, "usr/share/applications", ident)):
                continue
            pk = owners(ident)
            if pk is None:
                problems.append("pacman file database not available (run pacman -Fy)")
                break
            if not pk & allowed:
                problems.append("pinned %s is not shipped by a Base package (found in: %s)"
                                % (ident, ", ".join(sorted(pk)) or "nothing"))
            else:
                print("ok  %-34s %s" % (ident, ", ".join(sorted(pk & allowed))))
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
