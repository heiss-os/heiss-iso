"""scripts/audit-image.sh on small fake image trees (--root): a good tree passes, each broken rule fails, the work
directory guard refuses memory file systems. The real ISO is not needed (and not in CI)."""
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "audit-image.sh")
PACKAGES = ("heiss-core", "heiss-helper", "heiss-theme", "heiss-keyring", "heiss-welcome", "heiss-control",
            "heiss-safe-graphics", "heiss-profile-base")


def put(root, rel, text="", mode=0o644):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, mode)


def good_tree(root):
    put(root, "usr/lib/os-release", 'NAME="Heiss OS"\nPRETTY_NAME="Heiss OS"\nID=heiss\n')
    put(root, "etc/issue", "Heiss OS \\r (\\l)\n")
    put(root, "etc/motd", "")
    put(root, "usr/share/heiss/lsb-release", "DISTRIB_ID=Heiss\n")
    put(root, "etc/NetworkManager/conf.d/20-connectivity.conf", "[connectivity]\nenabled=false\n")
    put(root, "etc/shadow", "root:!:1::::::\n", 0o400)
    put(root, "etc/gshadow", "root:!::\n", 0o400)
    put(root, "etc/calamares/settings.conf", "sequence:\n- show:\n  - welcome\n")
    put(root, "usr/share/pacman/keyrings/heiss.gpg", "x")
    put(root, "usr/share/pacman/keyrings/heiss-trusted", "DDD292CCC8613FD3324D3833FEA84CEF8AEDF132:4:\n")
    put(root, "usr/local/bin/heiss-cleanup.sh",
        "printf '\\n[heiss]\\nSigLevel = Required DatabaseRequired\\nServer = x\\n' >> /etc/pacman.conf\n", 0o755)
    put(root, "etc/grub.d/41_heiss_safe", "linux ... nomodeset\n", 0o755)
    for p in PACKAGES:
        put(root, "var/lib/pacman/local/%s-1.0-1/desc" % p, "%NAME%\n" + p + "\n%SIZE%\n1048576\n")


class Audit(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="audit-test.")
        self.root = os.path.join(self.d, "root")
        good_tree(self.root)

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+rwX", self.d])
        shutil.rmtree(self.d)

    def run_audit(self, *args):
        return subprocess.run(["bash", SCRIPT, *args], capture_output=True, text=True,
                              env={"PATH": os.environ["PATH"], "HOME": self.d})

    def test_good_tree_passes(self):
        r = self.run_audit("--root", self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 FAIL", r.stdout)
        self.assertNotIn("\nFAIL", r.stdout)

    def test_each_broken_rule_fails(self):
        cases = [
            ("os-release says Arch", lambda: put(self.root, "usr/lib/os-release", 'NAME="Arch Linux"\nPRETTY_NAME="Arch Linux"\n')),
            ("issue says Arch", lambda: put(self.root, "etc/issue", "Arch Linux \\r\n")),
            ("shadow readable by all", lambda: os.chmod(os.path.join(self.root, "etc/shadow"), 0o644)),
            ("connectivity check on", lambda: put(self.root, "etc/NetworkManager/conf.d/20-connectivity.conf", "[connectivity]\nenabled=true\n")),
            ("enabled reflector timer", lambda: os.symlink("/usr/lib/systemd/system/reflector.timer",
                                                            self._wants("reflector.timer"))),
            ("tracking enabled", lambda: put(self.root, "etc/calamares/modules/tracking.conf", "user:\n    enabled: true\n")),
            ("keyring fingerprint wrong", lambda: put(self.root, "usr/share/pacman/keyrings/heiss-trusted", "0000:4:\n")),
            ("heiss package missing", lambda: shutil.rmtree(os.path.join(self.root, "var/lib/pacman/local/heiss-core-1.0-1"))),
            ("safe graphics script not executable", lambda: os.chmod(os.path.join(self.root, "etc/grub.d/41_heiss_safe"), 0o644)),
            ("world-writable file", lambda: put(self.root, "etc/leak.conf", "x", 0o666)),
        ]
        for name, change in cases:
            with self.subTest(name):
                shutil.rmtree(self.root)
                good_tree(self.root)
                change()
                r = self.run_audit("--root", self.root)
                self.assertEqual(r.returncode, 1, name + "\n" + r.stdout)
                self.assertRegex(r.stdout, r"(?m)^FAIL ")

    def _wants(self, name):
        d = os.path.join(self.root, "etc/systemd/system/multi-user.target.wants")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, name)

    def test_boot_title_with_arch_fails_but_internal_ids_do_not(self):
        boot = os.path.join(self.d, "boot")
        put(boot, "loader/entries/a.conf", "title    Heiss OS Live (x86_64, UEFI)\n")
        put(boot, "boot/grub/grub.cfg", "menuentry \"Heiss OS Live\" --class arch --id 'archlinux' {\n}\n")
        r = self.run_audit("--root", self.root, "--boot", boot)
        self.assertEqual(r.returncode, 0, r.stdout)
        put(boot, "loader/entries/b.conf", "title    Arch Linux install medium\n")
        r = self.run_audit("--root", self.root, "--boot", boot)
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_usage_errors_exit_two_and_read_nothing(self):
        self.assertEqual(self.run_audit().returncode, 2)
        self.assertEqual(self.run_audit("--root", os.path.join(self.d, "missing")).returncode, 2)
        self.assertEqual(self.run_audit("/nonexistent.iso").returncode, 2)
        self.assertEqual(self.run_audit("a.iso", "--root", self.root).returncode, 2)

    def test_work_directory_must_not_be_memory(self):
        if shutil.which("unsquashfs") is None or shutil.which("bsdtar") is None:
            self.skipTest("needs unsquashfs and bsdtar")
        iso = os.path.join(self.d, "x.iso")
        put(self.d, "x.iso", "not an iso")
        shm = "/dev/shm"
        if not os.path.isdir(shm):
            self.skipTest("no /dev/shm")
        env = {"PATH": os.environ["PATH"], "AUDIT_TMP": shm}
        r = subprocess.run(["bash", SCRIPT, iso], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("memory", r.stderr)
        self.assertEqual([n for n in os.listdir(shm) if n.startswith("heiss-audit.")], [])


if __name__ == "__main__":
    unittest.main()
