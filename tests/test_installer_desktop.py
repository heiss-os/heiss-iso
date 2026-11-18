"""Installer and desktop in the live and installed system: wallpaper packages, finish page style, VirtualBox tools."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIR = os.path.join(REPO, "profile/airootfs")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Wallpaper(unittest.TestCase):
    def test_wallpaper_packages_exist_for_both_ids(self):
        for wall in ("Heiss-Everyday", "Heiss-Everyday-Light"):
            self.assertTrue(os.path.isdir(os.path.join(AIR, "usr/share/wallpapers", wall, "contents/images")))
            self.assertTrue(os.path.isfile(os.path.join(AIR, "usr/share/wallpapers", wall, "metadata.json")))


class FinishPage(unittest.TestCase):
    def test_finish_text_is_normal_weight_and_upright_after_the_accent_rule(self):
        qss = read(AIR, "usr/share/calamares/branding/heiss/stylesheet.qss")
        accent = qss.index("#mainText, #titleLabel, #welcomeTitle")
        fin = re.search(r"FinishedPage #mainText[^{]*\{([^}]*)\}", qss)
        self.assertTrue(fin, "no rule for the finish page text")
        self.assertGreater(qss.index(fin.group(0)), accent)           # later rule, and more specific
        self.assertIn("font-weight: 400", fin.group(1))
        self.assertIn("font-style: normal", fin.group(1))


class VirtualBox(unittest.TestCase):
    def test_the_iso_ships_the_full_guest_package_the_hardware_profile_proposes(self):
        pk = read(REPO, "profile/packages.x86_64").split()
        self.assertIn("virtualbox-guest-utils", pk)
        self.assertNotIn("virtualbox-guest-utils-nox", pk)       # no VBoxClient: no clipboard, no resizing; conflicts
        hw = read(REPO, "hardware/vm-virtualbox.toml")
        self.assertIn('packages = ["virtualbox-guest-utils"]', hw)
        self.assertIn("vboxservice.service", hw)
        self.assertIn("safe_by_default = true", hw)

    def test_cleanup_keeps_the_same_package_on_virtualbox(self):
        sh = read(AIR, "usr/local/bin/heiss-cleanup.sh")
        self.assertRegex(sh, r"oracle\)\s+keep=virtualbox-guest-utils\s")
        self.assertIn("for g in virtualbox-guest-utils virtualbox-guest-utils-nox", sh)   # the other one is removed elsewhere

    def test_the_service_is_enabled_in_the_live_image(self):
        self.assertTrue(os.path.islink(os.path.join(AIR, "etc/systemd/system/multi-user.target.wants/vboxservice.service")))


if __name__ == "__main__":
    unittest.main()
