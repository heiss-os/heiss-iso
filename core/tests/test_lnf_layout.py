"""Packaged layout of the Heiss global themes (Look-and-Feel packages) and their system defaults."""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
AIR = os.path.join(REPO, "profile/airootfs")
LNF = os.path.join(AIR, "usr/share/plasma/look-and-feel")
THEMES = {"dark": ("org.heiss.dark.desktop", "Heiss Dark", "HeissDark", "Heiss-Everyday"),
          "light": ("org.heiss.light.desktop", "Heiss Light", "HeissLight", "Heiss-Everyday-Light")}


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


class Lnf(unittest.TestCase):
    def test_each_package_is_complete(self):
        for t, (pid, name, scheme, wall) in THEMES.items():
            base = os.path.join(LNF, pid)
            meta = json.loads(read(base, "metadata.json"))
            self.assertEqual(meta["KPackageStructure"], "Plasma/LookAndFeel")
            self.assertEqual((meta["KPlugin"]["Id"], meta["KPlugin"]["Name"]), (pid, name))
            for f in ("contents/defaults", "contents/layouts/org.kde.plasma.desktop-layout.js", "contents/splash/Splash.qml",
                      "contents/previews/preview.png", "contents/previews/fullscreenpreview.jpg"):
                self.assertTrue(os.path.isfile(os.path.join(base, f)), "%s: %s" % (pid, f))
            d = read(base, "contents/defaults")
            self.assertIn("ColorScheme=" + scheme, d)
            self.assertIn("Image=" + wall, d)
            self.assertIn("Theme=" + pid, d)                   # splash
            self.assertIn('writeConfig("Image", "%s")' % wall, read(base, "contents/layouts/org.kde.plasma.desktop-layout.js"))
            self.assertIn("FillMode", read(base, "contents/layouts/org.kde.plasma.desktop-layout.js"))

    def test_previews_are_real_images(self):
        for pid, *_ in THEMES.values():
            p = os.path.join(LNF, pid, "contents/previews")
            self.assertEqual(open(os.path.join(p, "preview.png"), "rb").read(8), b"\x89PNG\r\n\x1a\n")
            self.assertEqual(open(os.path.join(p, "fullscreenpreview.jpg"), "rb").read(2), b"\xff\xd8")

    def test_scheme_files_and_wallpaper_packages_exist_with_heiss_names(self):
        for t, (pid, name, scheme, wall) in THEMES.items():
            self.assertIn("Name=" + name, read(AIR, "usr/share/color-schemes", scheme + ".colors"))
            for size in ("1920x1080", "2560x1440", "3840x2160"):
                self.assertTrue(os.path.isfile(os.path.join(AIR, "usr/share/wallpapers", wall, "contents/images", size + ".png")))
            self.assertTrue(json.loads(read(AIR, "usr/share/wallpapers", wall, "metadata.json"))["KPlugin"]["Name"].startswith("Heiss"))

    def test_system_defaults_start_on_heiss_and_automatic_uses_only_heiss(self):
        k = read(AIR, "etc/xdg/kdeglobals")
        for line in ("ColorScheme=HeissDark", "LookAndFeelPackage=org.heiss.dark.desktop",
                     "DefaultDarkLookAndFeel=org.heiss.dark.desktop", "DefaultLightLookAndFeel=org.heiss.light.desktop",
                     "AutomaticLookAndFeel=false"):
            self.assertRegex(k, r"(?m)^%s$" % re.escape(line))
        self.assertEqual(read(AIR, "etc/xdg/ksplashrc").count("Theme=org.heiss.dark.desktop"), 1)

    def test_light_wallpaper_is_light_and_dark_is_dark(self):
        # the generator keeps the composition; sizes must match and the files must differ
        for size in ("1920x1080", "2560x1440", "3840x2160"):
            a = os.path.join(AIR, "usr/share/wallpapers/Heiss-Everyday/contents/images", size + ".png")
            b = os.path.join(AIR, "usr/share/wallpapers/Heiss-Everyday-Light/contents/images", size + ".png")
            with open(a, "rb") as fa, open(b, "rb") as fb:
                ha, hb = fa.read(24), fb.read(24)
            self.assertEqual(ha[16:24], hb[16:24], "same pixel size")
            self.assertNotEqual(read_bytes(a), read_bytes(b))


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


if __name__ == "__main__":
    unittest.main()
