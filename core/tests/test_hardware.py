import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from heiss_core import cli, hardware as hw  # noqa: E402
from heiss_core.errors import ValidationError  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
HARDWARE = os.path.join(REPO, "hardware")
FIX = os.path.join(HERE, "fixtures", "hw")


def plan_for(name):
    r = hw.detect(hw.load_fixture(os.path.join(FIX, name)), hw.load_profiles(HARDWARE))
    return r, {p.id for p in r.proposals}


def good(**over):
    d = {"schema_version": 1, "id": "x", "name": {"en": "X", "ru": "Икс"}, "description": {"en": "d", "ru": "о"},
         "match": {"form_factor": "laptop"}, "packages": ["foo"]}
    d.update(over)
    return d


class Parsing(unittest.TestCase):
    def test_lspci_real_capture(self):
        with open(os.path.join(FIX, "virtualbox-vmsvga", "lspci.txt")) as f:
            devs = hw.parse_lspci(f.read())
        gpu = [d for d in devs if d.cls == "0300"]
        self.assertEqual((gpu[0].vendor, gpu[0].device), ("15ad", "0405"))
        self.assertGreater(len(devs), 8)

    def test_garbage_lines_ignored(self):
        self.assertEqual(hw.parse_lspci("\nnot a device line\n"), [])


class Fixtures(unittest.TestCase):
    def test_intel_laptop(self):
        r, ids = plan_for("intel-igpu-laptop")
        self.assertEqual(r.form_factor, "laptop")
        self.assertTrue({"cpu-microcode-intel", "gpu-intel", "laptop-power"} <= ids)
        self.assertFalse(ids & {"gpu-amd", "gpu-nvidia-open", "wifi-broadcom", "vm-virtualbox"})
        self.assertFalse(r.hybrid_graphics)

    def test_amd_desktop(self):
        r, ids = plan_for("amd-gpu-desktop")
        self.assertEqual(r.form_factor, "desktop")
        self.assertEqual(ids, {"cpu-microcode-amd", "gpu-amd"})

    def test_nvidia_modern_needs_confirmation(self):
        r, ids = plan_for("nvidia-desktop-modern")
        self.assertIn("gpu-nvidia-open", ids)
        nv = next(p for p in r.proposals if p.id == "gpu-nvidia-open")
        self.assertFalse(nv.safe_by_default)
        self.assertIn("nvidia-open", nv.packages)
        self.assertNotIn("gpu-nvidia-legacy", ids)

    def test_nvidia_old_falls_back_to_open_stack_without_aur(self):
        r, ids = plan_for("nvidia-desktop-old")
        self.assertIn("gpu-nvidia-legacy", ids)
        self.assertNotIn("gpu-nvidia-open", ids)
        leg = next(p for p in r.proposals if p.id == "gpu-nvidia-legacy")
        self.assertEqual(leg.packages, ("mesa",))
        self.assertIn("AUR", leg.warnings["en"])

    def test_hybrid_laptop(self):
        r, ids = plan_for("nvidia-hybrid-laptop")
        self.assertTrue(r.hybrid_graphics)
        self.assertTrue({"gpu-intel", "gpu-nvidia-open", "hybrid-nvidia-intel", "laptop-power"} <= ids)
        self.assertNotIn("hybrid-nvidia-amd", ids)

    def test_broadcom_warns_and_never_installs_out_of_tree(self):
        r, ids = plan_for("broadcom-wifi-laptop")
        self.assertIn("wifi-broadcom", ids)
        b = next(p for p in r.proposals if p.id == "wifi-broadcom")
        self.assertEqual(b.packages, ("linux-firmware-broadcom",))
        self.assertIn("out-of-tree", b.warnings["en"])

    def test_virtualbox_real_capture_guest_tools_only(self):
        r, ids = plan_for("virtualbox-vmsvga")
        self.assertEqual(r.form_factor, "vm")
        self.assertEqual(ids, {"vm-virtualbox"})   # no microcode, no GPU driver, no laptop power in a VM

    def test_all_proposals_have_ru_and_en(self):
        for p in hw.load_profiles(HARDWARE).values():
            self.assertTrue(p.name["ru"] and p.description["en"], p.id)

    def test_no_aur_or_dkms_packages_anywhere(self):
        for p in hw.load_profiles(HARDWARE).values():
            for pkg in p.packages:
                self.assertFalse(pkg.endswith("-dkms") or pkg == "broadcom-wl", "%s in %s" % (pkg, p.id))

    def test_safe_by_default_never_installs_nvidia_proprietary(self):
        for p in hw.load_profiles(HARDWARE).values():
            if p.safe_by_default:
                self.assertFalse({"nvidia-open", "nvidia-utils"} & set(p.packages), p.id)


