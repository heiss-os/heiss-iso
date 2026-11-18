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
            vm.next(); vm.next()
            opts = vm.screen()["questions"][0]["options"]
            self.assertEqual({o["value"] for o in opts}, {"base", "cyber", "developer", "custom"})
            self.assertIn("Кибербезопасность", [o["label"] for o in opts])

    def test_a_profile_card_is_preselected(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.next(); vm.next()
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
            vm.toggle_addon("addon-lts-kernel")
            sel = {o["value"] for o in vm.screen()["questions"][0]["options"] if o["selected"]}
            self.assertEqual(sel, {"addon-lts-kernel"})
            vm.toggle_addon("addon-lts-kernel")
            self.assertEqual(vm.w.answers["addons"], [])

    def test_back_skip_and_buttons_state(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            s = vm.screen()
            self.assertTrue(s["isFirst"] and not s["canBack"] and not s["canSkip"])
            vm.next(); vm.next(); vm.choose("profile", "cyber"); vm.next()
            s = vm.screen()
            self.assertEqual((s["id"], s["canSkip"], s["canBack"]), ("level", True, True))
            self.assertEqual(vm.skip()["id"], "addons")
            self.assertEqual(vm.back()["id"], "level")
            self.assertEqual(vm.w.answers["profile"], "cyber")

    def test_summary_lists_profile_and_addons(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.choose("profile", "developer")
            vm.choose("addons", ["addon-lts-kernel"])
            vm.w.step = wz.IDS.index("summary")
            lines = vm.screen()["lines"]
            self.assertEqual(len(lines), 3)       # profile, "Add-ons:", one wrapped line per add-on
            self.assertIn("Developer", lines[0])
            self.assertEqual(lines[1], "Add-ons:")
            self.assertTrue(lines[2].startswith("\u2022 "))


class Order(unittest.TestCase):
    def test_language_then_appearance_then_the_rest_and_the_screen_carries_the_theme(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            self.assertEqual(vm.screen()["id"], "welcome")
            self.assertEqual(vm.next()["id"], "appearance")
            self.assertEqual(vm.choose("appearance.theme", "light")["theme"], "light")
            self.assertEqual(vm.next()["id"], "profile")
            self.assertEqual(vm.screen()["theme"], "light")      # every later page is drawn in the chosen theme

    def test_a_resume_file_of_the_old_order_or_with_an_unknown_step_starts_over(self):
        import json
        for doc in ({"version": 1, "step": "hardware", "answers": {}, "extras": {}, "touched": [], "skipped": False},
                    {"version": wz.STATE_VERSION, "step": "nowhere", "answers": {}, "extras": {}, "touched": [], "skipped": False}):
            with tempfile.TemporaryDirectory() as d:
                with open(os.path.join(d, "wizard-state.json"), "w", encoding="utf-8") as f:
                    json.dump(doc, f)
                vm, _ = vm_in(d)
                self.assertEqual(vm.screen()["id"], "welcome")


class Addons(unittest.TestCase):
    def test_mail_and_office_are_gone_and_the_rest_stays(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.w.step = wz.IDS.index("addons")
            ids = {o["value"] for o in vm.screen()["questions"][0]["options"]}
            self.assertEqual(ids, {"addon-cyber-extended", "addon-developer-extended", "addon-lts-kernel"})
            self.assertFalse([o for o in vm.screen()["questions"][0]["options"] if o["selected"]])
        for name in os.listdir(PROFILES):
            with open(os.path.join(PROFILES, name), encoding="utf-8") as f:
                text = f.read().lower()
            self.assertNotIn("libreoffice", text)
            self.assertNotIn("thunderbird", text)


class Wording(unittest.TestCase):
    def test_intros_have_no_what_will_change_prefix(self):
        for lang, d in strings.S.items():
            for k, v in d.items():
                if k.endswith(".what") or k.startswith("done."):
                    self.assertNotRegex(v, r"^[^.]{0,40}: [A-ZА-Я]", k)
        for lang in ("en", "ru"):
            with tempfile.TemporaryDirectory() as d:
                vm, _ = vm_in(d)
                vm.choose("language", lang)
                with open(os.path.join(REPO, "welcome", "heiss_welcome", "qml", "Main.qml"), encoding="utf-8") as f:
                    self.assertNotIn("whatLabel", f.read())
                self.assertNotIn("whatLabel", vm.screen())

    def test_done_page_names_the_real_place_to_apply(self):
        self.assertIn("Control Center", strings.S["en"]["done.what"])
        self.assertIn("Apply saved actions now", strings.S["en"]["done.what"])
        self.assertIn("Центр управления", strings.S["ru"]["done.what"])
        self.assertNotIn("when", strings.S["en"]["done.what"].lower().split("control center")[0])


class Persistence(unittest.TestCase):
    def test_state_is_saved_and_resumed(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = vm_in(d)
            vm.next(); vm.next(); vm.choose("profile", "cyber"); vm.next()
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

    def test_facts_use_vendor_names_and_one_graphics_line(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector("nvidia-hybrid-laptop"))
            texts = [f["text"] for f in vm.screen()["facts"]]
            self.assertIn("Processor: Intel", texts)
            self.assertEqual([t for t in texts if t.startswith("Graphics")], ["Graphics: Intel and NVIDIA"])
            self.assertFalse([t for t in texts if "GenuineIntel" in t or "8086" in t or "10de" in t])
            self.assertIn("Hybrid graphics (two different vendors)", texts)
            vm.w.set("language", "ru")
            texts = [f["text"] for f in vm.screen()["facts"]]
            self.assertIn("Процессор: Intel", texts)
            self.assertIn("Графика: Intel и NVIDIA", texts)

    def test_nvidia_hint_is_the_short_recovery_step(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector("nvidia-desktop-modern"))
            opts = {o["value"]: o for q in vm.screen()["questions"] for o in q["options"]}
            hint = opts["gpu-nvidia-open"]["hint"]
            self.assertIn("Heiss OS, safe graphics", hint)
            self.assertNotIn("0x1e00", hint)           # the technical detail stays in the Control Center
            self.assertNotIn("nvidia-open-lts", hint)

    def detector_caps(self, name, caps):
        from heiss_core import hardware as hw
        return lambda: hw.detect(hw.load_fixture(os.path.join(self.FIX, name)),
                                 hw.load_profiles(os.path.join(REPO, "hardware")), caps)

    def test_nvidia_is_not_offered_without_the_safe_graphics_entry(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector_caps("nvidia-desktop-modern", set()))
            scr = vm.screen()
            opts = {o["value"] for q in scr["questions"] for o in q["options"]}
            self.assertNotIn("gpu-nvidia-open", opts)
            texts = [f["text"] for f in scr["facts"]]
            self.assertTrue([t for t in texts if "NVIDIA graphics" in t and "safe graphics boot entry" in t], texts)
            # a stale tick cannot sneak the driver into Apply, and toggling it is rejected
            vm.w.set("extra.hardware_toggles", {"gpu-nvidia-open": True})
            self.assertNotIn("gpu-nvidia-open", vm.hardware_ids())
            vm.toggle_hardware("gpu-nvidia-open")
            self.assertNotIn("gpu-nvidia-open", vm.hardware_ids())
            vm.w.set("language", "ru")
            texts = [f["text"] for f in vm.screen()["facts"]]
            self.assertTrue([t for t in texts if "Графика NVIDIA" in t and "safe graphics" in t], texts)

    def test_nvidia_is_offered_when_the_entry_is_installed(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector_caps("nvidia-desktop-modern", {"safe-graphics-entry"}))
            opts = {o["value"] for q in vm.screen()["questions"] for o in q["options"]}
            self.assertIn("gpu-nvidia-open", opts)
            self.assertNotIn("gpu-nvidia-open", vm.hardware_ids())     # never ticked by default

    def nvidia_vm(self, d):
        vm = self.vm(d, self.detector_caps("nvidia-desktop-modern", {"safe-graphics-entry"}))
        vm.snapshot = lambda: False
        return vm

    def confirm_options(self, vm):
        return [o for q in vm.screen()["questions"] if q["title"] for o in q["options"]]

    def test_unsafe_driver_needs_its_own_confirmation_before_it_is_applied(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.nvidia_vm(d)
            self.assertEqual(self.confirm_options(vm), [])          # not ticked: nothing to confirm
            vm.toggle_hardware("gpu-nvidia-open")
            self.assertEqual(vm.unconfirmed_ids(), ["gpu-nvidia-open"])
            self.assertNotIn("gpu-nvidia-open", vm.hardware_ids())  # ticked but not confirmed: not applied
            opts = self.confirm_options(vm)
            self.assertEqual([o["value"] for o in opts], ["confirm:gpu-nvidia-open"])
            self.assertIn("Heiss OS, safe graphics", opts[0]["hint"])
            vm.toggle_hardware("confirm:gpu-nvidia-open")
            self.assertIn("gpu-nvidia-open", vm.hardware_ids())
            self.assertEqual(vm.unconfirmed_ids(), [])

    def test_unticking_forgets_the_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.nvidia_vm(d)
            vm.toggle_hardware("gpu-nvidia-open")
            vm.toggle_hardware("confirm:gpu-nvidia-open")
            vm.toggle_hardware("gpu-nvidia-open")                   # untick
            vm.toggle_hardware("gpu-nvidia-open")                   # tick again
            self.assertNotIn("gpu-nvidia-open", vm.hardware_ids())  # asks again
            self.assertEqual(vm.unconfirmed_ids(), ["gpu-nvidia-open"])

    def test_confirming_an_unticked_or_safe_or_unknown_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.nvidia_vm(d)
            self.assertTrue(vm.toggle_hardware("confirm:gpu-nvidia-open")["error"])   # not ticked
            self.assertTrue(vm.toggle_hardware("confirm:nosuch")["error"])
            self.assertNotIn("hardware_confirmed", vm.w.extras)
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, self.detector(self.fixture()))
            safe = vm.report().proposals[0].id
            self.assertTrue(vm.toggle_hardware("confirm:" + safe)["error"])           # safe by default

    def test_confirmation_text_follows_the_snapshot_and_the_language(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.nvidia_vm(d)
            vm.toggle_hardware("gpu-nvidia-open")
            self.assertIn("no snapshot", self.confirm_options(vm)[0]["hint"].lower())
            vm.snapshot = lambda: True
            self.assertIn("A snapshot is set up", self.confirm_options(vm)[0]["hint"])
            vm.w.set("language", "ru")
            self.assertIn("Снимок настроен", self.confirm_options(vm)[0]["hint"])

    def test_intro_has_no_second_colon_in_either_language(self):
        from heiss_welcome.strings import S
        for lang in S:
            self.assertNotIn(":", S[lang]["hardware.what"], lang)   # the screen already prints "What this will change:" before it

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
                self.assertEqual(vm.next()["id"], "privacy")

    def test_privacy_levels_are_explained_from_what_the_code_writes(self):
        from heiss_core import privacy
        with tempfile.TemporaryDirectory() as d:
            vm, _ = build(d, PROFILES)
            vm.w.step = wz.IDS.index("privacy")
            scr = vm.screen()
            self.assertEqual(len(scr["facts"]), 1)                       # the "can be changed later" line only
            self.assertEqual(scr["facts"][0]["badge"], "")
            hints = {o["value"]: o["hint"] for o in scr["questions"][0]["options"]}
            self.assertEqual(set(hints), set(privacy.LEVELS))
            for level, hint in hints.items():
                self.assertIn("%s minute" % privacy._TABLE[level][2], hint)
            self.assertIn("hardware address", hints["standard"])   # preserve
            self.assertIn("differs from the hardware", hints["enhanced"])   # stable
            self.assertIn("random", hints["maximum"])             # random
            self.assertEqual(privacy._TABLE["standard"][0], "preserve")
            self.assertEqual(privacy._TABLE["enhanced"][0], "stable")
            self.assertEqual(privacy._TABLE["maximum"][0], "random")
            vm.choose("language", "ru")
            self.assertTrue(all(o["hint"] for o in vm.screen()["questions"][0]["options"]))

    def test_no_list_of_works_today_or_coming_soon_on_privacy(self):
        for lang in strings.S.values():
            self.assertFalse([k for k in lang if k.startswith("pv.")])


class QmlPlainText(unittest.TestCase):
    def test_every_qml_text_is_plain_text(self):
        # Text defaults to AutoText: a string from a file or a command that looks like HTML (a package name, an
        # error line, the apply log) would be rendered as rich text, and a remote <img> would fetch from the network
        import re
        qdir = os.path.join(REPO, "welcome", "heiss_welcome", "qml")
        names = sorted(n for n in os.listdir(qdir) if n.endswith(".qml"))
        self.assertIn("ChoiceRow.qml", names)
        total = 0
        for name in names:
            with open(os.path.join(qdir, name), encoding="utf-8") as f:
                qml = f.read()
            items = re.findall(r"(?<![A-Za-z])(Text|Label|TextEdit|TextArea)\s*\{([^\n]*)", qml)
            total += len(items)
            for kind, line in items:
                self.assertEqual(kind, "Text", "use Text with textFormat PlainText, not %s" % kind)
                self.assertIn("textFormat: Text.PlainText", line, name)
        self.assertGreater(total, 10)

    def test_every_choice_list_uses_the_one_shared_row(self):
        qdir = os.path.join(REPO, "welcome", "heiss_welcome", "qml")
        with open(os.path.join(qdir, "Main.qml"), encoding="utf-8") as f:
            main = f.read()
        self.assertEqual(main.count("ChoiceRow {"), 1)           # one delegate for every list
        self.assertNotIn("ItemDelegate", main)
        with open(os.path.join(qdir, "ChoiceRow.qml"), encoding="utf-8") as f:
            row = f.read()
        self.assertNotRegex(row, r"selected \? row\.colors\.(button|panel)")   # the row background ignores `selected`
        self.assertNotRegex(main + row, r'"#[0-9A-Fa-f]{6}"[^\n]*selected')


if __name__ == "__main__":
    unittest.main()
