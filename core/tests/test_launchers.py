import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("check_launchers", os.path.join(REPO, "scripts", "check-launchers.py"))
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

GOOD = 'tasks.writeConfig("launchers", [\n "applications:a.desktop",\n "applications:b.desktop"\n]);'


class Pins(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(cl.pins(GOOD), ["applications:a.desktop", "applications:b.desktop"])

    def test_comma_joined_string_is_rejected(self):
        bad = ["applications:a.desktop,applications:b.desktop"]
        self.assertTrue(cl.pin_problems(bad, bad))

    def test_duplicates_and_mismatch(self):
        p = ["applications:a.desktop", "applications:a.desktop"]
        self.assertTrue(any("twice" in m for m in cl.pin_problems(p, p)))
        self.assertTrue(any("different" in m for m in cl.pin_problems(["applications:a.desktop"], ["applications:b.desktop"])))

    def test_shipped_layouts_are_clean(self):
        d, l = (cl.pins(cl.read(cl.LAYOUT % t)) for t in ("dark", "light"))
        self.assertEqual(cl.pin_problems(d, l), [])


class Desktop(unittest.TestCase):
    def test_installer_needs_wm_class(self):
        keys = {"Exec": "sudo -E calamares", "Icon": "heiss-installer"}
        self.assertTrue(cl.desktop_problems("usr/share/applications/x.desktop", keys))

    def test_local_override_must_be_hidden(self):
        keys = {"Exec": "sudo -E calamares", "Icon": "heiss-installer", "StartupWMClass": "calamares"}
        self.assertTrue(any("NoDisplay" in m for m in cl.desktop_problems("usr/local/share/applications/c.desktop", keys)))

    def test_keys_only_from_main_group(self):
        text = "[Desktop Entry]\nIcon=a\n[Desktop Action x]\nIcon=b\n"
        self.assertEqual(cl.desktop_keys(text)["Icon"], "a")

    def test_shipped_desktop_files_are_clean(self):
        import glob
        for pattern in cl.OUR_DESKTOP_GLOBS:
            for path in glob.glob(os.path.join(cl.AIROOTFS, pattern)):
                rel = os.path.relpath(path, cl.AIROOTFS)
                self.assertEqual(cl.desktop_problems(rel, cl.desktop_keys(cl.read(rel))), [], rel)


if __name__ == "__main__":
    unittest.main()