class VendorNames(unittest.TestCase):
    def test_cpu_vendor_names(self):
        self.assertEqual(hw.cpu_vendor_name("GenuineIntel"), "Intel")
        self.assertEqual(hw.cpu_vendor_name("AuthenticAMD"), "AMD")
        self.assertEqual(hw.cpu_vendor_name("HygonGenuine"), "Hygon")
        self.assertEqual(hw.cpu_vendor_name("JohnSmithCPU"), "")   # an unknown raw string is never echoed
        self.assertEqual(hw.cpu_vendor_name(""), "")

    def test_every_fixture_cpu_has_a_name(self):
        for fx in sorted(os.listdir(FIX)):
            f = hw.load_fixture(os.path.join(FIX, fx))
            self.assertTrue(hw.cpu_vendor_name(f.cpu_vendor), (fx, f.cpu_vendor))

    def test_graphics_vendors_once_each_in_detection_order(self):
        r = hw.detect(hw.load_fixture(os.path.join(FIX, "nvidia-hybrid-laptop")), hw.load_profiles(HARDWARE))
        self.assertEqual(hw.gpu_vendor_names(r.gpus), ["Intel", "NVIDIA"])
        self.assertEqual(hw.gpu_vendor_names([{"vendor": "8086"}, {"vendor": "8086"}]), ["Intel"])
        self.assertEqual(hw.gpu_vendor_names([{"vendor": "abcd"}], other="x"), ["x"])
        self.assertEqual(hw.pci_vendor_name("10de"), "NVIDIA")
        self.assertEqual(hw.pci_vendor_name("abcd"), "")


class TrailingNewline(unittest.TestCase):
    """"$" alone lets a trailing newline through; every validator must use fullmatch."""
    BASE = {"schema_version": 1, "id": "x", "name": {"en": "a", "ru": "а"}, "description": {"en": "a", "ru": "а"},
            "match": {"virt": "none"}}

    def bad(self, **change):
        doc = dict(self.BASE)
        doc.update(change)
        with self.assertRaises(ValidationError, msg=str(change)):
            hw.parse_profile(doc)

    def test_profile_id_virt_kernel_params_and_hex_ids_reject_a_trailing_newline(self):
        self.assertEqual(hw.parse_profile(self.BASE).id, "x")
        self.bad(id="x\n")
        self.bad(match={"virt": "oracle\n"})
        self.bad(kernel_params=["quiet\n"])
        self.bad(match={"pci": [{"vendor": "10de\n"}]})
        self.bad(match={"pci": [{"vendor": "10de", "devices": ["1e00\n"]}]})


class RecoveryText(unittest.TestCase):
    def test_recovery_is_optional_and_needs_both_languages(self):
        base = {"schema_version": 1, "id": "x", "name": {"en": "a", "ru": "а"}, "description": {"en": "a", "ru": "а"},
                "match": {"virt": "none"}}
        self.assertEqual(hw.parse_profile(base).recovery, {})
        with self.assertRaises(ValidationError):
            hw.parse_profile(dict(base, recovery={"en": "only english"}))
        ok = hw.parse_profile(dict(base, recovery={"en": "a", "ru": "б"}))
        self.assertEqual(ok.recovery["ru"], "б")

    def test_a_recovery_step_is_the_first_part_of_the_full_warning(self):
        n = 0
        for p in hw.load_profiles(HARDWARE).values():
            if p.recovery:
                n += 1
                for lang in ("en", "ru"):
                    self.assertTrue(p.warnings[lang].startswith(p.recovery[lang]), (p.id, lang))
        self.assertGreaterEqual(n, 1)


class FormFactor(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(hw.Facts(chassis_type=3).form_factor, "desktop")
        self.assertEqual(hw.Facts(chassis_type=10).form_factor, "laptop")
        self.assertEqual(hw.Facts(chassis_type=3, has_battery=True).form_factor, "laptop")
        self.assertEqual(hw.Facts(chassis_type=10, virt="kvm").form_factor, "vm")


class PciThresholds(unittest.TestCase):
    def test_boundaries(self):
        prof = hw.parse_profile(good(match={"pci": [{"vendor": "10de", "device_min": "1e00"}]}))
        mk = lambda d: hw.Facts(pci=[hw.PciDevice("01:00.0", "0300", "10de", d)])  # noqa: E731
        self.assertFalse(hw.matches(prof, mk("1dff")))
        self.assertTrue(hw.matches(prof, mk("1e00")))
        self.assertTrue(hw.matches(prof, mk("2503")))


class Validation(unittest.TestCase):
    def test_shipped_profiles_valid(self):
        self.assertGreaterEqual(len(hw.load_profiles(HARDWARE)), 14)

    def test_rejects_bad_input(self):
        for bad in (good(match={}), good(match={"nope": 1}), good(match={"form_factor": "toaster"}),
                    good(match={"pci": [{"vendor": "10DE"}]}), good(match={"pci": [{"class": "audio"}]}),
                    good(kernel_params=["bad param;rm"]), good(post_actions=["sh -c x"]),
                    good(packages=["Bad Name"]), good(unknown=1), good(warnings={"en": "only"}),
                    good(dropins=[{"path": "/etc/passwd", "content": ""}])):
            with self.assertRaises(ValidationError, msg=str(bad)):
                hw.parse_profile(bad)


class Cli(unittest.TestCase):
    def test_hw_detect_fixture_json_and_ru(self):
        out = io.StringIO()
        rc = cli.main(["--json", "hw", "detect", "--hardware", HARDWARE,
                       "--fixture", os.path.join(FIX, "nvidia-hybrid-laptop")], out=out)
        self.assertEqual(rc, 0)
        self.assertIn('"hybrid_graphics": true', out.getvalue())
        out = io.StringIO()
        cli.main(["hw", "detect", "--hardware", HARDWARE, "--lang", "ru",
                  "--fixture", os.path.join(FIX, "broadcom-wifi-laptop")], out=out)
        self.assertIn("Broadcom", out.getvalue())
        self.assertIn("WARNING", out.getvalue())


if __name__ == "__main__":
    unittest.main()
