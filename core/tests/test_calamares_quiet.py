"""The installer makes no network request of its own: no "internet" requirement check, no GeoIP,
no sample conditions from the stock welcome.conf (stdlib text checks; PyYAML is not in CI)."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULES = os.path.join(REPO, "profile/airootfs/etc/calamares/modules")
SETTINGS = os.path.join(REPO, "profile/airootfs/etc/calamares/settings.conf")
WELCOME = ("welcome.conf", "welcomeq.conf")
LOCALE = ("locale.conf", "localeq.conf")
HOSTS = ("geoip.kde.org", "example.com", "google.com", "kde.org", "freebsd.org")


def active_lines(name):
    with open(os.path.join(MODULES, name), encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if l.strip() and not l.lstrip().startswith("#")]


def block(lines, key):
    """Lines indented under `key:` (a top-level or nested mapping key)."""
    out, indent = [], None
    for l in lines:
        if indent is None:
            if l.strip() == key + ":":
                indent = len(l) - len(l.lstrip())
            continue
        cur = len(l) - len(l.lstrip())
        if cur <= indent:
            break
        out.append(l)
    return out


class ActiveModules(unittest.TestCase):
    def test_sequence_uses_the_files_checked_here(self):
        with open(SETTINGS, encoding="utf-8") as f:
            seq = [l.strip() for l in f if l.strip().startswith("- ")]
        self.assertIn("- welcome", seq)
        self.assertIn("- locale", seq)


class NoNetwork(unittest.TestCase):
    def test_no_active_line_names_a_remote_host(self):
        for name in WELCOME + LOCALE:
            for l in active_lines(name):
                for h in HOSTS:
                    self.assertNotIn(h, l, "%s: %s" % (name, l))

    def test_welcome_checks_have_no_internet_and_no_sample_conditions(self):
        for name in WELCOME:
            lines = active_lines(name)
            checks = [c.strip().lstrip("- ").strip('"') for c in block(block(lines, "requirements"), "check")]
            self.assertEqual(checks, ["storage", "ram", "power", "root", "screen"], name)
            required = [c.strip().lstrip("- ") for c in block(block(lines, "requirements"), "required")]
            self.assertEqual(required, ["ram"], name)
            self.assertFalse([l for l in lines if "internetCheckUrl" in l], name)

    def test_geoip_is_off_everywhere(self):
        for name in WELCOME + LOCALE:
            geo = [g.strip() for g in block(active_lines(name), "geoip")]
            self.assertTrue(geo, name)
            style = [g for g in geo if g.startswith("style:")]
            self.assertEqual(len(style), 1, name)
            self.assertRegex(style[0], r'^style:\s*"none"$', name)

    def test_locale_default_stays_the_fixed_zone(self):
        lines = active_lines("locale.conf")
        self.assertIn('region:                     "Europe"', lines)
        self.assertIn('zone:                       "Moscow"', lines)


if __name__ == "__main__":
    unittest.main()
