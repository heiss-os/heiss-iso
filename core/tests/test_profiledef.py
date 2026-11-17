"""profiledef.sh: secret files get a tight mode and the publisher URL is well formed."""
import re
import subprocess
import unittest
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[2] / "profile" / "profiledef.sh").read_text()


class ProfileDef(unittest.TestCase):
    def test_shadow_files_are_0400(self):
        for name in ("/etc/shadow", "/etc/gshadow"):
            pat = r'^\s*\["%s"\]="0:0:400"\s*$' % re.escape(name)
            self.assertEqual(len(re.findall(pat, TEXT, re.M)), 1, name)
            self.assertEqual(TEXT.count('["%s"]=' % name), 1, name + " is set more than once")

    def test_publisher_url(self):
        m = re.search(r'^iso_publisher="[^"]*<(\S+)>"', TEXT, re.M)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"^https://[^/]")

    def test_bash_syntax(self):
        path = Path(__file__).resolve().parents[2] / "profile" / "profiledef.sh"
        r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
