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


# guards.yml is a Tier A protected file: `persist-credentials: false` there needs the owner's design-approved. It holds no
# secrets and has `contents: read`. Remove it from this set in the PR that adds the option.
CHECKOUT_WITHOUT_OPTION_PENDING_APPROVAL = {"guards.yml"}


class Credentials(unittest.TestCase):
    def workflows(self):
        return {os.path.basename(f): open(f, encoding="utf-8").read().splitlines()
                for f in sorted(glob.glob(os.path.join(REPO, ".github", "workflows", "*.yml")))}

    def test_every_checkout_drops_the_token_from_the_clone(self):
        for name, lines in self.workflows().items():
            found, open_ = 0, 0
            for no, line in enumerate(lines):
                if "uses: actions/checkout@" not in line:
                    continue
                found += 1
                block = lines[no + 1:no + 4]
                if any(l.strip() == "persist-credentials: false" for l in block):
                    open_ += 1
            if name in CHECKOUT_WITHOUT_OPTION_PENDING_APPROVAL:
                self.assertLess(open_, found, "%s is fixed now: remove it from the pending set" % name)
            else:
                self.assertEqual(open_, found, "%s: every checkout needs persist-credentials: false" % name)

    def test_the_publish_token_is_not_put_on_a_command_line(self):
        text = "\n".join(self.workflows()["publish-repo.yml"])
        self.assertNotIn('-c "http.extraheader', text)
        self.assertNotIn("-c http.extraheader", text)
        lines = self.workflows()["publish-repo.yml"]
        push = next(i for i, l in enumerate(lines) if "git push origin HEAD:gh-pages" in l)
        cmd = " ".join(l.strip().rstrip("\\") for l in lines[max(push - 2, 0):push + 1] if "GIT_CONFIG" in l or "git push" in l)
        for name in ("GIT_CONFIG_COUNT=1", "GIT_CONFIG_KEY_0=http.extraheader", "GIT_CONFIG_VALUE_0="):
            self.assertIn(name, cmd, "the header must be set on the same command as git push")
        self.assertNotIn("export GIT_CONFIG", text)         # never for the rest of the step


if __name__ == "__main__":
    unittest.main()
