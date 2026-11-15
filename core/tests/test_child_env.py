"""The two apply paths (wizard and Control Center) start the same child with the same allowlisted environment."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for sub in ("core", "welcome", "control"):
    sys.path.insert(0, os.path.join(REPO, sub))
from heiss_control import runner as ctl  # noqa: E402
from heiss_welcome import applier as wiz  # noqa: E402


class SameEnvironment(unittest.TestCase):
    def test_the_allowlists_are_identical(self):
        for name in ("ALLOW_NAMES", "ALLOW_PREFIXES", "FIXED_PATH"):
            self.assertEqual(getattr(ctl, name), getattr(wiz, name), name)

    def test_the_same_input_gives_the_same_environment(self):
        sample = {"HOME": "/h", "LC_MESSAGES": "C", "PATH": "/evil", "PYTHONPATH": "/x", "LD_PRELOAD": "/y", "XAUTHORITY": "/a",
                  "FOO": "1", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/b"}
        self.assertEqual(ctl.clean_env(sample), wiz.clean_env(sample))
        self.assertEqual(wiz.clean_env(sample)["PATH"], "/usr/bin:/bin")

    def test_nothing_that_changes_code_loading_is_on_the_allowlist(self):
        for name in wiz.ALLOW_NAMES:
            self.assertFalse(name.startswith(("PYTHON", "LD_", "GI_", "GIO_", "G_", "GSETTINGS_", "HEISS_", "GCONV", "LOCPATH", "NLSPATH")), name)
        self.assertNotIn("PATH", wiz.ALLOW_NAMES)           # always the fixed value
        self.assertNotIn("DBUS_SYSTEM_BUS_ADDRESS", wiz.ALLOW_NAMES)


if __name__ == "__main__":
    unittest.main()
