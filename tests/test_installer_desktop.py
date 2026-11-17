"""Installer and desktop in the live and installed system: wallpaper reference, finish page style, VirtualBox tools."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIR = os.path.join(REPO, "profile/airootfs")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Wallpaper(unittest.TestCase):
    def test_every_wallpaper_reference_is_a_package_url_not_a_bare_id(self):
        # Plasma stores a package as file:///usr/share/wallpapers/<id>/; a bare id does not resolve and the desktop
        # stayed on the plain colour (first real install)
        url = r"file:///usr/share/wallpapers/Heiss-Everyday(-Light)?/"
        for theme, wall in (("dark", "Heiss-Everyday"), ("light", "Heiss-Everyday-Light")):
            js = read(AIR, "usr/share/plasma/look-and-feel/org.heiss.%s.desktop/contents/layouts/org.kde.plasma.desktop-layout.js" % theme)
            self.assertIn('writeConfig("Image", "file:///usr/share/wallpapers/%s/")' % wall, js)
            self.assertNotRegex(js, r'writeConfig\("Image", "Heiss-')
        self.assertRegex(read(AIR, "etc/xdg/kscreenlockerrc"), r"(?m)^Image=" + url + "$")
        sh = read(AIR, "usr/local/bin/heiss-set-wallpaper.sh")
        self.assertIn('URL="file:///usr/share/wallpapers/$ID/"', sh)
        self.assertNotIn('writeConfig("Image", "\'"$ID"\'")', sh)

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
