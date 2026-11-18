"""The Control Center starts `heiss profile apply` with an allowlisted environment and a fixed PATH."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for sub in ("core", "control"):
    sys.path.insert(0, os.path.join(REPO, sub))
from heiss_control import runner as ctl  # noqa: E402


class ChildEnvironment(unittest.TestCase):
    def test_only_allowlisted_variables_pass_and_path_is_fixed(self):
        sample = {"HOME": "/h", "LC_MESSAGES": "C", "PATH": "/evil", "PYTHONPATH": "/x", "LD_PRELOAD": "/y", "XAUTHORITY": "/a",
                  "FOO": "1", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/b"}
        env = ctl.clean_env(sample)
        self.assertEqual(env["PATH"], "/usr/bin:/bin")
        for bad in ("PYTHONPATH", "LD_PRELOAD", "FOO"):
            self.assertNotIn(bad, env)
        self.assertEqual(env["HOME"], "/h")

    def test_a_locale_value_that_is_a_path_is_not_passed(self):
        env = {"LANG": "/tmp/evil/locale", "LC_ALL": "../x", "LANGUAGE": "ru:en", "LC_MESSAGES": "ru_RU.UTF-8", "LC_CTYPE": "C\n"}
        self.assertEqual(ctl.clean_env(env), {"LANGUAGE": "ru:en", "LC_MESSAGES": "ru_RU.UTF-8", "PATH": "/usr/bin:/bin"})
        for v in ("ru_RU.UTF-8", "en_US.utf8", "C", "de_DE@euro", "POSIX"):
            self.assertEqual(ctl.clean_env({"LANG": v})["LANG"], v)

    def test_nothing_that_changes_code_loading_is_on_the_allowlist(self):
        for name in ctl.ALLOW_NAMES:
            self.assertFalse(name.startswith(("PYTHON", "LD_", "GI_", "GIO_", "G_", "GSETTINGS_", "HEISS_", "GCONV", "LOCPATH", "NLSPATH")), name)
        self.assertNotIn("PATH", ctl.ALLOW_NAMES)           # always the fixed value
        self.assertNotIn("DBUS_SYSTEM_BUS_ADDRESS", ctl.ALLOW_NAMES)


if __name__ == "__main__":
    unittest.main()
