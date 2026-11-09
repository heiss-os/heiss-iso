import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from heiss_core import system  # noqa: E402


class MissingCommands(unittest.TestCase):
    def test_run_reports_127_for_a_missing_command(self):
        self.assertEqual(system._run(["definitely-not-a-command-xyz"]), (127, ""))

    def test_queries_do_not_raise_when_tools_are_missing(self):
        real = system._run
        system._run = lambda args: (127, "")
        try:
            s = system.PacmanSystem()
            self.assertEqual(s.installed_packages(), set())
            self.assertEqual(s.explicit_packages(), set())
            self.assertEqual(s.required_by("x"), set())
            self.assertEqual(s.enabled_services(), set())
            self.assertEqual(s.installed_flatpaks(), set())
            self.assertTrue(s.network_connected())      # unknown counts as connected
        finally:
            system._run = real

    def test_network_state_parsing(self):
        real = system._run
        try:
            system._run = lambda args: (0, "connected\n")
            self.assertTrue(system.PacmanSystem().network_connected())
            system._run = lambda args: (0, "connected (local only)\n")
            self.assertFalse(system.PacmanSystem().network_connected())
            system._run = lambda args: (0, "disconnected\n")
            self.assertFalse(system.PacmanSystem().network_connected())
        finally:
            system._run = real

    def test_required_by_parsing(self):
        real = system._run
        try:
            system._run = lambda args: (0, "Name : x\nRequired By : a  b>=1\nOptional For : None\n")
            self.assertEqual(system.PacmanSystem().required_by("x"), {"a", "b"})
            system._run = lambda args: (0, "Required By : None\n")
            self.assertEqual(system.PacmanSystem().required_by("x"), set())
        finally:
            system._run = real


if __name__ == "__main__":
    unittest.main()
