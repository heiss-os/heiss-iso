"""Development quality files (round 25 PR F): lint configs, the shell check, Dependabot, the packager name."""
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(REPO, *p), encoding="utf-8") as f:
        return f.read()


class Build(unittest.TestCase):
    def test_packager_is_set_by_the_package_build_script(self):
        self.assertRegex(read("scripts/heiss-packages-build.sh"), r'(?m)^export PACKAGER="Heiss OS"$')


class ShellCheck(unittest.TestCase):
    def test_skipped_files_exist_and_are_tier_a(self):
        script = read("scripts/check-shell.sh")
        skip = re.search(r"SKIP=\((.*?)\)", script, re.S).group(1).split()
        protected = read("docs/design/protected-paths.txt").split()
        self.assertTrue(skip)
        for f in skip:
            self.assertTrue(os.path.isfile(os.path.join(REPO, f)), f)
            self.assertIn(f, protected, "%s is skipped but is not Tier A: fix it instead" % f)

    def test_script_is_valid_bash(self):
        subprocess.run(["bash", "-n", os.path.join(REPO, "scripts/check-shell.sh")], check=True)


class Dependabot(unittest.TestCase):
    def test_github_actions_weekly_and_grouped(self):
        text = read(".github/dependabot.yml")
        self.assertRegex(text, r'package-ecosystem:\s*"?github-actions"?')
        self.assertRegex(text, r'interval:\s*"?weekly"?')
        self.assertIn("groups:", text)


class Quality(unittest.TestCase):
    def test_workflow_uploads_the_gui_renders_for_seven_days_and_keeps_pngs_out_of_the_repo(self):
        text = read(".github/workflows/quality.yml")
        self.assertRegex(text, r"retention-days:\s*7\b")
        self.assertIn("render-gui.py", text)
        tracked = subprocess.run(["git", "ls-files", "--", "*gui-shots*"], cwd=REPO, capture_output=True, text=True).stdout
        self.assertEqual(tracked.strip(), "")

    def test_shell_check_and_python_lint_are_blocking_and_namcap_is_informational(self):
        text = read(".github/workflows/quality.yml")
        jobs = re.split(r"(?m)^  (?=[a-z-]+:\s*$)", text)
        by = {j.split(":", 1)[0]: j for j in jobs[1:]}
        for name in ("shellcheck", "python-lint", "namcap", "gui-renders"):
            self.assertIn(name, by)
        self.assertNotIn("continue-on-error", by["shellcheck"])
        self.assertNotIn("continue-on-error", by["python-lint"])
        self.assertIn("continue-on-error: true", by["namcap"])


if __name__ == "__main__":
    unittest.main()
