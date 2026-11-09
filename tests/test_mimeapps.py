import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("check_mimeapps", os.path.join(ROOT, "scripts", "check-mimeapps.py"))
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

# the one default application per job, and the Base package that ships it
EXPECTED = {
    "org.kde.dolphin.desktop": "dolphin", "org.kde.kate.desktop": "kate", "firefox.desktop": "firefox",
    "org.kde.gwenview.desktop": "gwenview", "org.kde.okular.desktop": "okular", "org.kde.haruna.desktop": "haruna",
    "org.kde.ark.desktop": "ark", "org.keepassxc.KeePassXC.desktop": "keepassxc",
}


class Mimeapps(unittest.TestCase):
    def setUp(self):
        with open(cm.PATH, encoding="utf-8") as f:
            self.data, self.problems = cm.parse(f.read())

    def test_file_is_well_formed(self):
        self.assertEqual(self.problems, [])

    def test_mime_types_exist_when_asked_to(self):
        # The type names follow the CURRENT shared-mime-info (Arch). Older databases (for example on an
        # Ubuntu CI runner) know fewer names, so this runs only with HEISS_CHECK_MIME_TYPES=1;
        # scripts/check-mimeapps.py does the same check in the Arch CI job.
        if os.environ.get("HEISS_CHECK_MIME_TYPES") != "1":
            self.skipTest("set HEISS_CHECK_MIME_TYPES=1 on a machine with a current shared-mime-info")
        known = cm.known_mime_types()
        self.assertIsNotNone(known)
        self.assertEqual(cm.mime_problems(self.data, known), [])

    def test_only_expected_applications_and_all_in_base(self):
        used = {i for ids in self.data.values() for i in ids}
        self.assertEqual(used, set(EXPECTED))
        base = cm.base_packages()
        for app, pkg in EXPECTED.items():
            self.assertIn(pkg, base, app)

    def test_exactly_one_application_per_type(self):
        for mime, ids in self.data.items():
            self.assertEqual(len(ids), 1, mime)

    def test_important_defaults(self):
        d = self.data
        self.assertEqual(d["inode/directory"], ["org.kde.dolphin.desktop"])
        for k in ("x-scheme-handler/http", "x-scheme-handler/https", "text/html"):
            self.assertEqual(d[k], ["firefox.desktop"], k)
        self.assertEqual(d["application/pdf"], ["org.kde.okular.desktop"])
        self.assertEqual(d["text/plain"], ["org.kde.kate.desktop"])
        self.assertEqual(d["image/png"], ["org.kde.gwenview.desktop"])
        self.assertEqual(d["application/zip"], ["org.kde.ark.desktop"])

    def test_no_mail_handler_because_base_has_no_mail_client(self):
        self.assertNotIn("x-scheme-handler/mailto", self.data)

    def test_parser_rejects_bad_input(self):
        for bad in ("[Added Associations]\na/b=x.desktop;\n", "[Default Applications]\na/b=x.desktop\n",
                    "[Default Applications]\na/b=../x.desktop;\n", "[Default Applications]\na/b=x.desktop;\na/b=y.desktop;\n",
                    "[Default Applications]\nnonsense\n"):
            self.assertTrue(cm.parse(bad)[1], bad)


if __name__ == "__main__":
    unittest.main()
