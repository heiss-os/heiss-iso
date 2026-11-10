import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import manifest as mf, wizard as wz  # noqa: E402
from heiss_welcome import strings  # noqa: E402
from heiss_welcome.app import build  # noqa: E402
from heiss_welcome.viewmodel import ViewModel  # noqa: E402

PROFILES = os.path.join(REPO, "profiles")
MANIFESTS = mf.load_dir(PROFILES)


def vm_in(tmp):
    return build(tmp, PROFILES)


class Strings(unittest.TestCase):
    def test_en_and_ru_have_the_same_keys(self):
        self.assertEqual(set(strings.S["en"]), set(strings.S["ru"]))
        self.assertTrue(all(v.strip() for lang in strings.S.values() for v in lang.values()))

    def test_every_step_has_title_and_what(self):
        for sid, _ in wz.STEPS:
            if sid in (wz.APPLYING, wz.DONE):
                continue
            for lang in strings.S:
                self.assertIn(sid + ".title", strings.S[lang])
                self.assertIn(sid + ".what", strings.S[lang])


class Screens(unittest.TestCase):
    def test_every_screen_renders_in_both_languages(self):
        for lang in ("en", "ru"):
            with tempfile.TemporaryDirectory() as d:
                vm, _ = vm_in(d)
                vm.choose("language", lang)
                for _ in range(len(wz.STEPS)):
                    scr = vm.screen()
                    self.assertTrue(scr["title"] and scr["what"])
                    if vm.w.step_id == "profile":
                        vm.choose("profile", "base")
                    if vm.w.step_id in (wz.SUMMARY, wz.DONE):
                        break
                    vm.next()
                self.assertEqual(vm.w.step_id, wz.SUMMARY)

    def test_profile_cards_hide_essentials_and_follow_language(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.choose("language", "ru")
            vm.next()
            opts = vm.screen()["questions"][0]["options"]
            self.assertEqual({o["value"] for o in opts}, {"base", "cyber", "developer", "custom"})
            self.assertIn("Кибербезопасность", [o["label"] for o in opts])

    def test_a_profile_card_is_preselected(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.next()
            self.assertEqual([o["value"] for o in vm.screen()["questions"][0]["options"] if o["selected"]], ["base"])

    def test_bad_value_shows_error_and_keeps_answers(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            scr = vm.choose("appearance.theme", "purple")
            self.assertTrue(scr["error"])
            self.assertEqual(vm.w.answers["appearance"]["theme"], "auto")
            self.assertEqual(vm.choose("appearance.theme", "dark")["error"], "")

    def test_addon_toggle_selects_and_unselects(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.w.step = wz.IDS.index("addons")
            vm.toggle_addon("addon-office")
            sel = {o["value"] for o in vm.screen()["questions"][0]["options"] if o["selected"]}
            self.assertEqual(sel, {"addon-office"})
            vm.toggle_addon("addon-office")
            self.assertEqual(vm.w.answers["addons"], [])

    def test_back_skip_and_buttons_state(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            s = vm.screen()
            self.assertTrue(s["isFirst"] and not s["canBack"] and not s["canSkip"])
            vm.next(); vm.choose("profile", "cyber"); vm.next()
            s = vm.screen()
            self.assertEqual((s["id"], s["canSkip"], s["canBack"]), ("level", True, True))
            self.assertEqual(vm.skip()["id"], "addons")
            self.assertEqual(vm.back()["id"], "level")
            self.assertEqual(vm.w.answers["profile"], "cyber")

    def test_summary_lists_profile_and_addons(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.choose("profile", "developer")
            vm.choose("addons", ["addon-office"])
            vm.w.step = wz.IDS.index("summary")
            lines = vm.screen()["lines"]
            self.assertEqual(len(lines), 2)
            self.assertIn("Developer", lines[0])


class Persistence(unittest.TestCase):
    def test_state_is_saved_and_resumed(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.next(); vm.choose("profile", "cyber"); vm.next()
            vm2, _ = vm_in(d)
            self.assertEqual(vm2.screen()["id"], "level")
            self.assertEqual(vm2.w.answers["profile"], "cyber")

    def test_save_later_writes_answers_queue_and_marker(self):
        with tempfile.TemporaryDirectory() as d:
            vm, store = vm_in(d)
            vm.choose("profile", "cyber")
            vm.w.step = wz.IDS.index("summary")
            self.assertTrue(vm.save_later()["isDone"])
            self.assertTrue(store.is_done())
            self.assertTrue(os.path.exists(store.p("answers.toml")))
            self.assertFalse(os.path.exists(store.p("wizard-state.json")))
            items = wz.PendingQueue(store.p("pending.json")).list()
            self.assertEqual([i["payload"]["profile"] for i in items], ["cyber"])

    def test_skip_all_marks_done_and_queues_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            vm, store = vm_in(d)
            scr = vm.skip_whole()
            self.assertTrue(scr["isDone"] and store.is_done())
            self.assertEqual(wz.PendingQueue(store.p("pending.json")).list(), [])
            self.assertEqual(vm.w.final_answers()["profile"], "base")

    def test_save_later_is_refused_outside_the_summary(self):
        with tempfile.TemporaryDirectory() as d:
            vm, store = vm_in(d)
            self.assertTrue(vm.save_later()["error"])
            self.assertFalse(store.is_done())


if __name__ == "__main__":
    unittest.main()
