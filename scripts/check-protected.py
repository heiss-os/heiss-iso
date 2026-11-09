#!/usr/bin/env python3
"""Tier A guard (stdlib only).

  check-protected.py verify   fail if any protected file changed, vanished or a new
                              file appeared under a protected path (not in the list)
  check-protected.py update   rewrite docs/design/protected.sha256 from the git tree

Only tracked files are considered (git ls-files). protected.sha256 itself is covered
by the path list (docs/design/protected-paths.txt), not hashed inside itself.
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATHS = os.path.join(ROOT, "docs", "design", "protected-paths.txt")
SUMS = os.path.join(ROOT, "docs", "design", "protected.sha256")
SELF_HASH_EXEMPT = {"docs/design/protected.sha256"}


def prefixes():
    with open(PATHS, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def protected_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                         capture_output=True).stdout.decode().split("\0")
    pre = prefixes()
    return sorted(p for p in out if p and p not in SELF_HASH_EXEMPT and any(p.startswith(x) for x in pre))


def sha(path):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums():
    sums = {}
    with open(SUMS, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                digest, path = line.rstrip("\n").split("  ", 1)
                sums[path] = digest
    return sums


def main(argv):
    if len(argv) != 1 or argv[0] not in ("verify", "update"):
        print(__doc__)
        return 2
    files = protected_files()
    if argv[0] == "update":
        with open(SUMS, "w", encoding="utf-8") as f:
            for p in files:
                f.write("%s  %s\n" % (sha(p), p))
        print("wrote %d checksums" % len(files))
        return 0
    sums, problems = read_sums(), []
    for p in files:
        if p not in sums:
            problems.append("NEW      " + p)
        elif not os.path.exists(os.path.join(ROOT, p)) or sha(p) != sums[p]:
            problems.append("CHANGED  " + p)
    for p in sums:
        if p not in files:
            problems.append("REMOVED  " + p)
    if problems:
        print("Protected (Tier A) files differ from docs/design/protected.sha256:")
        print(*("  " + x for x in problems), sep="\n")
        print("A deliberate change needs the PR label 'design-approved' and a regenerated protected.sha256.")
        return 1
    print("protected files unchanged (%d)" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
