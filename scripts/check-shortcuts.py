#!/usr/bin/env python3
"""Keyboard shortcut guard (stdlib only).

Reads X-KDE-Shortcuts of the desktop files found under the given roots (directories that
contain usr/share/applications, for example extracted packages) and checks:
  * no two different desktop files use the same key;
  * every row of docs/design/SHORTCUTS.md marked `desktop` still matches the packages
    (so a changed upstream default fails CI instead of leaving a wrong table).

Usage: check-shortcuts.py ROOT [ROOT ...]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "design", "SHORTCUTS.md")


def desktop_shortcuts(text):
    """Keys listed in X-KDE-Shortcuts of the main [Desktop Entry] group (list)."""
    in_main = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_main = line == "[Desktop Entry]"
        elif in_main and line.startswith("X-KDE-Shortcuts="):
            return [k.strip() for k in line.split("=", 1)[1].split(",") if k.strip()]
    return []


def collect(roots):
    """{desktop id: [keys]} for all files below the roots."""
    found = {}
    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "usr", "share", "applications", "*.desktop"))):
            with open(path, encoding="utf-8", errors="replace") as f:
                keys = desktop_shortcuts(f.read())
            if keys:
                found[os.path.basename(path)] = keys
    return found


def collisions(found):
    by_key = {}
    for ident, keys in found.items():
        for k in keys:
            by_key.setdefault(k.lower(), []).append(ident)
    return {k: v for k, v in by_key.items() if len(v) > 1}


def documented(doc_text):
    """Rows `| key | action | desktop | <desktop id> |` -> [(key, desktop id)]."""
    rows = []
    for line in doc_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[2] == "desktop":
            rows.append((cells[0].strip("`"), cells[3].strip("`")))
    return rows


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    found = collect(argv)
    problems = ["key %s is used by %s" % (k, ", ".join(v)) for k, v in sorted(collisions(found).items())]
    with open(DOC, encoding="utf-8") as f:
        rows = documented(f.read())
    for key, ident in rows:
        if key.lower() not in [k.lower() for k in found.get(ident, [])]:
            problems.append("SHORTCUTS.md says %s is %s, packages say %s" % (ident, key, found.get(ident, "nothing")))
    for p in problems:
        print("PROBLEM:", p)
    print("%d desktop files with shortcuts, %d documented rows" % (len(found), len(rows)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
