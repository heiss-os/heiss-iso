"""The dock fallback's single-instance lock must never live in /tmp (a shared, world-writable directory)."""
import os
import re
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(REPO, "profile/airootfs/usr/local/bin/heiss-setup-dock.sh")


class DockLock(unittest.TestCase):
    def lock_lines(self):
        text = open(SCRIPT, encoding="utf-8").read()
        m = re.search(r'^LOCK=.*\n^exec 9>"\$LOCK"\n^if ! flock -n 9.*$', text, re.M)
        self.assertIsNotNone(m, "lock block not found")
        return text, m.group(0)

    def test_lock_path_is_not_in_tmp(self):
        text, block = self.lock_lines()
        self.assertNotIn("/tmp", block)
        self.assertIn('LOCK="${XDG_RUNTIME_DIR:-$HOME/.cache}/heiss-dock.lock"', block)
        # the fallback directory exists before the lock is opened
        self.assertLess(text.index('mkdir -p "$HOME/.cache"'), text.index("LOCK="))

    def test_lock_block_runs_without_xdg_runtime_dir_and_creates_nothing_in_tmp(self):
        _, block = self.lock_lines()
        before = set(os.listdir("/tmp"))
        with tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".cache"))
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home}
            snippet = 'log() { :; }\n' + block + '\necho got-lock\n'
            r = subprocess.run(["sh", "-c", snippet], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "got-lock"), r.stderr)
            self.assertTrue(os.path.exists(os.path.join(home, ".cache", "heiss-dock.lock")))
        self.assertEqual(set(os.listdir("/tmp")) - before, set())


if __name__ == "__main__":
    unittest.main()
