#!/usr/bin/env python3
"""Check that every package named in profiles/*.toml exists in the sync databases (pacman -Si).

Needs pacman with synced databases (CI runs it in an archlinux container).
Prints a size summary per manifest (download / installed, packages alone, without dependencies).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from heiss_core import manifest as mf  # noqa: E402

UNITS = {"KiB": 1 / 1024, "MiB": 1.0, "GiB": 1024.0}


def info(pkg):
    r = subprocess.run(["pacman", "-Si", pkg], capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin"})
    if r.returncode != 0:
        return None
    sizes = {}
    for key, name in (("Download Size", "dl"), ("Installed Size", "inst")):
        m = re.search(r"^%s\s*:\s*([\d.]+) (\w+)" % key, r.stdout, re.M)
        sizes[name] = float(m.group(1)) * UNITS.get(m.group(2), 0) if m else 0.0
    return sizes


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles")
    manifests = mf.load_dir(root)
    missing, cache = [], {}
    for m in manifests.values():
        dl = inst = 0.0
        for p in m.packages:
            if p not in cache:
                cache[p] = info(p)
            if cache[p] is None:
                missing.append("%s: %s" % (m.id, p))
            else:
                dl += cache[p]["dl"]
                inst += cache[p]["inst"]
        print("%-26s %3d packages  download %7.0f MiB  installed %7.0f MiB" % (m.id, len(m.packages), dl, inst))
    if missing:
        print("MISSING packages:", *missing, sep="\n  ")
        return 1
    print("all %d packages exist" % len(cache))
    return 0


if __name__ == "__main__":
    sys.exit(main())
