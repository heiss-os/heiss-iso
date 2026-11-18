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


class DefaultTerminalAndFileManager(unittest.TestCase):
    """Kitty and Thunar are default applications of the Hyprland session (essentials), not add-ons."""

    def setUp(self):
        self.manifests = mf.load_dir(os.path.join(REPO, "profiles"))

    def packages(self, ids):
        return {p for mid in mf.closure(self.manifests, ids) for p in self.manifests[mid].packages}

    def test_essentials_have_kitty_and_thunar(self):
        for pid in ("base", "cyber", "developer", "custom"):
            pk = self.packages([pid])
            self.assertIn("kitty", pk, pid)
            self.assertIn("thunar", pk, pid)

    def test_no_second_terminal_or_file_manager(self):
        pk = self.packages(["base"])
        self.assertEqual(pk & (OTHER_TERMINALS - {"kitty"}), set())
        self.assertEqual(pk & (OTHER_FILE_MANAGERS - {"thunar"}), set())

    def test_kitty_and_thunar_are_no_longer_add_ons(self):
        self.assertNotIn("addon-kitty", self.manifests)
        self.assertNotIn("addon-thunar", self.manifests)

    def test_folders_open_in_thunar(self):
        with open(os.path.join(REPO, "profile", "airootfs", "etc", "xdg", "mimeapps.list"), encoding="utf-8") as f:
            text = f.read()
        lines = [l for l in text.splitlines() if l.startswith("inode/directory=")]
        self.assertEqual(lines, ["inode/directory=thunar.desktop;"])


if __name__ == "__main__":
    unittest.main()
