"""scripts/render-gui.py: renders both GUIs offscreen without warnings, writes only inside its output directory.

Skipped when PySide6 is not installed (CI does not install it); run it by hand on a machine that has it.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "render-gui.py")
HAVE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAVE, "PySide6 is required")
class RenderGui(unittest.TestCase):
    def run_script(self, *args, out=None):
        return subprocess.run([sys.executable, "-I", SCRIPT, *args] + (["--out", out] if out else []),
                              capture_output=True, text=True, timeout=300)

    def test_renders_every_page_without_qml_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out")
            r = self.run_script("--lang", "ru", "--theme", "light", out=out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Qt/QML warnings and errors: 0", r.stdout)
            pngs = [f for f in os.listdir(out) if f.endswith(".png")]
            self.assertTrue(any(f.startswith("welcome-ru-light-") for f in pngs))
            self.assertTrue(any(f.startswith("control-ru-light-") for f in pngs))
            self.assertEqual(sorted(os.listdir(d)), ["out"])   # nothing outside the output directory
            for line in r.stdout.splitlines():
                if line.endswith(".png"):
                    self.assertTrue(line.startswith(out + os.sep), line)
                    self.assertGreater(os.path.getsize(line), 1000)

    def test_refuses_a_non_empty_output_directory(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "keep"), "w").close()
            r = self.run_script("--only", "control", out=d)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(os.path.exists(os.path.join(d, "keep")))


if __name__ == "__main__":
    unittest.main()
