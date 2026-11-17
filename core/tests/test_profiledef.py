"""profiledef.sh: secret files get a tight mode and the publisher URL is well formed."""
import re
import unittest
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[2] / "profile" / "profiledef.sh").read_text()


class ProfileDef(unittest.TestCase):
    def test_shadow_files_are_0400(self):
        for name in ("/etc/shadow", "/etc/gshadow"):
            self.assertIn('["%s"]="0:0:400"' % name, TEXT)

    def test_publisher_url(self):
        m = re.search(r'^iso_publisher="[^"]*<(\S+)>"', TEXT, re.M)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"^https://[^/]")


if __name__ == "__main__":
    unittest.main()
