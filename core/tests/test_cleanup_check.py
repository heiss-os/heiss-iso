"""The installer's cleanup script must stop the installation when root is not locked or the live user remains."""
import os
import re
import stat
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(REPO, "profile/airootfs/usr/local/bin/heiss-cleanup.sh")
HOST_AUTOLOGIN = ("/etc/sddm.conf.d/autologin.conf", "/etc/systemd/system/getty@tty1.service.d/autologin.conf",
                  "/etc/sudoers.d/g_wheel")


def final_check_block():
    text = open(SCRIPT, encoding="utf-8").read()
    m = re.search(r"^# --- final check \(begin\) ---\n(.*?)^# --- final check \(end\) ---$", text, re.M | re.S)
    assert m, "final check block not found"
    return text, m.group(1)


def stub(directory, name, body):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n" + body + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


@unittest.skipIf(any(os.path.exists(p) for p in HOST_AUTOLOGIN), "the build host itself has a live autologin file")
class FinalCheck(unittest.TestCase):
    def run_block(self, passwd_line, liveuser_exists, getent_rc=None):
        _, block = final_check_block()
        if getent_rc is None:
            getent_rc = 0 if liveuser_exists else 2
        with tempfile.TemporaryDirectory() as bindir:
            stub(bindir, "passwd", 'echo "%s"' % passwd_line)
            stub(bindir, "getent", "exit %d" % getent_rc)
            env = {"PATH": bindir + ":" + os.environ.get("PATH", "/usr/bin:/bin")}
            snippet = "set -u\nlog() { echo \"[heiss-cleanup] $*\"; }\n" + block + "\necho reached-the-end\n"
            return subprocess.run(["bash", "-c", snippet], env=env, capture_output=True, text=True, timeout=20)

    def test_block_sits_before_the_script_removes_itself(self):
        text, _ = final_check_block()
        self.assertLess(text.index("# --- final check (end) ---"), text.index("rm -f /usr/local/bin/heiss-cleanup.sh"))
        # the script does not run with -e: the final check is the only hard stop
        self.assertNotIn("set -e", text)

    def test_locked_root_and_no_live_user_pass(self):
        r = self.run_block("root L 2026-01-01 0 99999 7 -1", liveuser_exists=False)
        self.assertEqual((r.returncode, r.stdout.strip().splitlines()[-1]), (0, "reached-the-end"), r.stdout + r.stderr)

    def test_unlocked_root_stops_the_installation(self):
        for line in ("root NP 2026-01-01 0 99999 7 -1", "root P 2026-01-01 0 99999 7 -1", ""):
            with self.subTest(passwd=line):
                r = self.run_block(line, liveuser_exists=False)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("root is not locked", r.stdout)
                self.assertNotIn("reached-the-end", r.stdout)

    def test_remaining_live_user_stops_the_installation(self):
        r = self.run_block("root L 2026-01-01 0 99999 7 -1", liveuser_exists=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("live user still exists", r.stdout)
        self.assertNotIn("reached-the-end", r.stdout)

    def test_broken_user_database_stops_the_installation(self):
        # getent exit 1 (bad database) or 3: the check must not pass just because the tool failed
        for rc in (1, 3, 127):
            with self.subTest(rc=rc):
                r = self.run_block("root L 2026-01-01 0 99999 7 -1", liveuser_exists=False, getent_rc=rc)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("cannot check the user database", r.stdout)

    def test_live_sudo_rule_is_part_of_the_check(self):
        _, block = final_check_block()
        self.assertIn("/etc/sudoers.d/g_wheel", block)
        self.assertTrue(os.path.exists(os.path.join(REPO, "profile/airootfs/etc/sudoers.d/g_wheel")))


class LiveOnlyDropIns(unittest.TestCase):
    """Every drop-in the live image ships under /etc/systemd that must not reach the installed system is removed."""

    def test_live_only_drop_ins_are_removed(self):
        text = open(SCRIPT, encoding="utf-8").read()
        for path in ("/etc/systemd/journald.conf.d/volatile-storage.conf",
                     "/etc/systemd/logind.conf.d/do-not-suspend.conf",
                     "/etc/systemd/system-generators/systemd-gpt-auto-generator",
                     "/etc/systemd/resolved.conf.d/archiso.conf"):
            airootfs = os.path.join(REPO, "profile/airootfs", path.lstrip("/"))
            self.assertTrue(os.path.lexists(airootfs), airootfs)
            self.assertRegex(text, re.compile(r"^rm -f .*" + re.escape(path), re.M), path)


if __name__ == "__main__":
    unittest.main()
