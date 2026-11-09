#!/usr/bin/env python3
"""WCAG contrast assertions for the Heiss tokens (stdlib only).

Fails (exit 1) when a text/background pair is below its minimum and is not
listed under known_exceptions in the token file. Known exceptions are printed
as findings so they stay visible.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heiss_tokens as h  # noqa: E402


def main():
    tokens = h.load()
    known = tokens["known_exceptions"]
    failed = 0
    for th in h.THEMES:
        listed = set(known.get(th, []))
        seen = set()
        for label, fg, bg, minimum in h.text_pairs(tokens, th):
            ratio = h.contrast(fg, bg)
            if ratio >= minimum:
                continue
            seen.add(label)
            if label in listed:
                print("KNOWN  %-5s %-40s %.2f < %.1f (frozen palette)" % (th, label, ratio, minimum))
            else:
                print("FAIL   %-5s %-40s %.2f < %.1f" % (th, label, ratio, minimum))
                failed += 1
        for label in sorted(listed - seen):
            print("STALE  %-5s %s is listed as exception but now passes: remove it" % (th, label))
            failed += 1
    print("contrast check: %s" % ("FAILED" if failed else "ok"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
