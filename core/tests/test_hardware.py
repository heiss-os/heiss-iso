import io
import os
import sys
import tempfile
import unittest
from unittest import mock

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


class Requires(unittest.TestCase):
    def test_requires_is_validated(self):
        self.assertEqual(hw.parse_profile(good(requires=["safe-graphics-entry"])).requires, ("safe-graphics-entry",))
        self.assertEqual(hw.parse_profile(good()).requires, ())
        for bad in (["nosuch"], "safe-graphics-entry", ["safe-graphics-entry", "safe-graphics-entry"], [1], [[1]], [{}],
                    [None], {"safe-graphics-entry": 1}, 5):
            with self.assertRaises(ValidationError, msg=str(bad)):
                hw.parse_profile(good(requires=bad))

    def test_every_profile_that_installs_the_nvidia_driver_requires_the_safe_entry(self):
        for p in hw.load_profiles(HARDWARE).values():
            if any(x.startswith("nvidia") for x in p.packages):
                self.assertIn("safe-graphics-entry", p.requires, p.id)

    def test_capabilities_reads_the_grub_script(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "41_heiss_safe")
            self.assertEqual(hw.capabilities(path), set())
            open(path, "w").close()
            os.chmod(path, 0o644)
            self.assertEqual(hw.capabilities(path), set())          # not executable: grub-mkconfig would skip it
            os.chmod(path, 0o755)
            self.assertEqual(hw.capabilities(path), {"safe-graphics-entry"})
            link = os.path.join(d, "link")
            os.symlink(path, link)
            self.assertEqual(hw.capabilities(link), set())          # a link is not the packaged file

    def test_detect_marks_the_proposal_unavailable_only_when_capabilities_were_given(self):
        facts = hw.load_fixture(os.path.join(FIX, "nvidia-desktop-modern"))
        profiles = hw.load_profiles(HARDWARE)
        self.assertEqual(hw.detect(facts, profiles).unavailable, {})                     # not checked
        r = hw.detect(facts, profiles, set())
        self.assertEqual(r.unavailable, {"gpu-nvidia-open": ["safe-graphics-entry"]})
        self.assertIn("gpu-nvidia-open", {p.id for p in r.proposals})                    # still reported, never silently hidden
        self.assertEqual(hw.detect(facts, profiles, {"safe-graphics-entry"}).unavailable, {})
        self.assertIn("NOT OFFERED: needs safe-graphics-entry", hw.render_text(r))
        self.assertEqual(r.to_dict()["unavailable"], {"gpu-nvidia-open": ["safe-graphics-entry"]})

    def test_apply_refuses_a_profile_whose_requirement_is_missing(self):
        env = {"HEISS_HARDWARE": HARDWARE, "HEISS_STATE": "/nonexistent/state.json"}
        argv = ["--profiles", os.path.join(REPO, "profiles"), "profile", "apply", "--dry-run", "--profile", "base",
                "--hardware", "gpu-nvidia-open"]
        with mock.patch.dict(os.environ, env), mock.patch("heiss_core.hardware.capabilities", return_value=set()):
            out = io.StringIO()
            with mock.patch("sys.stderr", io.StringIO()) as err:
                rc = cli.main(argv, system=__import__("fakes").FakeSystem(), out=out)
            self.assertEqual(rc, 1)
            self.assertIn("safe-graphics-entry", err.getvalue() + out.getvalue())
            self.assertIn("not applied", err.getvalue() + out.getvalue())
        with mock.patch.dict(os.environ, env), mock.patch("heiss_core.hardware.capabilities",
                                                           return_value={"safe-graphics-entry"}):
            out = io.StringIO()
            rc = cli.main(argv, system=__import__("fakes").FakeSystem(), out=out)
            self.assertEqual(rc, 0, out.getvalue())
            self.assertIn("nvidia-open", out.getvalue())


