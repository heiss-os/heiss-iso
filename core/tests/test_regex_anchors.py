"""Validators in the privileged path must use fullmatch: "$" alone matches before a trailing newline.

A source scan, because a single `.match(` on an anchored pattern would silently bring the hole back.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIRS = ("core/heiss_core", "helper/heiss_helper", "welcome/heiss_welcome", "control/heiss_control")
# a regex object used for validation (NAME_RE, HEX4, ...) or a literal pattern given to re.match
BAD = re.compile(r"\b([A-Z][A-Z0-9_]*(?:_RE|RE|HEX4))\.match\(|\bre\.match\(\s*r?[\"']\^")


# STEP_RE only picks progress lines out of a child's output (nothing is validated or trusted through it)
PARSERS = {"STEP_RE"}


class Anchors(unittest.TestCase):
    def test_no_validator_uses_match_instead_of_fullmatch(self):
        files = [f for d in DIRS for f in glob.glob(os.path.join(REPO, d, "*.py"))]
        self.assertTrue(files)
        for path in files:
            with open(path, encoding="utf-8") as f:
                for no, line in enumerate(f, 1):
                    m = BAD.search(line)
                    if m and m.group(1) in PARSERS:
                        continue
                    self.assertIsNone(m, "%s:%d uses match(): use fullmatch" % (os.path.relpath(path, REPO), no))

    def test_the_helper_policy_rejects_a_trailing_newline_in_every_pattern(self):
        import sys
        sys.path.insert(0, os.path.join(REPO, "core"))
        sys.path.insert(0, os.path.join(REPO, "helper"))
        from heiss_core import manifest as mf
        from heiss_helper import policy
        for rx, ok in ((mf.PKG_RE, "nmap"), (mf.UNIT_RE, "sshd.service"), (policy.SNAPSHOT_DESC_RE, "Before update")):
            self.assertTrue(rx.fullmatch(ok), ok)
            self.assertIsNone(rx.fullmatch(ok + "\n"), ok)


if __name__ == "__main__":
    unittest.main()
