"""lsb-release branding: the file, and the pacman hook that restores it after the package is (re)installed."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "profile" / "airootfs" / "usr" / "share" / "heiss" / "lsb-release"
HOOK_NAME = "92-heiss-lsb-release.hook"
HOOKS = [ROOT / "profile" / "hooks" / HOOK_NAME, ROOT / "profile" / "airootfs" / "usr" / "share" / "libalpm" / "hooks" / HOOK_NAME]


class LsbRelease(unittest.TestCase):
    def test_file_says_heiss_and_not_arch(self):
        text = SRC.read_text()
        keys = dict(re.findall(r'^(\w+)="([^"]*)"$', text, re.M))
        self.assertEqual(set(keys), {"DISTRIB_ID", "DISTRIB_RELEASE", "DISTRIB_DESCRIPTION"})
        self.assertEqual(keys["DISTRIB_DESCRIPTION"], "Heiss OS")
        self.assertNotRegex(text, r"(?i)arch")

    def test_hook_restores_the_file_after_the_package_changes(self):
        for hook in HOOKS:
            text = hook.read_text()
            self.assertRegex(text, r"(?m)^Target = lsb-release$", hook)
            self.assertRegex(text, r"(?m)^Operation = Install$", hook)
            self.assertRegex(text, r"(?m)^Operation = Upgrade$", hook)
            self.assertRegex(text, r"(?m)^When = PostTransaction$", hook)
            self.assertIn("Exec = /usr/bin/install -Dm644 /usr/share/heiss/lsb-release /etc/lsb-release", text, hook)

    def test_build_and_installed_hooks_are_identical(self):
        self.assertEqual(HOOKS[0].read_bytes(), HOOKS[1].read_bytes())

    def test_file_is_not_shipped_in_airootfs_etc(self):
        # /etc/lsb-release belongs to the lsb-release package and is not in its backup array: a copy in
        # airootfs/etc would make pacstrap fail with "exists in filesystem".
        self.assertFalse((ROOT / "profile" / "airootfs" / "etc" / "lsb-release").exists())


if __name__ == "__main__":
    unittest.main()
