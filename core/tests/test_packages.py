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

    def test_pkgbuild_ships_only_the_manifest_and_enables_nothing(self):
        for rel, data in self.files.items():
            if rel.endswith("PKGBUILD"):
                text = data.decode()
                self.assertNotIn("systemctl", text)
                self.assertNotIn(".install", text)
                self.assertEqual(text.count("install -Dm644"), 1)


if __name__ == "__main__":
    unittest.main()
