import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from heiss_core import manifest as mf, wizard as wz  # noqa: E402
from heiss_core.errors import HeissError, ValidationError  # noqa: E402
from fakes import FakeSystem  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
MANIFESTS = mf.load_dir(os.path.join(REPO, "profiles"))
IDS = [s for s, _ in wz.STEPS]


def walk_to(w, step_id):
    while w.step_id != step_id:
        if w.step_id == "profile":
            w.set("profile", "base")
        w.next()


class Navigation(unittest.TestCase):
    def test_step_order_matches_the_master_plan(self):
        self.assertEqual(IDS, ["welcome", "profile", "level", "addons", "hardware", "appearance", "privacy",
                               "software", "backups", "summary", "applying", "done"])

    def test_profile_must_be_chosen_to_leave_the_profile_step(self):
        w = wz.Wizard(MANIFESTS)
        w.next()
        self.assertEqual(w.step_id, "profile")
        w.answers["profile"] = "nonexistent"
        with self.assertRaises(ValidationError):
            w.next()

    def test_back_keeps_answers_and_skip_keeps_defaults(self):
        w = wz.Wizard(MANIFESTS)
        w.next(); w.set("profile", "cyber"); w.next()
        w.set("level", "advanced")
        w.next()
        self.assertEqual(w.step_id, "addons")
        w.back(); w.back()
        self.assertEqual(w.step_id, "profile")
        self.assertEqual((w.answers["profile"], w.answers["level"]), ("cyber", "advanced"))
        w.next(); w.next()
        w.skip()
        self.assertEqual(w.step_id, "hardware")
        self.assertEqual(w.answers["addons"], [])

    def test_unskippable_steps(self):
        w = wz.Wizard(MANIFESTS)
        with self.assertRaises(HeissError):
            w.skip()
        walk_to(w, "summary")
        with self.assertRaises(HeissError):
            w.skip()
        with self.assertRaises(HeissError):
            w.next()     # the summary is left by applying or saving

    def test_no_back_at_start_or_after_apply(self):
        w = wz.Wizard(MANIFESTS)
        with self.assertRaises(HeissError):
            w.back()
        w.step = IDS.index("done")
        with self.assertRaises(HeissError):
            w.back()

    def test_progress_counts_screens_without_applying(self):
        w = wz.Wizard(MANIFESTS)
        self.assertEqual(w.progress(), (1, 11))
        w.step = IDS.index("applying")
        self.assertEqual(w.progress(), (10, 11))
        w.step = IDS.index("done")
        self.assertEqual(w.progress(), (11, 11))

    def test_skip_whole_applies_base(self):
        w = wz.Wizard(MANIFESTS, language="ru")
        w.next(); w.set("profile", "cyber")
        w.skip_whole()
        self.assertEqual(w.final_answers()["profile"], "base")
        self.assertEqual(w.final_answers()["addons"], [])
        self.assertTrue(w.skipped)
        self.assertEqual(w.step_id, "done")


class Answers(unittest.TestCase):
    def test_set_validates_and_leaves_state_on_error(self):
        w = wz.Wizard(MANIFESTS)
        before = json.dumps(w.answers, sort_keys=True)
        for path, val in (("appearance.theme", "purple"), ("profile", "nope"), ("addons", ["nope"]),
                          ("nosuch", 1), ("appearance.nosuch", 1), ("schema_version", 9), ("software.flathub", "yes")):
            with self.assertRaises(ValidationError, msg=path):
                w.set(path, val)
        self.assertEqual(json.dumps(w.answers, sort_keys=True), before)
        self.assertEqual(w.touched, set())

    def test_profile_defaults_do_not_override_the_users_choice(self):
        w = wz.Wizard(MANIFESTS)
        w.set("profile", "cyber")
        self.assertEqual(w.answers["privacy"]["level"], "enhanced")
        w.set("privacy.level", "maximum")
        w.set("profile", "base")
        self.assertEqual(w.answers["privacy"]["level"], "maximum")
        w2 = wz.Wizard(MANIFESTS)
        w2.set("profile", "cyber"); w2.set("profile", "base")
        self.assertEqual(w2.answers["privacy"]["level"], "standard")

    def test_every_profile_default_is_a_valid_answer(self):
        for pid in MANIFESTS:
            if MANIFESTS[pid].kind == "profile":
                w = wz.Wizard(MANIFESTS)
                w.set("profile", pid)
                w.final_answers()

    def test_extras_are_typed_and_limited(self):
        w = wz.Wizard(MANIFESTS)
        w.set("extra.accent", "sand")
        w.set("extra.font_scale", 1.25)
        for path, val in (("extra.nosuch", "x"), ("extra.accent", 3), ("extra.hardware_toggles", ["x"])):
            with self.assertRaises(ValidationError, msg=path):
                w.set(path, val)
        self.assertEqual(w.extras, {"accent": "sand", "font_scale": 1.25})

    def test_level_controls_advanced_and_confirmations(self):
        w = wz.Wizard(MANIFESTS)
        self.assertFalse(w.advanced_visible()); self.assertTrue(w.confirmations())
        w.set("level", "advanced")
        self.assertTrue(w.advanced_visible()); self.assertFalse(w.confirmations())


