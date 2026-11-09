import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import manifest as mf  # noqa: E402

SCRIPT = os.path.join(REPO, "core", "data", "heiss-gtk-audit")
# what makes GTK applications follow the KDE theme: GTK sync, GTK theme, both portal backends
GTK_PREREQUISITES = {"kde-gtk-config", "breeze-gtk", "xdg-desktop-portal-kde", "xdg-desktop-portal-gtk"}


class GtkPrerequisites(unittest.TestCase):
    def test_base_closure_contains_the_gtk_integration_packages(self):
        manifests = mf.load_dir(os.path.join(REPO, "profiles"))
        pkgs = {p for mid in mf.closure(manifests, ["base"]) for p in manifests[mid].packages}
        self.assertLessEqual(GTK_PREREQUISITES, pkgs)

    def test_custom_profile_also_gets_them(self):
        manifests = mf.load_dir(os.path.join(REPO, "profiles"))
        pkgs = {p for mid in mf.closure(manifests, ["custom"]) for p in manifests[mid].packages}
        self.assertLessEqual(GTK_PREREQUISITES, pkgs)

    def test_iso_installs_the_base_profile(self):
        with open(os.path.join(REPO, "profile", "packages.x86_64")) as f:
            names = {l.split("#")[0].strip() for l in f}
        self.assertIn("heiss-profile-base", names)


class AuditScript(unittest.TestCase):
    def test_is_read_only_and_offline(self):
        text = open(SCRIPT, encoding="utf-8").read()
        for forbidden in ("kwriteconfig", "gsettings set", "curl", "wget", "pacman -S", "sudo", "rm ", " mv ", "chmod", "systemctl"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_rejects_unsafe_labels(self):
        for bad in ("../x", "a b", "a/b", "$(id)"):
            r = subprocess.run(["sh", SCRIPT, bad], capture_output=True, text=True, env={"HOME": "/nonexistent", "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 2, bad)

    def test_writes_only_its_report_into_home(self):
        with tempfile.TemporaryDirectory() as home:
            r = subprocess.run(["sh", SCRIPT, "t1"], capture_output=True, text=True, timeout=60,
                               env={"HOME": home, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, r.stderr)
            # tools such as gsettings may create ~/.cache; the script itself writes only its report and never touches ~/.config
            self.assertEqual([f for f in os.listdir(home) if not f.startswith(".")], ["heiss-gtk-audit-t1.txt"])
            self.assertNotIn(".config", os.listdir(home))
            self.assertIn("Heiss GTK audit", open(os.path.join(home, "heiss-gtk-audit-t1.txt")).read())


if __name__ == "__main__":
    unittest.main()
