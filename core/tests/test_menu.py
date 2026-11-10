import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(REPO, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


menu, mimeapps = load("check-menu"), load("check-mimeapps")


class Stubs(unittest.TestCase):
    def test_good_stub(self):
        keys = {"Type": "Application", "Name": "x", "NoDisplay": "true", "Hidden": "true"}
        self.assertEqual(menu.stub_problems("x.desktop", keys), [])

    def test_exec_and_visibility_are_rejected(self):
        keys = {"Type": "Application", "Name": "x", "Exec": "x", "NoDisplay": "true"}
        msgs = " ".join(menu.stub_problems("x.desktop", keys))
        self.assertIn("Exec", msgs)
        self.assertIn("Hidden", msgs)

    def test_pins_are_read(self):
        self.assertIn("org.kde.dolphin.desktop", menu.pinned_ids())

    def test_shipped_stubs_are_clean_and_do_not_hide_used_apps(self):
        keep = menu.used_ids(mimeapps)
        import glob
        files = [f for f in glob.glob(os.path.join(menu.DIR, "*.desktop")) if os.path.basename(f) not in menu.NOT_STUBS]
        self.assertTrue(files)
        for path in files:
            name = os.path.basename(path)
            self.assertNotIn(name, keep)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(menu.stub_problems(name, menu.desktop_keys(f.read())), [], name)


if __name__ == "__main__":
    unittest.main()
