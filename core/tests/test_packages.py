import importlib.util
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
from heiss_core import manifest as mf  # noqa: E402

spec = importlib.util.spec_from_file_location("gen_pkgs", os.path.join(REPO, "scripts", "gen-profile-packages.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def depends_of(pkgbuild):
    body = re.search(r"depends=\(\n(.*?)\n\)", pkgbuild, re.S).group(1)
    return re.findall(r"'([^']+)'", body)


class Metapackages(unittest.TestCase):
    def setUp(self):
        self.manifests = mf.load_dir(os.path.join(REPO, "profiles"))
        self.files = gen.outputs()

    def test_depends_are_manifest_packages_plus_required_metapackages(self):
        for mid in gen.PROFILES:
            m = self.manifests[mid]
            pk = self.files[os.path.join("heiss-profile-" + mid, "PKGBUILD")].decode()
            self.assertEqual(depends_of(pk), ["heiss-profile-" + r for r in m.requires] + list(m.packages), mid)

    def test_committed_files_match_generator(self):
        for rel, data in self.files.items():
            with open(os.path.join(gen.PKG_ROOT, rel), "rb") as f:
                self.assertEqual(f.read(), data, rel)

    def test_required_metapackages_exist(self):
        names = {"heiss-profile-" + p for p in gen.PROFILES}
        for mid in gen.PROFILES:
            for r in self.manifests[mid].requires:
                self.assertIn("heiss-profile-" + r, names)

    def test_every_generated_package_has_pkgrel(self):
        import json
        with open(os.path.join(gen.PKG_ROOT, "pkgrel.json")) as f:
            rel = json.load(f)
        for mid in gen.PROFILES:
            self.assertIsInstance(rel["heiss-profile-" + mid], int)

    def test_metapackages_are_empty_and_enable_nothing(self):
        for rel, data in self.files.items():
            text = data.decode()
            self.assertNotIn("systemctl", text)
            self.assertNotIn(".install", text)
            self.assertNotIn("install -D", text)
            self.assertNotIn("source=", text)


def pkgbuild(name):
    with open(os.path.join(REPO, "packages", name, "PKGBUILD"), encoding="utf-8") as f:
        return f.read()


class EnginePackages(unittest.TestCase):
    def test_versions_agree_with_code_and_pkgrel_file(self):
        import json
        with open(os.path.join(REPO, "packages", "pkgrel.json")) as f:
            rel = json.load(f)
        for name, init in (("heiss-core", "core/heiss_core/__init__.py"), ("heiss-helper", "helper/heiss_helper/__init__.py")):
            pk = pkgbuild(name)
            code_ver = re.search(r'__version__ = "([^"]+)"', open(os.path.join(REPO, init)).read()).group(1)
            self.assertEqual(re.search(r"^pkgver=(\S+)", pk, re.M).group(1), code_ver, name)
            self.assertEqual(int(re.search(r"^pkgrel=(\d+)", pk, re.M).group(1)), rel[name], name)
        self.assertEqual(rel["pkgver"], code_ver)

    def test_core_ships_every_manifest_and_hardware_profile(self):
        pk = pkgbuild("heiss-core")
        self.assertIn("profiles/*.toml", pk)
        self.assertIn("hardware/*.toml", pk)
        for f in os.listdir(os.path.join(REPO, "core", "data")):
            self.assertIn("core/data/" + f, pk, f)

    def test_helper_installs_every_data_file(self):
        pk = pkgbuild("heiss-helper")
        for f in os.listdir(os.path.join(REPO, "helper", "data")):
            self.assertIn("helper/data/" + f, pk, f)
        self.assertIn("polkit", pk)
        self.assertIn("python-gobject", pk)
        self.assertIn("'heiss-core'", pk)

    def test_helper_files_land_in_the_paths_the_service_expects(self):
        pk = pkgbuild("heiss-helper")
        for dest in ("/usr/share/dbus-1/system.d/org.heiss.Helper1.conf", "/usr/share/dbus-1/system-services/org.heiss.Helper1.service",
                     "/usr/lib/systemd/system/heiss-helper.service", "/usr/share/polkit-1/actions/org.heiss.helper.policy"):
            self.assertIn(dest, pk)

    def test_default_paths_match_where_core_ships_files(self):
        from heiss_core import cli
        self.assertEqual(cli.DEFAULT_PROFILES, "/usr/share/heiss/profiles")
        self.assertEqual(cli.DEFAULT_HARDWARE, "/usr/share/heiss/hardware")
        self.assertIn("/usr/share/heiss/profiles", pkgbuild("heiss-core"))

    def test_sources_are_local_archives_only(self):
        for name in ("heiss-core", "heiss-helper"):
            pk = pkgbuild(name)
            self.assertIn("source=('heiss-src.tar.gz')", pk)
            self.assertNotIn("http", re.search(r"source=.*", pk).group(0))


if __name__ == "__main__":
    unittest.main()


class ThemePackage(unittest.TestCase):
    def test_installs_every_generated_terminal_file(self):
        import fnmatch
        pk = pkgbuild("heiss-theme")
        patterns = {"konsole": ["*.colorscheme", "*.profile", "konsolerc"],
                    "kitty": ["kitty.conf", "*-theme.auto.conf", "heiss-dark.conf", "heiss-light.conf"]}
        gen_dir = os.path.join(REPO, "branding", "tokens", "generated")
        for sub, pats in patterns.items():
            for pat in pats:
                self.assertIn(sub + "/" + pat, pk, pat)          # the PKGBUILD installs this pattern
            for f in os.listdir(os.path.join(gen_dir, sub)):
                self.assertTrue(any(fnmatch.fnmatch(f, pat) for pat in pats), "generated %s/%s is not installed" % (sub, f))

    def test_konsole_default_profile_exists_in_the_package(self):
        rc = open(os.path.join(REPO, "branding", "tokens", "generated", "konsole", "konsolerc")).read()
        self.assertIn("DefaultProfile=Heiss-Dark.profile", rc)
        self.assertTrue(os.path.exists(os.path.join(REPO, "branding", "tokens", "generated", "konsole", "Heiss-Dark.profile")))

    def test_config_files_are_marked_as_backup_and_no_overwrites_of_other_packages(self):
        pk = pkgbuild("heiss-theme")
        self.assertIn("backup=('etc/xdg/konsolerc' 'etc/xdg/kitty/kitty.conf')", pk)
        self.assertNotIn("/usr/share/konsole/Konsole", pk)

    def test_iso_lists_the_theme_package(self):
        with open(os.path.join(REPO, "profile", "packages.x86_64")) as f:
            self.assertIn("heiss-theme", {l.split("#")[0].strip() for l in f})


class KeyringPackage(unittest.TestCase):
    PINNED = "DDD292CCC8613FD3324D3833FEA84CEF8AEDF132"

    def test_pinned_key_agrees_everywhere(self):
        pk = pkgbuild("heiss-keyring")
        self.assertEqual(re.search(r"^_fpr=(\S+)", pk, re.M).group(1), self.PINNED)
        wf = open(os.path.join(REPO, ".github", "workflows", "publish-repo.yml"), encoding="utf-8").read()
        self.assertEqual(re.search(r"EXPECTED_FPR: (\S+)", wf).group(1), self.PINNED)
        with open(os.path.join(REPO, "packages", "pkgrel.json")) as f:
            rel = json.load(f)
        self.assertEqual(int(re.search(r"^pkgrel=(\d+)", pk, re.M).group(1)), rel["heiss-keyring"])

    def test_key_file_is_the_pinned_key(self):
        import shutil, subprocess
        if not shutil.which("gpg"):
            self.skipTest("gpg not installed")
        out = subprocess.run(["gpg", "--batch", "--show-keys", "--with-colons",
                              os.path.join(REPO, "docs", "infra", "heiss-public.asc")],
                             capture_output=True, text=True, check=True).stdout
        fprs = [l.split(":")[9] for l in out.splitlines() if l.startswith("fpr:")]
        self.assertEqual(fprs[0], self.PINNED)

    def test_build_script_ships_the_key_file_to_the_package(self):
        with open(os.path.join(REPO, "scripts", "heiss-packages-build.sh"), encoding="utf-8") as f:
            self.assertIn("docs/infra/heiss-public.asc", f.read())

    def test_keyring_file_formats(self):
        pk = pkgbuild("heiss-keyring")
        self.assertIn("usr/share/pacman/keyrings", pk)
        self.assertIn('"$_fpr:4:"', pk)
        self.assertIn("heiss-trusted", pk)
        self.assertIn("heiss-revoked", pk)
        self.assertIn("makedepends=('gnupg')", pk)
        with open(os.path.join(REPO, "packages", "heiss-keyring", "heiss-keyring.install"), encoding="utf-8") as f:
            inst = f.read()
        self.assertIn("pacman-key --populate heiss", inst)
        self.assertNotIn(" /usr/", inst)   # install scripts run inside the root: no leading slash

    def test_cleanup_adds_the_repository_only_after_the_key_is_imported(self):
        with open(os.path.join(REPO, "profile", "airootfs", "usr", "local", "bin", "heiss-cleanup.sh"), encoding="utf-8") as f:
            sh = f.read()
        self.assertLess(sh.index("pacman-key --populate heiss"), sh.index("printf '\\n[heiss]"))
        self.assertIn("SigLevel = Required DatabaseRequired", sh)
        self.assertIn("https://heiss-os.github.io/heiss-repo/$arch", sh)
        with open(os.path.join(REPO, "profile", "packages.x86_64"), encoding="utf-8") as f:
            self.assertIn("heiss-keyring", f.read().split())