class LtsFallback(unittest.TestCase):
    """SAFE-FALLBACK answer 2 A: linux-lts and its driver come only together with the NVIDIA driver."""

    def setUp(self):
        self.cat = hw.load_profiles(HARDWARE)

    def test_the_nvidia_profile_installs_the_lts_kernel_with_its_driver(self):
        pk = set(self.cat["gpu-nvidia-open"].packages)
        self.assertTrue({"nvidia-open", "nvidia-utils", "linux-lts", "nvidia-open-lts"} <= pk)

    def test_no_other_profile_pulls_in_the_lts_kernel(self):
        for i, p in self.cat.items():
            if i != "gpu-nvidia-open":
                self.assertFalse({"linux-lts", "nvidia-open-lts"} & set(p.packages), i)

    def test_the_warning_no_longer_says_the_lts_kernel_is_unsupported(self):
        for lang, w in self.cat["gpu-nvidia-open"].warnings.items():
            self.assertNotIn("Built for the standard kernel", w, lang)
            self.assertNotIn("Драйвер собран только для обычного ядра", w, lang)
            self.assertNotIn("needs the package nvidia-open-lts", w, lang)
            self.assertIn("linux-lts", w, lang)
            self.assertIn("nvidia-open-lts", w, lang)


class Confirmation(unittest.TestCase):
    """A profile that is not safe by default is applied only with --confirm-hardware (SAFE-FALLBACK answer 3 A)."""

    def setUp(self):
        self.cat = hw.load_profiles(HARDWARE)

    def args(self, hardware, confirm=(), sub="apply", dry_run=False):
        import argparse
        return argparse.Namespace(hardware=list(hardware), confirm_hardware=list(confirm), sub=sub, dry_run=dry_run)

    def chosen(self, *a, **kw):
        with mock.patch("heiss_core.hardware.capabilities", return_value={"safe-graphics-entry"}):
            return cli._chosen_hardware(self.args(*a, **kw), self.cat)

    def test_exactly_the_profiles_that_are_not_safe_by_default_need_it(self):
        need = {i for i, p in self.cat.items() if hw.needs_confirmation(p)}
        self.assertEqual(need, {"gpu-nvidia-open", "hybrid-nvidia-amd", "hybrid-nvidia-intel"})

    def test_apply_without_the_flag_is_refused_and_the_message_is_plain(self):
        with self.assertRaises(cli.HeissError) as cm:
            self.chosen(["gpu-nvidia-open"])
        msg = str(cm.exception)
        self.assertNotIn("snapshot", msg.lower())
        self.assertIn("Heiss OS, safe graphics", msg)
        self.assertIn("--confirm-hardware gpu-nvidia-open", msg)

    def test_apply_with_the_flag_passes_and_a_safe_profile_needs_nothing(self):
        self.assertEqual([p.id for p in self.chosen(["gpu-nvidia-open"], ["gpu-nvidia-open"])], ["gpu-nvidia-open"])
        self.assertEqual([p.id for p in self.chosen(["vm-virtualbox"])], ["vm-virtualbox"])
        self.assertEqual([p.id for p in self.chosen(["vm-virtualbox"], ["vm-virtualbox"])], ["vm-virtualbox"])

    def test_one_confirmation_does_not_cover_another_profile(self):
        with self.assertRaises(cli.HeissError):
            self.chosen(["gpu-nvidia-open", "hybrid-nvidia-intel"], ["gpu-nvidia-open"])

    def test_diff_and_dry_run_only_show_the_plan_and_need_no_confirmation(self):
        self.assertTrue(self.chosen(["gpu-nvidia-open"], sub="diff"))
        self.assertTrue(self.chosen(["gpu-nvidia-open"], dry_run=True))

    def test_a_confirmation_for_a_profile_that_was_not_selected_is_an_error(self):
        with self.assertRaises(cli.HeissError) as cm:
            self.chosen(["vm-virtualbox"], ["gpu-nvidia-open"])
        self.assertIn("not selected", str(cm.exception))

    def test_the_cli_flag_exists_on_apply_and_diff(self):
        env = {"HEISS_HARDWARE": HARDWARE, "HEISS_STATE": "/nonexistent/state.json"}
        for sub in ("diff", "apply --dry-run"):
            argv = (["--profiles", os.path.join(REPO, "profiles"), "profile"] + sub.split()
                    + ["--profile", "base", "--hardware", "gpu-nvidia-open", "--confirm-hardware", "gpu-nvidia-open"])
            with mock.patch.dict(os.environ, env), mock.patch("heiss_core.hardware.capabilities",
                                                               return_value={"safe-graphics-entry"}):
                out = io.StringIO()
                rc = cli.main(argv, system=__import__("fakes").FakeSystem(), out=out)
                self.assertEqual(rc, 0, out.getvalue())


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
