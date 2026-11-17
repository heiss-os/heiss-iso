"""Package review of the installed system (round 25): what was decided to leave out, and the guards that stay."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIR = os.path.join(REPO, "profile/airootfs")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Leftovers(unittest.TestCase):
    def test_refind_is_not_shipped_and_cleanup_removes_it_and_arch_install_scripts(self):
        self.assertNotIn("refind", read(REPO, "profile/packages.x86_64").split())     # the bootloader is GRUB
        cleanup = read(AIR, "usr/local/bin/heiss-cleanup.sh")
        live = re.search(r"LIVE_PKGS=\((.*?)\)", cleanup, re.S).group(1).split()
        for pkg in ("arch-install-scripts", "refind", "archinstall"):
            self.assertIn(pkg, live)
        self.assertIn('bootloader.conf', os.listdir(os.path.join(AIR, "etc/calamares/modules")))
        self.assertRegex(read(AIR, "etc/calamares/modules/bootloader.conf"), r"(?m)^efiBootLoader:\s*\"?grub")

    def test_reflector_stays_installed_but_nothing_enables_it(self):
        self.assertIn("reflector", read(REPO, "profiles/essentials.toml"))
        for root, _dirs, files in os.walk(os.path.join(AIR, "etc/systemd")):
            for f in files:
                self.assertNotIn("reflector", f, os.path.join(root, f))          # no unit, link or drop-in
        for sub in ("system", "user"):
            d = os.path.join(AIR, "etc/systemd", sub)
            if os.path.isdir(d):
                for root, _dirs, files in os.walk(d):
                    for f in files:
                        if os.path.islink(os.path.join(root, f)):
                            self.assertNotIn("reflector", os.readlink(os.path.join(root, f)))
        services = re.search(r"services = \[(.*?)\]", read(REPO, "profiles/essentials.toml"), re.S).group(1)
        self.assertNotIn("reflector", services)

    def test_no_calamares_user_tracking_and_no_tracking_module_in_the_sequence(self):
        self.assertNotIn("tracking", read(AIR, "etc/calamares/settings.conf"))
        tr = read(AIR, "etc/calamares/modules/tracking.conf")
        user = tr[tr.index("\nuser:"):]
        self.assertRegex(user, r"(?m)^\s+enabled:\s*false")

    def test_no_heiss_tool_calls_lsb_release(self):
        # /etc/lsb-release and the lsb_release command exist only while the lsb-release package is installed
        # (it is a dependency of open-vm-tools, removed on other hypervisors)
        skip = {"tests", "out", ".git", "__pycache__"}
        hits = []
        for base in ("core", "helper", "welcome", "control", "scripts", "profile/airootfs/usr/local/bin"):
            for root, dirs, files in os.walk(os.path.join(REPO, base)):
                dirs[:] = [d for d in dirs if d not in skip]
                for f in files:
                    if f.endswith((".py", ".sh", ".qml")) or base.endswith("bin"):
                        try:
                            if "lsb_release" in read(root, f):
                                hits.append(os.path.join(root, f))
                        except (UnicodeDecodeError, OSError):
                            pass
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
