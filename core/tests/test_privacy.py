import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fakes import FakeSystem  # noqa: E402
from heiss_core import answers as ans, apply as ap, cli, manifest as mf, privacy as pv, resolver  # noqa: E402
from heiss_core.errors import ValidationError  # noqa: E402

PROFILES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "profiles")
EMPTY = {"schema_version": 1, "applied": {"profile": None, "addons": []}, "packages": [], "services": [], "flatpaks": []}


def plan(level, system=None):
    m = mf.load_dir(PROFILES)
    return resolver.resolve(ans.validate({"profile": "base"}), m, dict(EMPTY), system or FakeSystem(), privacy=level)


class Data(unittest.TestCase):
    def test_levels_match_the_answers_schema(self):
        self.assertEqual(pv.LEVELS, ans.PRIVACY)

    def test_every_level_has_one_dropin_under_networkmanager_conf_d(self):
        for lv in pv.LEVELS:
            (d,) = pv.dropins(lv)
            self.assertEqual(d["path"], pv.NM_DROPIN)
            self.assertTrue(d["path"].startswith("/etc/NetworkManager/conf.d/"))
            self.assertIn("(privacy level: %s)" % lv, d["content"])

    def test_levels_differ_and_get_stricter(self):
        c = {lv: pv.dropins(lv)[0]["content"] for lv in pv.LEVELS}
        self.assertIn("wifi.cloned-mac-address=preserve", c["standard"])
        self.assertIn("wifi.cloned-mac-address=stable", c["enhanced"])
        self.assertIn("wifi.cloned-mac-address=random", c["maximum"])
        self.assertIn("ethernet.cloned-mac-address=stable", c["maximum"])
        t = {lv: int(next(k["value"] for k in pv.kde_settings(lv) if k["key"] == "Timeout")) for lv in pv.LEVELS}
        self.assertGreater(t["standard"], t["enhanced"])
        self.assertGreater(t["enhanced"], t["maximum"])

    def test_screen_lock_keys_are_kscreenlocker_daemon_keys(self):
        for lv in pv.LEVELS:
            ks = pv.kde_settings(lv)
            self.assertEqual({(k["file"], k["group"]) for k in ks}, {("kscreenlockerrc", "Daemon")})
            self.assertEqual({k["key"] for k in ks}, {"Autolock", "Timeout", "LockGrace"})
            self.assertTrue(all(isinstance(k["value"], str) for k in ks))

    def test_unknown_level_is_rejected(self):
        for bad in ("", "paranoid", None, "../x"):
            with self.assertRaises(ValidationError):
                pv.dropins(bad)
            with self.assertRaises(ValidationError):
                pv.kde_settings(bad)


class InPlan(unittest.TestCase):
    def test_no_level_means_privacy_is_left_alone(self):
        p = plan(None)
        self.assertEqual(p.privacy, "")
        self.assertFalse([k for k in p.kde_settings if k["file"] == "kscreenlockerrc"])
        self.assertNotIn("WritePrivacy", [c[0] for c in ap.build_calls(p)])

    def test_level_plans_the_dropin_call_and_kde_keys(self):
        p = plan("enhanced")
        self.assertEqual(p.privacy, "enhanced")
        self.assertIn("privacy level: enhanced", p.to_text())
        calls = ap.build_calls(p)
        self.assertIn(("WritePrivacy", ("enhanced",), "write the enhanced privacy settings"), calls)
        self.assertEqual(len([k for k in p.kde_settings if k["file"] == "kscreenlockerrc"]), 3)
        self.assertNotIn("Network", repr([c[1] for c in calls if c[0] == "WritePrivacy"]))   # a name only, never content

    def test_idempotent_when_the_system_already_matches(self):
        kde = {(k["file"], k["group"], k["key"]): k["value"] for k in pv.kde_settings("maximum")}
        sysm = FakeSystem(files={pv.NM_DROPIN: pv.dropins("maximum")[0]["content"]}, kde=kde)
        p = plan("maximum", sysm)
        self.assertEqual(p.privacy, "")
        self.assertFalse([k for k in p.kde_settings if k["file"] == "kscreenlockerrc"])

    def test_lowering_the_level_rewrites_both(self):
        kde = {(k["file"], k["group"], k["key"]): k["value"] for k in pv.kde_settings("maximum")}
        sysm = FakeSystem(files={pv.NM_DROPIN: pv.dropins("maximum")[0]["content"]}, kde=kde)
        p = plan("standard", sysm)
        self.assertEqual(p.privacy, "standard")
        self.assertTrue(any(k["key"] == "Timeout" and k["value"] == "5" for k in p.kde_settings))

    def test_order_privacy_write_is_before_removals_and_post_actions(self):
        methods = [c[0] for c in ap.build_calls(plan("maximum"))]
        self.assertLess(methods.index("WritePrivacy"), methods.index("RunPostAction"))

    def test_only_privacy_to_do_is_not_an_empty_plan(self):
        m = mf.load_dir(PROFILES)
        p = plan("maximum")
        done = FakeSystem(installed=p.next_state["packages"], services=p.next_state["services"],
                          files={d["path"]: d["content"] for d in p.dropins})
        p2 = resolver.resolve(ans.validate({"profile": "base"}), m, p.next_state, done, privacy="maximum")
        self.assertEqual(p2.privacy, "maximum")
        self.assertFalse(p2.is_empty())


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        rc = cli.main(["--profiles", PROFILES] + list(argv), system=FakeSystem(), out=out)
        return rc, out.getvalue()

    def test_dry_run_with_privacy(self):
        rc, text = self.run_cli("profile", "diff", "--profile", "base", "--privacy", "maximum")
        self.assertEqual(rc, 0)
        self.assertIn("privacy level: maximum", text)

    def test_without_the_flag_nothing_about_privacy(self):
        _, text = self.run_cli("profile", "diff", "--profile", "base")
        self.assertNotIn("privacy", text)

    def test_unknown_level_is_refused_by_the_parser(self):
        with self.assertRaises(SystemExit):
            self.run_cli("profile", "diff", "--profile", "base", "--privacy", "paranoid")


if __name__ == "__main__":
    unittest.main()
