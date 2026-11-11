import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fakes import FakeSystem  # noqa: E402
from heiss_core import answers as ans, apply as ap, cli, hardware as hw, manifest as mf, resolver  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
PROFILES = os.path.join(ROOT, "profiles")
HARDWARE = os.path.join(ROOT, "hardware")
EMPTY = {"schema_version": 1, "applied": {"profile": None, "addons": []}, "packages": [], "services": [], "flatpaks": []}


class Helper:
    def __init__(self):
        self.calls = []

    def call(self, method, args, on_output):
        self.calls.append((method, args))


class Local:
    def kwriteconfig(self, *a):
        pass


class HardwareInPlan(unittest.TestCase):
    def setUp(self):
        self.m = mf.load_dir(PROFILES)
        self.cat = hw.load_profiles(HARDWARE)

    def plan(self, ids=(), state=None, system=None, catalog=None):
        a = ans.validate({"profile": "base"})
        return resolver.resolve(a, self.m, state or dict(EMPTY), system or FakeSystem(), False,
                                hardware=[self.cat[i] for i in ids], catalog=catalog)

    def test_chosen_profile_adds_packages_services_and_is_listed(self):
        p = self.plan(["vm-virtualbox"])
        self.assertIn("virtualbox-guest-utils", p.install_packages)
        self.assertIn("vboxservice.service", p.enable_services)
        self.assertEqual(p.hardware, ["vm-virtualbox"])
        self.assertIn("hardware profiles: vm-virtualbox", p.to_text())
        self.assertNotIn("virtualbox-guest-utils", self.plan().install_packages)

    def test_dropins_and_post_actions_of_the_profile_are_planned_but_kernel_params_are_not(self):
        p = self.plan(["gpu-nvidia-open"])
        self.assertIn("nvidia-open", p.install_packages)
        self.assertIn("/etc/mkinitcpio.conf.d/heiss-nvidia.conf", [d["path"] for d in p.dropins])
        self.assertIn("mkinitcpio", p.post_actions)
        self.assertEqual(len(p.notes), 1)
        self.assertIn("nvidia-drm.modeset=1", p.notes[0])
        self.assertIn("not applied", p.notes[0])

    def test_calls_go_through_the_helper_in_the_usual_order(self):
        calls = ap.build_calls(self.plan(["vm-virtualbox"]))
        install = [c for c in calls if c[0] == "InstallPackages"][0]
        self.assertIn("virtualbox-guest-utils", install[1][0])

    def test_applied_hardware_stays_wanted_when_the_profile_changes(self):
        first = self.plan(["vm-virtualbox"])
        system = FakeSystem(installed=first.next_state["packages"], services=first.next_state["services"],
                            files={d["path"]: d["content"] for d in first.dropins})
        # a later apply that does not name the hardware: the catalog keeps it wanted, nothing is removed
        later = self.plan([], state=first.next_state, system=system, catalog=self.cat)
        self.assertEqual(later.remove_packages, [])
        self.assertEqual(later.hardware, ["vm-virtualbox"])
        # without the catalog the driver would be proposed for removal
        naive = self.plan([], state=first.next_state, system=system)
        self.assertIn("virtualbox-guest-utils", naive.remove_packages)

    def test_profiles_whose_packages_the_profile_already_wants_are_not_listed(self):
        first = self.plan([])           # a plain Base install owns intel-ucode, amd-ucode, vulkan-radeon ...
        later = self.plan([], state=dict(EMPTY, packages=first.next_state["packages"]), catalog=self.cat)
        self.assertEqual(later.hardware, [])

    def test_sticky_needs_every_package_owned(self):
        self.assertEqual(resolver.sticky_hardware(self.cat, dict(EMPTY)), [])
        self.assertEqual(resolver.sticky_hardware(self.cat, dict(EMPTY, packages=["nvidia-open"])), [])


class Cli(unittest.TestCase):
    def run_cli(self, *argv, state=None):
        out = io.StringIO()
        env = {k: os.environ.get(k) for k in ("HEISS_HARDWARE", "HEISS_STATE")}
        os.environ["HEISS_HARDWARE"] = HARDWARE
        os.environ["HEISS_STATE"] = state or "/nonexistent/state.json"
        try:
            rc = cli.main(["--profiles", PROFILES] + list(argv), system=FakeSystem(), out=out)
        finally:
            for k, v in env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        return rc, out.getvalue()

    def test_dry_run_with_a_hardware_profile(self):
        rc, text = self.run_cli("profile", "apply", "--dry-run", "--profile", "base", "--hardware", "vm-virtualbox")
        self.assertEqual(rc, 0)
        self.assertIn("virtualbox-guest-utils", text)
        self.assertIn("hardware profiles: vm-virtualbox", text)

    def test_json_plan_carries_the_hardware_ids(self):
        import json
        rc, text = self.run_cli("--json", "profile", "apply", "--dry-run", "--profile", "base", "--hardware", "vm-virtualbox")
        self.assertEqual(json.loads(text)["hardware"], ["vm-virtualbox"])

    def test_unknown_hardware_profile_is_an_error(self):
        rc, _ = self.run_cli("profile", "apply", "--dry-run", "--profile", "base", "--hardware", "nosuch")
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
