#!/usr/bin/env python3
"""Fail when a file shipped by our packages is also shipped by an official package.

An ISO build (pacstrap) stops with "exists in filesystem" on such a conflict, so it must be caught earlier.
Usage: check-file-conflicts.py PACKAGE.pkg.tar.zst ...   (needs pacman with a synced file database: pacman -Fy)
"""
import re
import subprocess
import sys

IGNORED = re.compile(r"^(\.|.*/$)")   # package metadata and directories


def package_files(path):
    r = subprocess.run(["bsdtar", "-tf", path], capture_output=True, text=True, check=True)
    return [l for l in r.stdout.splitlines() if l and not IGNORED.match(l)]


def owners(paths):
    """{path: {repo/package}} for paths that an official package ships."""
    found = {}
    for i in range(0, len(paths), 40):
        chunk = paths[i:i + 40]
        regex = "^(%s)$" % "|".join(re.escape(p) for p in chunk)
        r = subprocess.run(["pacman", "-Fx", "--machinereadable", regex], capture_output=True, text=True,
                           env={"LC_ALL": "C", "PATH": "/usr/bin"})
        if r.returncode not in (0, 1):
            raise SystemExit("pacman -F failed (run pacman -Fy first): %s" % r.stderr.strip())
        for line in r.stdout.splitlines():
            parts = line.split("\0")
            if len(parts) >= 4:
                found.setdefault(parts[3], set()).add("%s/%s" % (parts[0], parts[1]))
    return found


def main(argv):
    bad, total = [], 0
    for pkg in argv:
        files = package_files(pkg)
        total += len(files)
        for path, who in sorted(owners(files).items()):
            bad.append("%s: %s is also in %s" % (pkg.rsplit("/", 1)[-1], path, ", ".join(sorted(who))))
    print("checked %d files in %d package(s)" % (total, len(argv)))
    for b in bad:
        print("CONFLICT:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
