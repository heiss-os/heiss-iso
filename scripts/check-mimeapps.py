#!/usr/bin/env python3
"""Check profile/airootfs/etc/xdg/mimeapps.list (stdlib only).

Always: syntax, no duplicate keys, only [Default Applications], values are desktop ids,
MIME types exist in shared-mime-info (types and aliases; x-scheme-handler/* and the types
listed in APP_DEFINED_TYPES are exempt) when /usr/share/mime is available.

With --require-file-db (CI, archlinux container after `pacman -Fy`): every desktop id must be
shipped by a package that belongs to the Base profile closure (pacman -F).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from heiss_core import manifest as mf  # noqa: E402

PATH = os.path.join(ROOT, "profile", "airootfs", "etc", "xdg", "mimeapps.list")
APP_DEFINED_TYPES = {"application/x-keepass2"}   # defined by the keepassxc package itself
ID_RE = re.compile(r"^[A-Za-z0-9._-]+\.desktop$")


def parse(text):
    """Return ({mime: [desktop ids]}, [problems])."""
    data, problems, section = {}, [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            section = line
            if section != "[Default Applications]":
                problems.append("line %d: unexpected section %s" % (n, section))
            continue
        if "=" not in line or section != "[Default Applications]":
            problems.append("line %d: not a key=value line in [Default Applications]" % n)
            continue
        key, value = line.split("=", 1)
        if key in data:
            problems.append("line %d: duplicate key %s" % (n, key))
        ids = [v for v in value.split(";") if v]
        if not value.endswith(";") or not ids or not all(ID_RE.match(i) for i in ids):
            problems.append("line %d: %s needs desktop ids ending with ';'" % (n, key))
        data[key] = ids
    return data, problems


def known_mime_types(mime_dir="/usr/share/mime"):
    try:
        types = set(open(os.path.join(mime_dir, "types"), encoding="utf-8").read().split())
        for line in open(os.path.join(mime_dir, "aliases"), encoding="utf-8"):
            parts = line.split()
            if len(parts) == 2:
                types.add(parts[0])
        return types
    except OSError:
        return None


def mime_problems(data, known):
    return ["unknown MIME type %s" % k for k in sorted(data)
            if not (k.startswith("x-scheme-handler/") or k in APP_DEFINED_TYPES or k in known)]


def base_packages():
    manifests = mf.load_dir(os.path.join(ROOT, "profiles"))
    return {p for mid in mf.closure(manifests, ["base"]) for p in manifests[mid].packages}


def owners(desktop_id):
    """Packages shipping usr/share/applications/<id>, or None when the file database is missing."""
    r = subprocess.run(["pacman", "-Fx", "--machinereadable", "^usr/share/applications/%s$" % re.escape(desktop_id)],
                       capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
    if r.returncode not in (0, 1):
        return None
    return {line.split("\0")[1] for line in r.stdout.splitlines() if line.count("\0") >= 3}


def main(argv):
    with open(PATH, encoding="utf-8") as f:
        data, problems = parse(f.read())
    known = known_mime_types()
    if known is None:
        print("note: /usr/share/mime not found, MIME type names were not checked")
    else:
        problems += mime_problems(data, known)
    apps = sorted({i for ids in data.values() for i in ids})
    if "--require-file-db" in argv:
        allowed = base_packages()
        for app in apps:
            pk = owners(app)
            if pk is None:
                problems.append("pacman file database not available (run pacman -Fy)")
                break
            if not pk:
                problems.append("%s is not shipped by any package" % app)
            elif not pk & allowed:
                problems.append("%s comes from %s which is not in the Base profile" % (app, ", ".join(sorted(pk))))
            else:
                print("ok  %-34s %s" % (app, ", ".join(sorted(pk & allowed))))
    for p in problems:
        print("PROBLEM:", p)
    print("%d associations, %d applications" % (len(data), len(apps)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
