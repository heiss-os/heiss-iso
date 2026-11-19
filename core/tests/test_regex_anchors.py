"""Validators in the privileged path must use fullmatch: "$" alone matches before a trailing newline.

A source scan, because a single `.match(` on an anchored pattern would silently bring the hole back.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRS = ("core/heiss_core", "helper/heiss_helper", "welcome/heiss_welcome", "control/heiss_control")
COMPILED = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*re\.compile\(", re.M)
LITERAL = re.compile(r"\bre\.match\(\s*r?[\"']\^")

# STEP_RE only picks progress lines out of a child's output (nothing is validated or trusted through it)
# the Lua tokenizer in hyprcfg.py matches a token at a position (pattern.match(text, i)): it reads, it validates nothing
PARSERS = {"STEP_RE", "_BLOCK_COMMENT", "_LONG_STRING", "_NUMBER", "_NAME"}


class Anchors(unittest.TestCase):
    def test_no_validator_uses_match_instead_of_fullmatch(self):
        files = [f for d in DIRS for f in glob.glob(os.path.join(REPO, d, "**", "*.py"), recursive=True)]
        self.assertTrue(files)
        names_seen = 0
        for path in files:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            names = set(COMPILED.findall(text)) - PARSERS     # every compiled pattern of this file, any name
            names_seen += len(names)
            call = re.compile(r"\b(%s)\.match\(" % "|".join(sorted(names))) if names else None
            for no, line in enumerate(text.splitlines(), 1):
                where = "%s:%d uses match(): use fullmatch" % (os.path.relpath(path, REPO), no)
                if call:
                    self.assertIsNone(call.search(line), where)
                self.assertIsNone(LITERAL.search(line), where)
        self.assertGreater(names_seen, 10)   # the scan really found the patterns

    def test_the_helper_policy_rejects_a_trailing_newline_in_every_pattern(self):
        import sys
        sys.path.insert(0, os.path.join(REPO, "core"))
        sys.path.insert(0, os.path.join(REPO, "helper"))
        from heiss_core import manifest as mf
        for rx, ok in ((mf.PKG_RE, "nmap"), (mf.UNIT_RE, "sshd.service")):
            self.assertTrue(rx.fullmatch(ok), ok)
            self.assertIsNone(rx.fullmatch(ok + "\n"), ok)


if __name__ == "__main__":
    unittest.main()
