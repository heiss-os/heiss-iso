"""Workflow files: every action is pinned to a full commit SHA (a tag can be moved by whoever owns the action)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)(.*)$")
SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


# Workflow files that may stay unpinned for now (none: guards.yml, Tier A, was pinned with the owner's design-approved).
PENDING_OWNER_APPROVAL = set()


class Pins(unittest.TestCase):
    def test_every_action_is_pinned_to_a_commit_sha_with_a_version_comment(self):
        files = sorted(glob.glob(os.path.join(REPO, ".github", "workflows", "*.yml")))
        self.assertTrue(files)
        n = 0
        for path in files:
            if os.path.basename(path) in PENDING_OWNER_APPROVAL:
                with open(path, encoding="utf-8") as f:
                    unpinned = [m for m in map(USES.match, f) if m and not SHA.match(m.group(1))]
                self.assertTrue(unpinned, "%s is pinned now: remove it from PENDING_OWNER_APPROVAL" % os.path.basename(path))
                continue
            with open(path, encoding="utf-8") as f:
                for no, line in enumerate(f, 1):
                    m = USES.match(line)
                    if not m or m.group(1).startswith("./"):
                        continue
                    n += 1
                    where = "%s:%d" % (os.path.basename(path), no)
                    self.assertRegex(m.group(1), SHA, where)
                    self.assertRegex(m.group(2), r"#\s*v\d", where + " needs a '# vX.Y.Z' comment")
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
