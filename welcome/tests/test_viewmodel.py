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



class HardwareAndPrivacy(unittest.TestCase):
    FIX = os.path.join(REPO, "core", "tests", "fixtures", "hw")

    def detector(self, name):
        from heiss_core import hardware as hw
        return lambda: hw.detect(hw.load_fixture(os.path.join(self.FIX, name)),
                                 hw.load_profiles(os.path.join(REPO, "hardware")))

    def vm(self, d, detector):
        vm, _ = build(d, PROFILES, detector)
        vm.w.step = wz.IDS.index("hardware")
        return vm

    def fixture(self):
        return "virtualbox-vmsvga"

    def test_detected_machine_shows_facts_and_proposals(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector(self.fixture()))
            scr = vm.screen()
            self.assertTrue(scr["facts"])
            opts = [o for q in scr["questions"] for o in q["options"]]
            self.assertTrue(opts)
            self.assertTrue(all(o["path"] == "hardware" for o in opts))

    def test_safe_proposals_start_ticked_and_toggle_into_extras(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector(self.fixture()))
            prop = vm.report().proposals[0]
            first = vm.screen()["questions"][0]["options"][0]
            self.assertEqual(first["selected"], prop.safe_by_default)
            vm.toggle_hardware(prop.id)
            self.assertEqual(vm.w.extras["hardware_toggles"][prop.id], not prop.safe_by_default)
            self.assertNotIn("hardware_toggles", vm.w.final_answers())   # extras never leak into answers
            vm2, _ = build(d, PROFILES)
            self.assertEqual(vm2.w.extras["hardware_toggles"][prop.id], not prop.safe_by_default)

    def test_unknown_proposal_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector(self.fixture()))
            self.assertTrue(vm.toggle_hardware("nosuch")["error"])
            self.assertEqual(vm.w.extras, {})

    def test_failed_or_missing_detection_does_not_block(self):
        def boom():
            raise OSError("lspci missing")
        for det in (boom, None):
            with tempfile.TemporaryDirectory() as d:
                vm = self.vm(d, det)
                scr = vm.screen()
                self.assertEqual(scr["questions"], [])
                self.assertTrue(scr["facts"])
                self.assertEqual(vm.next()["id"], "appearance")

    def test_privacy_marks_only_the_firewall_as_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = build(d, PROFILES)
            vm.w.step = wz.IDS.index("privacy")
            done = strings.S["en"]["pv.done"]
            facts = vm.screen()["facts"]
            self.assertEqual([f["text"] for f in facts if f["badge"] == done], [strings.S["en"]["pv.firewall"]])
            n = len(facts)
            vm.choose("level", "advanced")
            self.assertEqual(len(vm.screen()["facts"]), n + 1)   # linux-hardened shows for Advanced only


if __name__ == "__main__":
    unittest.main()
