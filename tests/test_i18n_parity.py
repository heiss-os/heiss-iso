"""Interface text parity: every ru string has an en string and the reverse, in the Python catalogs of the wizard
and the Control Center, in the manifests, and no QML file carries literal Cyrillic text (all text comes from the
catalogs). Fails on a missing key, an empty value or a different set of placeholders."""
import glob
import os
import re
import sys
import tomllib
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("core", "welcome", "control"):
    sys.path.insert(0, os.path.join(REPO, sub))

from heiss_welcome import strings as welcome_strings  # noqa: E402
from heiss_control import strings as control_strings  # noqa: E402

PLACEHOLDER = re.compile(r"%(?:\([a-z_]+\))?[sdif]|\{[a-z_0-9]*\}")
CYRILLIC = re.compile("[А-Яа-яЁё]")


def placeholders(text):
    return sorted(PLACEHOLDER.findall(text))


class Catalogs(unittest.TestCase):
    def check(self, name, S):
        self.assertEqual(sorted(S), ["en", "ru"], name)
        en, ru = S["en"], S["ru"]
        self.assertEqual(sorted(set(en) - set(ru)), [], "%s: keys with an en string and no ru string" % name)
        self.assertEqual(sorted(set(ru) - set(en)), [], "%s: keys with a ru string and no en string" % name)
        for key in sorted(en):
            for lang in ("en", "ru"):
                self.assertIsInstance(S[lang][key], str, "%s %s %s" % (name, lang, key))
                self.assertTrue(S[lang][key].strip(), "%s: empty %s string for %s" % (name, lang, key))
            self.assertEqual(placeholders(en[key]), placeholders(ru[key]), "%s: placeholders differ for %s" % (name, key))
            if key.startswith("lang_"):
                continue                      # a language is always written in its own language
            self.assertFalse(CYRILLIC.search(en[key]), "%s: Cyrillic text in the en string %s" % (name, key))

    def test_welcome_catalog(self):
        self.check("welcome", welcome_strings.S)

    def test_control_catalog(self):
        self.check("control", control_strings.S)

    def test_the_check_notices_a_missing_key(self):
        broken = {"en": {"a": "x", "b": "y"}, "ru": {"a": "и"}}
        with self.assertRaises(AssertionError):
            self.check("broken", broken)
        with self.assertRaises(AssertionError):
            self.check("broken", {"en": {"a": "%d of %d"}, "ru": {"a": "%d из"}})


class Manifests(unittest.TestCase):
    def test_every_localised_table_has_both_languages(self):
        files = glob.glob(os.path.join(REPO, "profiles", "**", "*.toml"), recursive=True)
        files += glob.glob(os.path.join(REPO, "hardware", "**", "*.toml"), recursive=True)
        self.assertTrue(files)
        bad = []

        def walk(node, path, name):
            if isinstance(node, dict):
                if set(node) & {"en", "ru"}:
                    if set(node) != {"en", "ru"} or not all(isinstance(v, str) and v.strip() for v in node.values()):
                        bad.append("%s: %s" % (name, path))
                else:
                    for k, v in node.items():
                        walk(v, path + "." + k, name)
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, "%s[%d]" % (path, i), name)

        for f in sorted(files):
            with open(f, "rb") as fh:
                walk(tomllib.load(fh), "", os.path.relpath(f, REPO))
        self.assertEqual(bad, [])


class Qml(unittest.TestCase):
    def test_no_literal_cyrillic_text_in_qml(self):
        files = glob.glob(os.path.join(REPO, "welcome", "**", "*.qml"), recursive=True)
        files += glob.glob(os.path.join(REPO, "control", "**", "*.qml"), recursive=True)
        self.assertTrue(files)
        for f in files:
            with open(f, encoding="utf-8") as fh:
                for no, line in enumerate(fh, 1):
                    self.assertFalse(CYRILLIC.search(line), "%s:%d: text must come from the catalogs" % (os.path.relpath(f, REPO), no))


if __name__ == "__main__":
    unittest.main()
