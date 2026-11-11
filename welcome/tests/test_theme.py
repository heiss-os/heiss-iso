import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import wizard as wz  # noqa: E402
from heiss_welcome.app import build  # noqa: E402
from heiss_welcome.theme import LNF, apply_theme  # noqa: E402

PROFILES = os.path.join(REPO, "profiles")


class Run:
    def __init__(self, rc=0, err="", raises=None):
        self.calls, self.rc, self.err, self.raises = [], rc, err, raises

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if self.raises:
            raise self.raises
        return subprocess.CompletedProcess(argv, self.rc, "", self.err)


class ApplyTheme(unittest.TestCase):
    def test_dark_and_light_use_the_heiss_look_and_feel(self):
        for theme, lnf in (("dark", "org.heiss.dark.desktop"), ("light", "org.heiss.light.desktop")):
            run = Run()
            self.assertEqual(apply_theme(theme, run), (True, ""))
            self.assertEqual(run.calls, [["plasma-apply-lookandfeel", "--apply", lnf]])

    def test_auto_changes_nothing(self):
        run = Run()
        self.assertEqual(apply_theme("auto", run), (True, ""))
        self.assertEqual(run.calls, [])

    def test_failures_are_reported_not_raised(self):
        ok, msg = apply_theme("dark", Run(rc=1, err="No such package\nCould not find theme"))
        self.assertFalse(ok)
        self.assertEqual(msg, "Could not find theme")
        ok, msg = apply_theme("dark", Run(raises=FileNotFoundError("plasma-apply-lookandfeel")))
        self.assertFalse(ok)
        self.assertIn("cannot switch the theme", msg)

    def test_the_ids_match_the_shipped_look_and_feel_packages(self):
        for lnf in LNF.values():
            self.assertTrue(os.path.isdir(os.path.join(REPO, "profile", "airootfs", "usr", "share", "plasma",
                                                       "look-and-feel", lnf)), lnf)


class Wizard(unittest.TestCase):
    def vm(self, d, fn):
        vm, _ = build(d, PROFILES, theme_applier=fn)
        vm._spawn = lambda f: f()
        vm.w.step = wz.IDS.index("appearance")
        return vm

    def test_choosing_dark_or_light_switches_the_desktop(self):
        seen = []
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, lambda t: (seen.append(t), (True, ""))[1])
            vm.choose("appearance.theme", "light")
            vm.choose("appearance.theme", "auto")
            self.assertEqual(seen, ["light", "auto"])
            self.assertEqual(vm.w.answers["appearance"]["theme"], "auto")

    def test_a_rejected_choice_switches_nothing(self):
        seen = []
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, lambda t: (seen.append(t), (True, ""))[1])
            self.assertTrue(vm.choose("appearance.theme", "purple")["error"])
            self.assertEqual(seen, [])

    def test_a_failed_switch_is_a_note_and_never_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, lambda t: (False, "Could not find theme"))
            scr = vm.choose("appearance.theme", "dark")
            self.assertEqual(vm.screen()["note"], "Could not find theme")
            self.assertEqual(vm.screen()["error"], "")
            self.assertEqual(vm.next()["id"], "privacy")
            self.assertEqual(vm.screen()["note"], "")           # shown on the appearance screen only

    def test_an_exception_in_the_switch_is_a_note(self):
        def boom(t):
            raise RuntimeError("kaput")
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, boom)
            vm.choose("appearance.theme", "dark")
            self.assertEqual(vm.screen()["note"], "kaput")

    def test_jobs_started_out_of_order_leave_the_newest_choice(self):
        seen, jobs = [], []
        with tempfile.TemporaryDirectory() as d:
            vm, _ = build(d, PROFILES, theme_applier=lambda t: (seen.append(t), (True, ""))[1])
            vm._spawn = jobs.append                   # the jobs wait: they will run in the wrong order
            vm.w.step = wz.IDS.index("appearance")
            vm.choose("appearance.theme", "dark")
            vm.choose("appearance.theme", "light")
            for job in reversed(jobs):                # light first, then the stale dark job
                job()
            self.assertEqual(seen, ["light"])
            self.assertEqual(vm.w.answers["appearance"]["theme"], "light")

    def test_a_stale_failure_does_not_overwrite_the_newest_note(self):
        with tempfile.TemporaryDirectory() as d:
            results = {"dark": (False, "old failure"), "light": (True, "")}
            vm, _ = build(d, PROFILES, theme_applier=lambda t: results[t])
            jobs = []
            vm._spawn = jobs.append
            vm.w.step = wz.IDS.index("appearance")
            vm.choose("appearance.theme", "dark")
            vm.choose("appearance.theme", "light")
            for job in jobs:                          # dark is stale: skipped; light succeeds
                job()
            self.assertEqual(vm.screen()["note"], "")

    def test_without_a_theme_applier_choosing_still_works(self):
        with tempfile.TemporaryDirectory() as d:
            vm = self.vm(d, None)
            self.assertEqual(vm.choose("appearance.theme", "dark")["error"], "")


if __name__ == "__main__":
    unittest.main()
