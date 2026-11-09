import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fakes import FakeSystem  # noqa: E402
from heiss_core import answers as ans, apply as ap, cli, manifest as mf, resolver  # noqa: E402
from heiss_core.errors import HeissError  # noqa: E402

PROFILES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "profiles")
EMPTY = {"schema_version": 1, "applied": {"profile": None, "addons": []}, "packages": [], "services": [], "flatpaks": []}


class FakeHelper:
    def __init__(self, fail_at=None):
        self.calls, self.fail_at = [], fail_at

    def call(self, method, args, on_output):
        self.calls.append((method, args))
        on_output("output of " + method)
        if self.fail_at == method:
            raise HeissError("simulated failure")


class FakeLocal:
    def __init__(self):
        self.calls = []

    def kwriteconfig(self, *a):
        self.calls.append(a)


def plan_for(profile, addons=(), state=None, system=None, adopt=False):
    m = mf.load_dir(PROFILES)
    return resolver.resolve(ans.validate({"profile": profile, "addons": list(addons)}), m, state or dict(EMPTY),
                            system or FakeSystem(), adopt)


class Order(unittest.TestCase):
    def test_order_install_first_removal_last(self):
        p1 = plan_for("cyber")
        sysm = FakeSystem(installed=p1.next_state["packages"], services=p1.next_state["services"],
                          files={d["path"]: d["content"] for d in p1.dropins})
        p2 = plan_for("developer", state=p1.next_state, system=sysm)
        methods = [c[0] for c in ap.build_calls(p2)]
        self.assertIn("InstallPackages", methods)
        self.assertIn("RemovePackages", methods)
        self.assertLess(methods.index("InstallPackages"), methods.index("RemovePackages"))

    def test_fresh_install_call_sequence(self):
        calls = ap.build_calls(plan_for("base"))
        self.assertEqual([c[0] for c in calls][:3], ["InstallPackages", "SetServices", "WriteDropin"])
        self.assertEqual(calls[-1][0], "RunPostAction")
        self.assertEqual(calls[1][1][1], [])        # enable-only call: nothing to disable

    def test_adopt_comes_first_and_only_with_flag(self):
        sysm = FakeSystem(installed={"kate"}, explicit={"kate"})
        self.assertEqual(ap.build_calls(plan_for("base", system=sysm, adopt=True))[0][0], "AdoptPackages")
        self.assertNotIn("AdoptPackages", [c[0] for c in ap.build_calls(plan_for("base", system=sysm))])

    def test_client_sends_only_names_and_ids_never_content(self):
        for method, args, _ in ap.build_calls(plan_for("base")):
            flat = repr(args)
            self.assertNotIn("zram-size", flat)      # drop-in content stays in the manifest
        dropin = [c for c in ap.build_calls(plan_for("base")) if c[0] == "WriteDropin"][0]
        self.assertEqual(dropin[1], ("/etc/systemd/zram-generator.conf.d/heiss.conf",))


class Apply(unittest.TestCase):
    def run_apply(self, plan, helper=None, system=None, local=None):
        lines, steps = [], []
        helper = helper or FakeHelper()
        n = ap.apply_plan(plan, helper, system or FakeSystem(), lines.append, local or FakeLocal(),
                          on_step=lambda *a: steps.append(a))
        return n, helper, lines, steps

    def test_runs_all_calls_and_streams_output(self):
        plan = plan_for("base")
        n, helper, lines, steps = self.run_apply(plan)
        self.assertEqual(n, len(ap.build_calls(plan)))
        self.assertEqual([c[0] for c in helper.calls], [c[0] for c in ap.build_calls(plan)])
        self.assertTrue(lines)
        self.assertEqual(steps[0][:2], (1, len(helper.calls)))

    def test_failure_stops_and_names_the_step(self):
        plan = plan_for("base")
        helper = FakeHelper(fail_at="SetServices")
        with self.assertRaises(HeissError) as cm:
            self.run_apply(plan, helper)
        self.assertEqual([c[0] for c in helper.calls], ["InstallPackages", "SetServices"])
        self.assertIn("step 2 of", str(cm.exception))
        self.assertIn("simulated failure", str(cm.exception))
        self.assertIn("Steps before it were applied", str(cm.exception))

    def test_first_step_failure_says_nothing_was_applied(self):
        with self.assertRaises(HeissError) as cm:
            self.run_apply(plan_for("base"), FakeHelper(fail_at="InstallPackages"))
        self.assertIn("Nothing was applied", str(cm.exception))

    def test_offline_refused_before_anything_changes(self):
        helper = FakeHelper()
        with self.assertRaises(HeissError) as cm:
            self.run_apply(plan_for("base"), helper, FakeSystem(online=False))
        self.assertIn("no network", str(cm.exception))
        self.assertEqual(helper.calls, [])

    def test_offline_ok_when_nothing_to_download(self):
        p1 = plan_for("custom")
        sysm = FakeSystem(installed=p1.next_state["packages"], services=p1.next_state["services"], online=False)
        p2 = plan_for("custom", state=p1.next_state, system=sysm)
        n, helper, *_ = self.run_apply(p2, system=sysm)
        self.assertEqual([c[0] for c in helper.calls if c[0] == "InstallPackages"], [])

    def test_flatpaks_refused_before_anything_changes(self):
        plan = plan_for("base")
        plan.install_flatpaks = ["org.example.App"]
        helper = FakeHelper()
        with self.assertRaises(HeissError):
            self.run_apply(plan, helper)
        self.assertEqual(helper.calls, [])

    def test_kde_settings_run_locally_after_helper_calls(self):
        plan = plan_for("base")
        plan.kde_settings = [{"file": "kdeglobals", "group": "General", "key": "ColorScheme", "value": "HeissDark"}]
        local = FakeLocal()
        self.run_apply(plan, local=local)
        self.assertEqual(local.calls, [("kdeglobals", "General", "ColorScheme", "HeissDark")])

    def test_kde_settings_not_written_when_helper_fails(self):
        plan = plan_for("base")
        plan.kde_settings = [{"file": "a", "group": "b", "key": "c", "value": "d"}]
        local = FakeLocal()
        with self.assertRaises(HeissError):
            self.run_apply(plan, FakeHelper(fail_at="InstallPackages"), local=local)
        self.assertEqual(local.calls, [])


