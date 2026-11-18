import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import hyprcfg  # noqa: E402
from heiss_welcome import model  # noqa: E402

SHIPPED = os.path.join(REPO, "desktop", "hypr", "hyprland.lua")


def put(d, text=None):
    os.makedirs(os.path.join(d, "hypr"), exist_ok=True)
    if text is None:
        with open(SHIPPED, encoding="utf-8") as f:
            text = f.read()
    with open(os.path.join(d, "hypr", "hyprland.lua"), "w", encoding="utf-8") as f:
        f.write(text)


class Screen(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)

    def test_rows_come_from_the_active_configuration(self):
        put(self.d)
        s = model.screen("en", self.d)
        self.assertEqual(len(s["rows"]), len(hyprcfg.load(self.d).bindings))
        first = s["rows"][0]
        self.assertEqual((first["keys"], first["description"]), ("Alt + Enter", "Open the terminal"))
        self.assertEqual(s["mainKey"], "Main key: Alt")
        self.assertEqual(s["empty"], "")

    def test_switching_the_modifier_changes_every_row_and_the_main_key_line(self):
        put(self.d)
        hyprcfg.write_modifier(self.d, "SUPER")
        s = model.screen("en", self.d)
        self.assertEqual(s["mainKey"], "Main key: Super")
        self.assertEqual(s["rows"][0]["keys"], "Super + Enter")
        self.assertFalse([r for r in s["rows"] if r["keys"].startswith("Alt")])

    def test_own_configuration_is_reported_as_not_switchable(self):
        put(self.d, 'local mainMod = "SUPER"\n-- Terminal\nhl.bind(mainMod .. " + T", f())\n')
        s = model.screen("ru", self.d)
        self.assertIn("mainMod", s["mainKeyNote"])
        self.assertEqual(s["rows"], [{"keys": "Super + T", "description": "Terminal"}])

    def test_key_names_are_localised(self):
        put(self.d)
        s = model.screen("ru", self.d)
        keys = [r["keys"] for r in s["rows"]]
        self.assertIn("Alt + стрелка влево", keys)
        self.assertIn("Alt + левая кнопка мыши", keys)
        self.assertIn("Громкость выше", keys)
        en = [r["keys"] for r in model.screen("en", self.d)["rows"]]
        self.assertIn("Alt + Left arrow", en)
        self.assertIn("Alt + 1", en)
        self.assertIn("Alt + Shift + E", en)

    def test_search_filters_keys_and_descriptions_and_says_so_when_nothing_matches(self):
        put(self.d)
        self.assertEqual({r["description"] for r in model.screen("en", self.d, "workspace 2")["rows"]},
                         {"Go to workspace 2", "Move the window to workspace 2"})
        self.assertTrue(model.screen("en", self.d, "volume")["rows"])
        s = model.screen("en", self.d, "zzzz")
        self.assertEqual((s["rows"], s["empty"]), ([], "Nothing matches."))

    def test_missing_configuration_gives_a_message_not_an_exception(self):
        s = model.screen("en", self.d)
        self.assertEqual(s["rows"], [])
        self.assertIn("could not be read", s["empty"])

    def test_undescribed_and_unresolved_bindings_are_shown_honestly(self):
        put(self.d, 'hl.bind("SUPER + X", f())\nhl.bind(odd(), f())\n')
        rows = model.screen("en", self.d)["rows"]
        self.assertEqual(rows[0]["keys"], "Super + X")
        self.assertIn("no description", rows[0]["description"])
        self.assertIn("odd", rows[1]["keys"])
        self.assertIn("cannot read", rows[1]["description"])


class FirstRun(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.live = os.path.join(self.d, "archiso")

    def test_first_run_shows_once_and_never_in_the_live_session(self):
        self.assertTrue(model.should_show(True, False, self.d, self.live))
        model.mark_done(self.d)
        self.assertFalse(model.should_show(True, False, self.d, self.live))
        self.assertTrue(model.should_show(True, True, self.d, self.live))      # --force
        self.assertTrue(model.should_show(False, False, self.d, self.live))    # started by hand
        d2 = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d2)
        open(self.live, "w").close()
        self.assertFalse(model.should_show(True, False, d2, self.live))
        self.assertTrue(model.should_show(True, True, d2, self.live))


class KeyLabels(unittest.TestCase):
    def test_labels(self):
        for key, en in (("ALT", "Alt"), ("SUPER", "Super"), ("Return", "Enter"), ("e", "E"), ("1", "1"), ("F1", "F1"),
                        ("XF86Unknown", "XF86Unknown"), ("mouse:272", "left mouse button")):
            self.assertEqual(model.key_label("en", key), en)


if __name__ == "__main__":
    unittest.main()
