import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fakes import FakeSystem  # noqa: E402
from heiss_core import cli, hardware as hw, hwremove, manifest as mf  # noqa: E402
from heiss_core.errors import ValidationError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
PROFILES = os.path.join(ROOT, "profiles")
HARDWARE = os.path.join(ROOT, "hardware")
NV = ["nvidia-open", "nvidia-utils", "linux-lts", "nvidia-open-lts"]


def state(packages=(), services=(), profile="base", addons=()):
    return {"schema_version": 1, "applied": {"profile": profile, "addons": list(addons)},
            "packages": list(packages), "services": list(services), "flatpaks": []}


class Plan(unittest.TestCase):
    def setUp(self):
        self.m = mf.load_dir(PROFILES)
        self.cat = hw.load_profiles(HARDWARE)

    def plan(self, pid="gpu-nvidia-open", st=None, installed=NV):
        return hwremove.plan_removal(pid, self.cat, self.m, st or state(NV), installed)

    def test_nvidia_removes_the_driver_and_keeps_the_lts_kernel(self):
        p = self.plan()
        self.assertEqual(sorted(p.packages), ["nvidia-open", "nvidia-open-lts", "nvidia-utils"])
        self.assertIn("linux-lts", p.kept)
        self.assertEqual([d["path"] for d in p.dropins], ["/etc/mkinitcpio.conf.d/heiss-nvidia.conf"])
        self.assertEqual(p.post_actions, ["mkinitcpio"])
        self.assertIn("kept linux-lts", p.to_text())

    def test_only_what_heiss_installed_and_what_is_installed(self):
        p = self.plan(st=state(["nvidia-open", "nvidia-utils"]), installed=NV)
        self.assertEqual(sorted(p.packages), ["nvidia-open", "nvidia-utils"])
        p = self.plan(st=state(NV), installed=["nvidia-open"])
        self.assertEqual(p.packages, ["nvidia-open"])

    def test_nothing_to_remove_is_an_error(self):
        for st, inst in ((state(), NV), (state(NV), [])):
            with self.assertRaises(ValidationError):
                self.plan(st=st, installed=inst)
        with self.assertRaises(ValidationError):
            self.plan("no-such-profile")

    def test_a_package_the_applied_profile_wants_stays(self):
        m = dict(self.m)
        base = m["base"]
        m["base"] = type(base)(**{**base.__dict__, "packages": tuple(base.packages) + ("nvidia-utils",)})
        p = hwremove.plan_removal("gpu-nvidia-open", self.cat, m, state(NV), NV)
        self.assertNotIn("nvidia-utils", p.packages)
        self.assertIn("nvidia-utils", p.kept)

    def test_another_hardware_profile_that_is_applied_keeps_its_packages(self):
        # hybrid-nvidia-intel (nvidia-prime) is applied as well: its package is not part of this removal
        st = state(NV + ["nvidia-prime"])
        p = hwremove.plan_removal("hybrid-nvidia-intel", self.cat, self.m, st, NV + ["nvidia-prime"])
        self.assertEqual(p.packages, ["nvidia-prime"])
        self.assertNotIn("nvidia-open", p.packages)

    def test_services_are_disabled_only_when_heiss_enabled_them(self):
        p = hwremove.plan_removal("vm-virtualbox", self.cat, self.m,
                                  state(["virtualbox-guest-utils"], ["vboxservice.service"]), ["virtualbox-guest-utils"])
        self.assertEqual(p.services, ["vboxservice.service"])
        p = hwremove.plan_removal("vm-virtualbox", self.cat, self.m, state(["virtualbox-guest-utils"]), ["virtualbox-guest-utils"])
        self.assertEqual(p.services, [])

    def test_keep_on_remove_must_name_a_package_of_the_profile(self):
        doc = {"schema_version": 1, "id": "x-test", "name": {"en": "a", "ru": "б"}, "description": {"en": "a", "ru": "б"},
               "match": {"virt": "none"}, "packages": ["a"], "keep_on_remove": ["b"]}
        with self.assertRaises(ValidationError):
            hw.parse_profile(doc)


class Cli(unittest.TestCase):
    def run_cli(self, argv, installed=NV, helper=None, yes_to=True, st=None):
        import json
        import tempfile
        d = tempfile.mkdtemp()
        path = os.path.join(d, "state.json")
        with open(path, "w") as f:
            json.dump(st or state(NV), f)
        os.environ["HEISS_STATE"], os.environ["HEISS_HARDWARE"] = path, HARDWARE
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("HEISS_STATE", "HEISS_HARDWARE")])
        out = io.StringIO()
        rc = cli.main(["--profiles", PROFILES] + argv, system=FakeSystem(installed=installed), out=out,
                      helper=helper, confirm=lambda q: yes_to)
        return rc, out.getvalue()

    def test_dry_run_prints_the_plan_and_calls_nothing(self):
        calls = []
        h = type("H", (), {"call": lambda s, m, a, o: calls.append((m, a))})()
        rc, text = self.run_cli(["hw", "remove", "gpu-nvidia-open", "--dry-run"], helper=h)
        self.assertEqual((rc, calls), (0, []))
        self.assertIn("nvidia-open-lts", text)

    def test_confirmed_remove_calls_the_helper_with_the_id_only(self):
        calls = []
        h = type("H", (), {"call": lambda s, m, a, o: calls.append((m, a))})()
        rc, text = self.run_cli(["hw", "remove", "gpu-nvidia-open"], helper=h)
        self.assertEqual((rc, calls), (0, [("RemoveHardware", ("gpu-nvidia-open",))]))

    def test_declined_remove_changes_nothing(self):
        calls = []
        h = type("H", (), {"call": lambda s, m, a, o: calls.append(m)})()
        rc, text = self.run_cli(["hw", "remove", "gpu-nvidia-open"], helper=h, yes_to=False)
        self.assertEqual((rc, calls), (1, []))
        self.assertIn("cancelled", text)

    def test_nothing_installed_is_a_clean_error(self):
        rc, _ = self.run_cli(["hw", "remove", "gpu-nvidia-open"], st=state())
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