class CliApply(unittest.TestCase):
    def run_cli(self, *argv, helper=None, confirm=None, system=None):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            os.environ["HEISS_STATE"] = os.path.join(d, "state.json")
            os.environ["HEISS_ETC"] = d
            rc = cli.main(["--profiles", PROFILES, *argv], system=system or FakeSystem(), out=out,
                          helper=helper, confirm=confirm)
        return rc, out.getvalue()

    def test_yes_applies_through_helper(self):
        helper = FakeHelper()
        rc, text = self.run_cli("profile", "apply", "--profile", "custom", "--yes", helper=helper)
        self.assertEqual(rc, 0)
        self.assertIn("[1/", text)
        self.assertIn("done", text)
        self.assertEqual(helper.calls[0][0], "InstallPackages")

    def test_declined_confirmation_changes_nothing(self):
        helper = FakeHelper()
        rc, text = self.run_cli("profile", "apply", "--profile", "custom", helper=helper, confirm=lambda q: False)
        self.assertEqual(rc, 1)
        self.assertIn("cancelled", text)
        self.assertEqual(helper.calls, [])

    def test_confirmation_shows_plan_first(self):
        rc, text = self.run_cli("profile", "apply", "--profile", "custom", helper=FakeHelper(), confirm=lambda q: False)
        self.assertLess(text.index("install packages"), text.index("cancelled"))

    def test_no_tty_without_yes_refuses(self):
        helper = FakeHelper()
        rc, _ = self.run_cli("profile", "apply", "--profile", "custom", helper=helper)   # stdin is not a tty in tests
        self.assertEqual(rc, 1)
        self.assertEqual(helper.calls, [])

    def test_nothing_to_apply(self):
        p1 = plan_for("custom")
        sysm = FakeSystem(installed=p1.next_state["packages"], services=p1.next_state["services"],
                          files={d["path"]: d["content"] for d in p1.dropins})
        from heiss_core import state as st
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, "state.json")
            st.save(sp, p1.next_state)
            os.environ["HEISS_STATE"], os.environ["HEISS_ETC"] = sp, d
            out, helper = io.StringIO(), FakeHelper()
            rc = cli.main(["--profiles", PROFILES, "profile", "apply", "--profile", "custom", "--yes"],
                          system=sysm, out=out, helper=helper)
        self.assertEqual(rc, 0)
        self.assertIn("nothing to apply", out.getvalue())
        self.assertEqual(helper.calls, [])

    def test_helper_failure_exit_code_and_message(self):
        rc, text = self.run_cli("profile", "apply", "--profile", "custom", "--yes", helper=FakeHelper(fail_at="InstallPackages"))
        self.assertEqual(rc, 1)

    def test_dry_run_never_touches_helper(self):
        helper = FakeHelper()
        rc, _ = self.run_cli("profile", "apply", "--dry-run", "--profile", "custom", helper=helper)
        self.assertEqual(rc, 0)
        self.assertEqual(helper.calls, [])


if __name__ == "__main__":
    unittest.main()
