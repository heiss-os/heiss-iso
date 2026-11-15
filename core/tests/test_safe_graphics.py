"""The safe-graphics GRUB entry (packages/heiss-safe-graphics/41_heiss_safe).

The script is run with `sh` against a stub of grub-mkconfig_lib and a scratch /boot (a copy of the script with the path replaced).
Not covered here: a real grub-mkconfig run, booting the entry, UEFI, NVIDIA hardware.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PKG = os.path.join(REPO, "packages", "heiss-safe-graphics")
SCRIPT = os.path.join(PKG, "41_heiss_safe")

STUB_LIB = r"""
make_system_path_relative_to_its_root () { if [ "$1" = / ]; then echo "${STUB_ROOT_REL:-/}"; else echo "$1"; fi; }
grub_get_device_id () { echo "devid"; }
prepare_grub_to_access_device () { echo "set root='hd0,1'"; }
grub_add_tab () { sed 's/^/\t/'; }
grub_quote () { sed "s/'/'\\\\''/g"; }
gettext_printf () { fmt="$1"; shift; printf "$fmt" "$@"; }
"""


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def run_script(files=("vmlinuz-linux", "initramfs-linux.img"), lib=None, **env):
    with tempfile.TemporaryDirectory() as d:
        boot = os.path.join(d, "boot")
        os.makedirs(boot)
        for f in files:
            open(os.path.join(boot, f), "w").close()
        with open(os.path.join(d, "grub-mkconfig_lib"), "w") as f:
            f.write(lib or STUB_LIB)
        # the script has no override for /boot (it runs as root); the tests run a copy with the path replaced
        script = os.path.join(d, "41_heiss_safe")
        src = read(SCRIPT)
        assert 'boot_dir="/boot"' in src
        with open(script, "w", encoding="utf-8") as f:
            f.write(src.replace('boot_dir="/boot"', 'boot_dir="%s"' % boot))
        e = {"PATH": "/usr/bin:/bin", "pkgdatadir": d,
             "GRUB_DEVICE": "/dev/vda2", "GRUB_DEVICE_UUID": "1111-2222", "GRUB_FS": "ext4",
             "GRUB_CMDLINE_LINUX": ""}
        e.update(env)
        r = subprocess.run(["sh", script], env=e, capture_output=True, text=True)
        return r, boot


def unescape(line):
    """What GRUB makes of a line of words: a backslash takes the next character literally."""
    return re.sub(r"\\(.)", r"\1", line)


def linux_lines(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("linux")]


class Script(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run(["sh", "-n", SCRIPT]).returncode, 0)

    def test_entry_has_safe_parameters_and_root(self):
        r, boot = run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("menuentry 'Heiss OS, safe graphics (linux)'", r.stdout)
        (line,) = linux_lines(r.stdout)
        self.assertIn("root=UUID=1111-2222", line)
        for p in ("nomodeset", "modprobe.blacklist=nvidia,nvidia_modeset,nvidia_uvm,nvidia_drm"):
            self.assertIn(p, line.split())
        self.assertIn(boot + "/vmlinuz-linux", line)
        self.assertIn("initrd\t" + boot + "/initramfs-linux.img", r.stdout)
        self.assertEqual(r.stdout.count("{"), r.stdout.count("}"))

    def test_nvidia_and_mode_parameters_are_dropped_and_the_rest_kept(self):
        r, _ = run_script(GRUB_CMDLINE_LINUX="foo=bar nvidia-drm.modeset=1 nvidia.NVreg_X=1 modprobe.blacklist=nouveau nomodeset baz")
        words = linux_lines(r.stdout)[0].split()
        self.assertIn("foo=bar", words)
        self.assertIn("baz", words)
        self.assertNotIn("nvidia-drm.modeset=1", words)
        self.assertNotIn("nvidia.NVreg_X=1", words)
        self.assertNotIn("modprobe.blacklist=nouveau", words)
        self.assertEqual(words.count("nomodeset"), 1)

    def test_btrfs_root_subvolume_keeps_rootflags(self):
        r, _ = run_script(GRUB_FS="btrfs", STUB_ROOT_REL="/@", GRUB_CMDLINE_LINUX="foo=bar")
        words = linux_lines(r.stdout)[0].split()
        self.assertIn("rootflags=subvol=@", words)
        self.assertIn("foo=bar", words)
        r, _ = run_script(GRUB_FS="btrfs", STUB_ROOT_REL="/")
        self.assertNotIn("rootflags", r.stdout)

    def test_no_uuid_falls_back_to_the_device(self):
        r, _ = run_script(GRUB_DEVICE_UUID="")
        self.assertIn("root=/dev/vda2", linux_lines(r.stdout)[0])
        r, _ = run_script(GRUB_DISABLE_LINUX_UUID="true")
        self.assertIn("root=/dev/vda2", linux_lines(r.stdout)[0])

    def test_nothing_is_printed_without_a_kernel_or_without_its_initramfs(self):
        for files in ((), ("vmlinuz-linux",), ("initramfs-linux.img",)):
            r, _ = run_script(files=files)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "", files)

    def test_lts_kernel_gets_its_own_entry(self):
        r, _ = run_script(files=("vmlinuz-linux", "initramfs-linux.img", "vmlinuz-linux-lts", "initramfs-linux-lts.img"))
        self.assertEqual(len(linux_lines(r.stdout)), 2)
        self.assertIn("(linux-lts)", r.stdout)
        ids = re.findall(r"'(heiss-safe-graphics-[^']+)'", r.stdout)
        self.assertEqual(len(set(ids)), 2)

    def test_glob_characters_in_the_command_line_are_not_expanded_by_sh_or_grub(self):
        r, _ = run_script(GRUB_CMDLINE_LINUX="foo=* ?")
        line = linux_lines(r.stdout)[0]
        self.assertIn("foo=\\*", line.split())     # escaped for GRUB, not expanded by sh
        self.assertIn("\\?", line.split())
        self.assertIn("foo=* ?", unescape(line))

    def test_characters_that_change_grub_syntax_are_escaped(self):
        hostile = "a'b a\"b $x ${y} ;rm &x |x <x >x (x) {x} #x `x` ~x !x \\x"
        r, _ = run_script(GRUB_CMDLINE_LINUX=hostile)
        self.assertEqual(r.returncode, 0, r.stderr)
        (line,) = linux_lines(r.stdout)
        # nothing special is left unescaped on the linux line
        stripped = re.sub(r"\\.", "", line)
        for ch in "'\"$;&|<>(){}#`~!*?[]":
            self.assertNotIn(ch, stripped, ch)
        for part in hostile.split():
            self.assertIn(part, unescape(line).split(), part)
        self.assertEqual(r.stdout.count("{"), r.stdout.count("}"))   # the menu entry braces are still balanced

    def test_a_newline_or_non_ascii_parameter_is_left_out_with_a_message(self):
        for bad in ("bad\nword", "caf\u00e9", "tab\x01x"):
            r, _ = run_script(GRUB_CMDLINE_LINUX="keep " + bad)
            self.assertEqual(r.returncode, 0, r.stderr)
            (line,) = linux_lines(r.stdout)
            self.assertIn("keep", line.split())
            self.assertNotIn("\u00e9", line)
            self.assertNotIn("\x01", line)

    def test_btrfs_subvolume_name_is_escaped_and_never_split_into_two_parameters(self):
        r, _ = run_script(GRUB_FS="btrfs", STUB_ROOT_REL="/@my'root$x;")
        (line,) = linux_lines(r.stdout)
        self.assertIn("rootflags=subvol=@my'root$x;", unescape(line).split())
        self.assertEqual(re.sub(r"\\.", "", line).count("'"), 0)
        for bad in ("/@a b", "/@a init=/bin/sh b", "/@a\nb"):
            r, _ = run_script(GRUB_FS="btrfs", STUB_ROOT_REL=bad)
            self.assertEqual((r.returncode, r.stdout), (0, ""), bad)
            self.assertIn("no entry written", r.stderr)

    def test_unusual_device_is_escaped_and_the_rest_of_the_entry_is_intact(self):
        r, _ = run_script(GRUB_DEVICE_UUID="", GRUB_DEVICE="/dev/x';z")
        (line,) = linux_lines(r.stdout)
        self.assertIn("root=/dev/x';z", unescape(line).split())
        self.assertEqual(re.sub(r"\\.", "", line).count("'"), 0)

    def test_unusable_device_writes_no_entry(self):
        for bad in ("/dev/x\ny", "/dev/x init=/bin/sh", "/dev/caf\u00e9"):
            r, _ = run_script(GRUB_DEVICE_UUID="", GRUB_DEVICE=bad)
            self.assertEqual((r.returncode, r.stdout), (0, ""), bad)
            self.assertIn("unusable root device", r.stderr)

    def test_empty_root_device_writes_no_entry(self):
        r, _ = run_script(GRUB_DEVICE_UUID="", GRUB_DEVICE="")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("unusable root device", r.stderr)

    def test_without_grep_a_value_is_refused_not_passed_on(self):
        with tempfile.TemporaryDirectory() as bindir:
            for tool in ("sh", "sed", "cat", "printf", "mkdir"):
                src = subprocess.run(["sh", "-c", "command -v " + tool], capture_output=True, text=True).stdout.strip()
                if src:
                    os.symlink(src, os.path.join(bindir, tool))
            r, _ = run_script(GRUB_CMDLINE_LINUX="keep caf\u00e9", PATH=bindir)
        self.assertNotIn("\u00e9", r.stdout)
        # nothing can be checked, so nothing is written (fails closed)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("no entry written", r.stderr)

    def test_boot_directory_with_a_space_writes_no_entry(self):
        r, _ = run_script(STUB_ROOT_REL="/")
        self.assertTrue(r.stdout)    # sanity: the normal case writes an entry
        lib = STUB_LIB.replace('echo "$1"; fi; }', 'echo "$1 x"; fi; }')
        r, _ = run_script(lib=lib)
        self.assertEqual(r.stdout, "")

    def test_the_menu_entry_id_is_quoted(self):
        lib = STUB_LIB.replace('echo "devid"', "echo \"de'vid\"")
        r, _ = run_script(lib=lib)
        ids = re.findall(r"heiss-safe-graphics-linux-([^ ]+)'", r.stdout)
        self.assertTrue(ids and "'\\''" in ids[0], r.stdout)

    def test_no_environment_override_of_the_kernel_directory(self):
        self.assertNotIn("HEISS_SAFE_BOOT", read(SCRIPT))

    def test_script_does_not_touch_the_network_or_write_files(self):
        text = read(SCRIPT)
        for bad in ("curl", "wget", "> /", ">/", "tee ", "rm ", "mv "):
            self.assertNotIn(bad, text, bad)


class Package(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PKG, "PKGBUILD"), encoding="utf-8") as f:
            self.pk = f.read()

    def test_installs_an_executable_script_into_grub_d(self):
        self.assertIn('install -Dm755 "$srcdir/41_heiss_safe" "$pkgdir/etc/grub.d/41_heiss_safe"', self.pk)
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_checksum_matches_the_script(self):
        want = hashlib.sha256(read(SCRIPT, "rb")).hexdigest()
        self.assertIn("sha256sums=('%s')" % want, self.pk)

    def test_depends_on_grub_and_nothing_protected_is_wired(self):
        self.assertIn("depends=('grub')", self.pk)
        self.assertNotIn(".install", self.pk)
        self.assertNotIn("install=", self.pk)

    def test_pkgrel_file_and_iso_list(self):
        rel = json.loads(read(os.path.join(REPO, "packages", "pkgrel.json")))
        self.assertEqual(int(re.search(r"^pkgrel=(\d+)", self.pk, re.M).group(1)), rel["heiss-safe-graphics"])
        self.assertEqual(re.search(r"^pkgver=(\S+)", self.pk, re.M).group(1), rel["pkgver"])
        with open(os.path.join(REPO, "profile", "packages.x86_64"), encoding="utf-8") as f:
            names = {l.split("#")[0].strip() for l in f}
        self.assertIn("heiss-safe-graphics", names)
        self.assertIn("grub", names)


class NvidiaWarning(unittest.TestCase):
    def setUp(self):
        import tomllib
        with open(os.path.join(REPO, "hardware", "gpu-nvidia-open.toml"), "rb") as f:
            self.w = tomllib.load(f)["warnings"]

    def test_names_the_entry_that_exists_and_not_dkms(self):
        entry = re.search(r"title=\"([^\"$]+)", read(SCRIPT)).group(1)
        self.assertEqual(entry, "Heiss OS, safe graphics (")   # title prefix, then the kernel name
        for lang in ("en", "ru"):
            self.assertIn("Heiss OS, safe graphics", self.w[lang])
            self.assertIn("nvidia-open-lts", self.w[lang])
            self.assertNotIn("DKMS", self.w[lang])


if __name__ == "__main__":
    unittest.main()
