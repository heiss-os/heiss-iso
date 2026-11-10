import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("check_shortcuts", os.path.join(REPO, "scripts", "check-shortcuts.py"))
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


class Shortcuts(unittest.TestCase):
    def test_parse_only_main_group(self):
        text = "[Desktop Entry]\nX-KDE-Shortcuts=Meta+E, Tools\n[Desktop Action a]\nX-KDE-Shortcuts=Ctrl+X\n"
        self.assertEqual(cs.desktop_shortcuts(text), ["Meta+E", "Tools"])

    def test_collisions_ignore_case(self):
        found = {"a.desktop": ["Meta+E"], "b.desktop": ["meta+e"], "c.desktop": ["Meta+I"]}
        self.assertEqual(cs.collisions(found), {"meta+e": ["a.desktop", "b.desktop"]})

    def test_documented_rows(self):
        rows = cs.documented("| `Meta+E` | Files | desktop | `x.desktop` |\n| `Alt+F2` | Run | plasma | - |\n")
        self.assertEqual(rows, [("Meta+E", "x.desktop")])

    def test_shipped_doc_has_desktop_rows(self):
        with open(cs.DOC, encoding="utf-8") as f:
            self.assertGreaterEqual(len(cs.documented(f.read())), 5)


if __name__ == "__main__":
    unittest.main()
