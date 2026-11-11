import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import wizard as wz  # noqa: E402
from heiss_core.errors import HeissError  # noqa: E402
from heiss_welcome import strings  # noqa: E402
from heiss_welcome.app import build  # noqa: E402
from heiss_welcome.applier import CliApplier  # noqa: E402

PROFILES = os.path.join(REPO, "profiles")
PLAN = {"install_packages": ["a", "b"], "remove_packages": [], "enable_services": ["x.service"], "disable_services": []}


class FakeApplier:
    def __init__(self, plan=PLAN, plan_error=None, failures=0):
        self._plan, self.plan_error, self.failures, self.runs = plan, plan_error, failures, []

    def plan(self, answers):
        if self.plan_error:
            raise HeissError(self.plan_error)
        return self._plan

    def run(self, answers, on_line, on_step):
        self.runs.append((answers["profile"], list(answers["addons"])))
        on_step(1, 2, "install 2 package(s)")
        on_line("downloading")
        if self.failures:
            self.failures -= 1
            raise HeissError("no network connection, nothing was changed")
        on_step(2, 2, "enable 1 service(s)")


def at_summary(tmp, applier):
    vm, store = build(tmp, PROFILES, applier=applier)
    vm._spawn = lambda fn: fn()          # run the job synchronously in tests
    while vm.w.step_id != wz.SUMMARY:
        vm.next() if not vm.w.can_skip() else vm.skip()
    return vm, store


