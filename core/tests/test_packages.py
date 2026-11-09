import importlib.util
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