class Resume(unittest.TestCase):
    def test_round_trip_and_interrupted_apply_restarts_at_summary(self):
        with tempfile.TemporaryDirectory() as d:
            store = wz.Store(d)
            w = wz.Wizard(MANIFESTS)
            w.next(); w.set("profile", "developer"); w.next(); w.set("extra.accent", "sand")
            store.save(w)
            r = store.load(MANIFESTS)
            self.assertEqual((r.step_id, r.answers, r.extras, r.touched), (w.step_id, w.answers, w.extras, w.touched))
            w.step = IDS.index("applying")
            store.save(w)
            self.assertEqual(store.load(MANIFESTS).step_id, "summary")

    def test_corrupt_or_foreign_state_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            store = wz.Store(d)
            self.assertIsNone(store.load(MANIFESTS))
            for text in ("{broken", "[]", json.dumps({"version": 99}),
                         json.dumps({"version": 1, "step": "nosuch", "answers": {}}),
                         json.dumps({"version": 1, "step": "profile", "answers": {"profile": "ghost"}}),
                         json.dumps({"version": 1, "step": "profile", "answers": {}, "extras": {"evil": 1}})):
                with open(os.path.join(d, "wizard-state.json"), "w") as f:
                    f.write(text)
                self.assertIsNone(store.load(MANIFESTS), text)

    def test_marker_clears_resume_state_and_saved_answers_validate(self):
        with tempfile.TemporaryDirectory() as d:
            store = wz.Store(os.path.join(d, "heiss"))
            w = wz.Wizard(MANIFESTS)
            w.set("profile", "base")
            store.save(w); store.save_answers(w)
            self.assertFalse(store.is_done())
            store.mark_done()
            self.assertTrue(store.is_done())
            self.assertIsNone(store.load(MANIFESTS))
            from heiss_core import answers as ans
            self.assertEqual(ans.load(store.p("answers.toml"))["profile"], "base")


class Summary(unittest.TestCase):
    def test_summary_plan_is_a_dry_run(self):
        w = wz.Wizard(MANIFESTS)
        w.set("profile", "base")
        system = FakeSystem(installed=["bash"])
        plan = wz.summary_plan(w, MANIFESTS, {"schema_version": 1, "applied": {"profile": None, "addons": []},
                                              "packages": [], "services": [], "flatpaks": []}, system)
        self.assertFalse(plan.is_empty())
        self.assertEqual(system.installed, {"bash"})     # nothing was changed


class Pending(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.q = wz.PendingQueue(os.path.join(self.d.name, "pending.json"))
        self.addCleanup(self.d.cleanup)

    def test_add_list_remove_and_kinds(self):
        a = self.q.add("apply-profile", {"profile": "base", "addons": []}, now=1)
        b = self.q.add("apply-profile", {"profile": "cyber", "addons": []}, now=2)
        self.assertEqual([i["id"] for i in self.q.list()], [a["id"], b["id"]])
        with self.assertRaises(ValidationError):
            self.q.add("rm -rf", {})
        self.q.remove(a["id"])
        self.assertEqual([i["id"] for i in self.q.list()], [b["id"]])

    def test_offline_runs_nothing(self):
        self.q.add("apply-profile", {"profile": "base", "addons": []})
        calls = []
        self.assertEqual(self.q.run(calls.append, online=False), [])
        self.assertEqual(calls, [])
        self.assertEqual(len(self.q.list()), 1)

    def test_online_runs_in_order_and_failure_keeps_the_item(self):
        ids = [self.q.add("apply-profile", {"profile": p, "addons": []})["id"] for p in ("base", "cyber", "developer")]
        seen = []

        def ex(item):
            seen.append(item["payload"]["profile"])
            if item["payload"]["profile"] == "cyber":
                raise HeissError("no space left")
        self.assertEqual(self.q.run(ex, online=True), [ids[0]])
        self.assertEqual(seen, ["base", "cyber"])          # stops at the first failure
        left = self.q.list()
        self.assertEqual([i["payload"]["profile"] for i in left], ["cyber", "developer"])
        self.assertEqual((left[0]["status"], left[0]["error"]), ("failed", "no space left"))
        self.assertEqual(self.q.run(lambda i: None, online=True), ids[1:])   # retry works
        self.assertEqual(self.q.list(), [])

    def test_queue_apply_stores_only_profile_and_addons(self):
        w = wz.Wizard(MANIFESTS)
        w.set("profile", "base")
        item = wz.queue_apply(self.q, w)
        self.assertEqual(item["payload"], {"profile": "base", "addons": []})

    def test_corrupt_queue_is_an_error_not_silently_dropped(self):
        with open(self.q.path, "w") as f:
            f.write("{oops")
        with self.assertRaises(ValidationError):
            self.q.list()


if __name__ == "__main__":
    unittest.main()
