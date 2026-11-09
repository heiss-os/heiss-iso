#!/usr/bin/env python3
"""Check profile/packages.x86_64: every entry must exist in the official repositories
(pacman -Si) or be a local package (calamares from the AUR build, or a directory under packages/).

Needs pacman with synced databases (CI runs it in an archlinux container).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_EXTRA = {"calamares"}   # built from the AUR by scripts/heiss-calamares-build.sh


def entries():
    with open(os.path.join(ROOT, "profile", "packages.x86_64"), encoding="utf-8") as f:
        names = [l.split("#")[0].strip() for l in f]
    return [n for n in names if n]


def local_packages():
    d = os.path.join(ROOT, "packages")
    return LOCAL_EXTRA | {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}


def main():
    names, local = entries(), local_packages()
    dup = sorted({n for n in names if names.count(n) > 1})
    missing = []
    for n in names:
        if n in local:
            continue
        r = subprocess.run(["pacman", "-Si", n], capture_output=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
        if r.returncode != 0:
            missing.append(n)
    for n in dup:
        print("DUPLICATE:", n)
    for n in missing:
        print("NOT FOUND in the repositories and not a local package:", n)
    print("%d entries, %d local" % (len(names), len([n for n in names if n in local])))
    return 1 if (dup or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