class ApplyFlow(unittest.TestCase):
    def test_summary_lists_the_plan_and_offers_apply(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, FakeApplier())
            s = vm.screen()
            self.assertTrue(s["canApply"])
            self.assertTrue(any(l.endswith(": 2") for l in s["lines"]))
            self.assertTrue(s["canSaveLater"])

    def test_empty_plan_says_nothing_to_change(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, FakeApplier(plan={}))
            self.assertIn(strings.t("en", "plan.nothing"), vm.screen()["lines"])

    def test_plan_failure_blocks_apply_but_not_saving(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, FakeApplier(plan_error="boom"))
            s = vm.screen()
            self.assertFalse(s["canApply"])
            self.assertTrue(s["canSaveLater"])
            self.assertTrue(any("boom" in l for l in s["lines"]))

    def test_without_an_applier_nothing_changes(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, None)
            s = vm.screen()
            self.assertFalse(s["canApply"])
            self.assertEqual(s["what"], strings.t("en", "summary.what"))
            vm.start_apply()
            self.assertNotEqual(vm.error, "")
            self.assertEqual(vm.w.step_id, wz.SUMMARY)

    def test_successful_apply_ends_done_and_saves_answers(self):
        with tempfile.TemporaryDirectory() as d:
            ap = FakeApplier()
            vm, store = at_summary(d, ap)
            s = vm.start_apply()
            self.assertEqual(s["id"], wz.DONE)
            self.assertEqual(s["title"], strings.t("en", "done.title_applied"))
            self.assertEqual(s["what"], strings.t("en", "done.applied"))
            self.assertTrue(store.is_done())
            self.assertTrue(os.path.exists(os.path.join(d, "answers.toml")))
            self.assertEqual(ap.runs, [("base", [])])
            self.assertEqual(vm.queue.list(), [])

    def test_failure_keeps_applying_screen_with_the_error_and_retry_works(self):
        with tempfile.TemporaryDirectory() as d:
            ap = FakeApplier(failures=1)
            vm, store = at_summary(d, ap)
            s = vm.start_apply()
            self.assertEqual(s["id"], wz.APPLYING)
            self.assertTrue(s["canRetry"] and s["canSaveLater"] and not s["canBack"])
            self.assertIn("no network", s["error"])
            self.assertEqual(s["job"]["step"], "[1/2] install 2 package(s)")
            self.assertFalse(store.is_done())
            s = vm.retry_apply()
            self.assertEqual(s["id"], wz.DONE)
            self.assertEqual(len(ap.runs), 2)

    def test_failed_apply_can_be_saved_for_later(self):
        with tempfile.TemporaryDirectory() as d:
            vm, store = at_summary(d, FakeApplier(failures=5))
            vm.start_apply()
            s = vm.save_later()
            self.assertEqual(s["id"], wz.DONE)
            self.assertEqual([i["kind"] for i in vm.queue.list()], ["apply-profile"])
            self.assertTrue(store.is_done())

    def test_retry_without_a_failure_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, FakeApplier())
            vm.retry_apply()
            self.assertNotEqual(vm.error, "")

    def test_unexpected_exception_in_the_worker_becomes_a_failure(self):
        class Bad(FakeApplier):
            def run(self, *a):
                raise RuntimeError("kaput")
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, Bad())
            s = vm.start_apply()
            self.assertEqual(s["id"], wz.APPLYING)
            self.assertIn("kaput", s["error"])

    def test_no_second_job_while_running_and_no_save_while_running(self):
        with tempfile.TemporaryDirectory() as d:
            started = []
            vm, _ = at_summary(d, FakeApplier())
            vm._spawn = started.append          # the job never runs
            s = vm.start_apply()
            self.assertTrue(s["isRunning"])
            vm._launch()
            self.assertEqual(len(started), 1)
            vm.save_later()
            self.assertNotEqual(vm.error, "")
            self.assertEqual(vm.w.step_id, wz.APPLYING)

    def test_update_callback_fires_from_the_job(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = at_summary(d, FakeApplier())
            calls = []
            vm.on_update = lambda: calls.append(1)
            vm.start_apply()
            self.assertGreaterEqual(len(calls), 3)

    def test_apply_screens_render_in_both_languages(self):
        for lang in ("en", "ru"):
            with tempfile.TemporaryDirectory() as d:
                vm, _ = at_summary(d, FakeApplier(failures=1))
                vm.choose("language", lang)
                s = vm.start_apply()
                self.assertEqual(s["title"], strings.t(lang, "applying.title"))
                self.assertEqual(s["labels"]["retry"], strings.t(lang, "retry"))


FAKE_CLI = r'''
import json, sys
a = sys.argv[1:]
if "--dry-run" in a:
    if "--addon=--fail-plan" in a: sys.stderr.write("heiss: no such profile\n"); sys.exit(1)
    print(json.dumps({"install_packages": ["p"], "args": a}))
else:
    print("[1/2] install 1 package(s)")
    print("  :: downloading")
    print("[2/2] enable 1 service(s)")
    if "--addon=fail" in a: sys.stderr.write("heiss: step 2 of 2 failed (enable): denied. Steps before it were applied.\n"); sys.exit(1)
    print("done")
'''


class Threads(unittest.TestCase):
    def test_real_thread_gated_job_finishes_on_the_gui_thread(self):
        import threading
        gate, started = threading.Event(), threading.Event()

        class Gated(FakeApplier):
            def run(self, answers, on_line, on_step):
                started.set()
                gate.wait(5)
                super().run(answers, on_line, on_step)
        with tempfile.TemporaryDirectory() as d:
            vm, store = build(d, PROFILES, applier=Gated())
            while vm.w.step_id != wz.SUMMARY:
                vm.next() if not vm.w.can_skip() else vm.skip()
            ready = threading.Event()
            vm.on_update = ready.set
            for _ in range(50):                      # the plan is computed on a worker thread
                if vm.screen()["canApply"]:
                    break
                ready.wait(0.1)
            self.assertTrue(vm.screen()["canApply"])
            s = vm.start_apply()
            self.assertTrue(started.wait(5))
            self.assertTrue(s["isRunning"])
            self.assertFalse(vm.screen()["canSaveLater"])
            vm.save_later()
            self.assertNotEqual(vm.error, "")          # not while running
            self.assertEqual(vm.w.step_id, wz.APPLYING)
            ready.clear()
            gate.set()
            self.assertTrue(ready.wait(5))
            for _ in range(50):
                if vm._status() == "applied" or vm._status() == "ok":
                    break
                ready.wait(0.1)
            s = vm.refresh()                           # what the GUI thread does on the update signal
            self.assertEqual(s["id"], wz.DONE)
            self.assertTrue(store.is_done())

    def test_resume_after_a_close_mid_apply_returns_to_the_summary(self):
        with tempfile.TemporaryDirectory() as d:
            vm, _ = build(d, PROFILES, applier=FakeApplier())
            vm._spawn = lambda fn: None             # the job never finishes: the window was closed
            while vm.w.step_id != wz.SUMMARY:
                vm.next() if not vm.w.can_skip() else vm.skip()
            self.assertTrue(vm.start_apply()["isRunning"])
            vm2, _ = build(d, PROFILES, applier=FakeApplier())
            self.assertEqual(vm2.w.step_id, wz.SUMMARY)

    def test_failed_save_keeps_the_error_visible(self):
        with tempfile.TemporaryDirectory() as d:
            vm, store = at_summary(d, FakeApplier())
            store.save_answers = lambda w: (_ for _ in ()).throw(OSError("disk full"))
            s = vm.start_apply()
            self.assertEqual(s["id"], wz.APPLYING)
            self.assertIn("disk full", s["error"])
            self.assertTrue(s["canRetry"])

    def test_plan_failure_is_tried_again_after_leaving_the_summary(self):
        with tempfile.TemporaryDirectory() as d:
            ap = FakeApplier(plan_error="flaky")
            vm, _ = at_summary(d, ap)
            self.assertFalse(vm.screen()["canApply"])
            vm.back()
            ap.plan_error = None
            vm.next()
            self.assertTrue(vm.screen()["canApply"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.script = os.path.join(self.tmp.name, "fake.py")
        with open(self.script, "w") as f:
            f.write(FAKE_CLI)
        self.ap = CliApplier([sys.executable, self.script])

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_uses_dry_run_with_adopt_profile_and_addons(self):
        plan = self.ap.plan({"profile": "cyber", "addons": ["a1", "a2"]})
        self.assertEqual(plan["install_packages"], ["p"])
        self.assertEqual(plan["args"], ["--json", "profile", "apply", "--dry-run", "--adopt", "--profile=cyber",
                                        "--addon=a1", "--addon=a2"])

    def test_run_streams_steps_and_lines(self):
        steps, lines = [], []
        self.ap.run({"profile": "base", "addons": []}, lines.append, lambda n, t, d: steps.append((n, t, d)))
        self.assertEqual(steps, [(1, 2, "install 1 package(s)"), (2, 2, "enable 1 service(s)")])
        self.assertEqual(lines, ["  :: downloading", "done"])

    def test_failure_message_is_the_heiss_error_line(self):
        with self.assertRaises(HeissError) as cm:
            self.ap.run({"profile": "base", "addons": ["fail"]}, lambda l: None, lambda *a: None)
        self.assertTrue(str(cm.exception).startswith("step 2 of 2 failed"))

    def test_plan_failure_is_a_heiss_error(self):
        with self.assertRaises(HeissError) as cm:
            self.ap.plan({"profile": "base", "addons": ["--fail-plan"]})
        self.assertEqual(str(cm.exception), "no such profile")

    def test_missing_command_is_a_heiss_error(self):
        with self.assertRaises(HeissError):
            CliApplier(["/nonexistent/heiss"]).plan({"profile": "base", "addons": []})


if __name__ == "__main__":
    unittest.main()
