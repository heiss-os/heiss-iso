import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
from heiss_core import manifest as mf  # noqa: E402

OTHER_TERMINALS = {"kitty", "alacritty", "xterm", "foot", "wezterm", "xfce4-terminal", "gnome-terminal",
                   "lxterminal", "terminator", "tilix", "yakuake", "ghostty", "rxvt-unicode", "st"}
OTHER_FILE_MANAGERS = {"thunar", "nautilus", "pcmanfm", "pcmanfm-qt", "nemo", "caja", "krusader", "doublecmd-qt"}


class OpenTerminalHere(unittest.TestCase):
    def setUp(self):
        self.manifests = mf.load_dir(os.path.join(REPO, "profiles"))

    def packages(self, ids):
        return {p for mid in mf.closure(self.manifests, ids) for p in self.manifests[mid].packages}

    def test_base_has_konsole_and_dolphin(self):
        base = self.packages(["base"])
        self.assertIn("konsole", base)     # also ships konsolepart.so for Dolphin's terminal panel
        self.assertIn("dolphin", base)

    def test_base_has_one_terminal_and_one_file_manager(self):
        base = self.packages(["base"])
        self.assertEqual(base & OTHER_TERMINALS, set())
        self.assertEqual(base & OTHER_FILE_MANAGERS, set())

    def test_addons_stay_out_of_every_profile(self):
        for pid in ("base", "cyber", "developer", "custom"):
            if pid in self.manifests:
                closure = mf.closure(self.manifests, [pid])
                self.assertNotIn("addon-kitty", closure, pid)
                self.assertNotIn("addon-thunar", closure, pid)

    def test_addons_are_the_only_source_of_the_alternatives(self):
        self.assertIn("kitty", self.manifests["addon-kitty"].packages)
        self.assertIn("thunar", self.manifests["addon-thunar"].packages)

    def test_folders_open_in_dolphin(self):
        with open(os.path.join(REPO, "profile", "airootfs", "etc", "xdg", "mimeapps.list"), encoding="utf-8") as f:
            text = f.read()
        lines = [l for l in text.splitlines() if l.startswith("inode/directory=")]
        self.assertEqual(lines, ["inode/directory=org.kde.dolphin.desktop;"])


if __name__ == "__main__":
    unittest.main()
