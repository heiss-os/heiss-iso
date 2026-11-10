import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from heiss_core import check as ck, cli  # noqa: E402
from test_themesync import FakeEnv as FakeTheme  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
PROFILES = os.path.join(REPO, "profiles")
GOOD_STUB = "[Desktop Entry]\nType=Application\nName=x\nNoDisplay=true\nHidden=true\n"


def app(name, **extra):
    keys = {"Type": "Application", "Name": name, "Exec": "x"}
    keys.update(extra)
    return "[Desktop Entry]\n" + "".join("%s=%s\n" % kv for kv in keys.items())


class FakeCheckEnv:
    """Fixture system: files dict, scripted commands (prefix match on the joined argv)."""

    def __init__(self, files=None, commands=None, denied=()):
        self.files = dict(files or {})
        self.scripted = commands or {}
        self.denied = set(denied)
        self.commands = []
        self.uid = 1000

    def run(self, argv):
        key = " ".join(argv)
        rc, out = (127, "")
        for prefix, res in self.scripted.items():
            if key.startswith(prefix):
                rc, out = res
        self.commands.append((list(argv), rc, out))
        return rc, out

    def read(self, path):
        if path in self.denied:
            raise PermissionError(path)
        return self.files.get(path)

    def euid(self):
        return self.uid

    def exists(self, path):
        return path in self.files or any(f.startswith(path.rstrip("/") + "/") for f in self.files)

    def listdir(self, path):
        pre = path.rstrip("/") + "/"
        return sorted({f[len(pre):].split("/")[0] for f in self.files if f.startswith(pre)})


def healthy(profile="base", packages=("plasma-desktop", "konsole"), **over):
    state = {"schema_version": 1, "applied": {"profile": profile, "addons": []}, "packages": ["konsole"],
             "services": [], "flatpaks": []}
    files = {ck.STATE_FILE: json.dumps(state), "/etc/passwd": "root:x:0:0::/root:/bin/bash\nme:x:1000:1000::/home/me:/bin/bash\n",
             "/etc/shadow": "root:!:19000::::::\nme:$6$x:19000::::::\n"}
    for f in ck.HIDE_STUBS:
        files["/usr/local/share/applications/" + f] = GOOD_STUB
    for f, key in ck.SHORTCUT_FILES.items():
        files["/usr/share/applications/" + f] = app(f, **{"X-KDE-Shortcuts": key})
    for f in ck.HELPER_FILES + ("/usr/lib/qt6/plugins/kf6/parts/konsolepart.so",):
        files[f] = ""
    files.update(over.pop("files", {}))
    commands = {"systemctl": (0, ""), "pacman -Qq": (0, "\n".join(packages) + "\n"),
                "busctl": (0, 's "0.1.0"\n')}
    commands.update(over.pop("commands", {}))
    return FakeCheckEnv(files, commands, **over)


def by_name(items):
    return {i.name: i for i in items}


class Checks(unittest.TestCase):
    def items(self, env, theme=None):
        return by_name(ck.run_checks(env, theme or FakeTheme(scheme="HeissDark"), PROFILES))

    def test_healthy_system_has_no_fail(self):
        items = ck.run_checks(healthy(), FakeTheme(scheme="HeissDark"), PROFILES)
        self.assertEqual([i for i in items if i.status == ck.FAIL], [], [i.line() for i in items])
        self.assertEqual(ck.exit_code(items), 0)
        self.assertEqual(len(items), 8)

    def test_failed_system_unit(self):
        env = healthy(commands={"systemctl --failed": (0, "foo.service loaded failed failed Foo\n")})
        r = self.items(env)["failed-units"]
        self.assertEqual(r.status, ck.FAIL)
        self.assertIn("system:foo.service", r.detail)

    def test_user_manager_unreachable_is_warn(self):
        env = healthy(commands={"systemctl --user": (1, "Failed to connect to bus")})
        self.assertEqual(self.items(env)["failed-units"].status, ck.WARN)

    def test_state_missing_is_warn(self):
        env = healthy()
        del env.files[ck.STATE_FILE]
        self.assertEqual(self.items(env)["profile-state"].status, ck.WARN)

    def test_state_corrupt_and_unknown_profile(self):
        env = healthy(files={ck.STATE_FILE: "{not json"})
        self.assertEqual(self.items(env)["profile-state"].status, ck.FAIL)
        env = healthy(profile="nonexistent")
        self.assertIn("no manifest", self.items(env)["profile-state"].detail)

    def test_state_vs_answers_and_missing_packages(self):
        env = healthy(files={ck.ETC_PROFILE: 'schema_version = 1\nprofile = "cyber"\n'})
        r = self.items(env)["profile-state"]
        self.assertEqual(r.status, ck.FAIL)
        self.assertIn("cyber", r.detail)
        env = healthy(packages=("plasma-desktop",))     # state records konsole, not installed
        self.assertIn("konsole", self.items(env)["profile-state"].detail)

    def test_theme_results_map_to_status(self):
        env = healthy()
        self.assertEqual(self.items(env, FakeTheme(scheme="Breeze"))["theme-sync"].status, ck.WARN)
        self.assertEqual(self.items(env, FakeTheme(scheme=None))["theme-sync"].status, ck.WARN)   # no session: cannot judge
        t = FakeTheme(scheme="HeissDark", gsettings="prefer-light")
        self.assertIn(self.items(env, t)["theme-sync"].status, (ck.WARN, ck.FAIL))

    def test_theme_lock_held_is_warn_not_a_color_scheme_message(self):
        r = self.items(healthy(), FakeTheme(scheme="HeissDark", locked=True))["theme-sync"]
        self.assertEqual(r.status, ck.WARN)
        self.assertIn("another theme sync", r.detail)
        self.assertNotIn("color scheme", r.detail)

    def test_as_root_user_scope_and_theme_are_not_judged(self):
        env = healthy()
        env.uid = 0
        items = self.items(env)
        self.assertEqual(items["theme-sync"].status, ck.WARN)
        self.assertEqual(items["failed-units"].status, ck.WARN)
        self.assertNotIn(["systemctl", "--user", "--failed", "--no-legend", "--plain", "--no-pager"], [c[0] for c in env.commands])

    def test_constants_match_the_repo(self):
        stubs = set(os.listdir(os.path.join(REPO, "profile/airootfs/usr/local/share/applications"))) - {"calamares.desktop"}
        self.assertEqual(stubs, set(ck.HIDE_STUBS))
        with open(os.path.join(REPO, "docs/design/SHORTCUTS.md"), encoding="utf-8") as f:
            doc = f.read()
        for fname, key in ck.SHORTCUT_FILES.items():
            self.assertRegex(doc, r"`%s`[^\n]*`%s`" % (key.replace("+", r"\+"), fname.replace(".", r"\.")))

    def test_launcher_missing_and_malformed_stub(self):
        env = healthy()
        del env.files["/usr/local/share/applications/vim.desktop"]
        r = self.items(env)["launcher-menu"]
        self.assertEqual(r.status, ck.FAIL)
        self.assertIn("vim.desktop is missing", r.detail)
        env = healthy(files={"/usr/local/share/applications/mpv.desktop": GOOD_STUB + "Exec=mpv\n"})
        self.assertIn("malformed", self.items(env)["launcher-menu"].detail)

    def test_launcher_duplicates_are_warn_and_hidden_do_not_count(self):
        env = healthy(files={"/usr/share/applications/a.desktop": app("Editor"), "/usr/share/applications/b.desktop": app("Editor")})
        r = self.items(env)["launcher-menu"]
        self.assertEqual(r.status, ck.WARN)
        self.assertIn("Editor", r.detail)
        env = healthy(files={"/usr/share/applications/a.desktop": app("Editor"),
                             "/usr/share/applications/b.desktop": app("Editor", NoDisplay="true")})
        self.assertEqual(self.items(env)["launcher-menu"].status, ck.OK)
        # a local stub overrides the package entry with the same id: only one entry per id is counted
        env = healthy(files={"/usr/share/applications/vim.desktop": app("Editor"), "/usr/share/applications/a.desktop": app("Editor")})
        self.assertEqual(self.items(env)["launcher-menu"].status, ck.OK)

    def test_removed_packages(self):
        self.assertEqual(len(ck.REMOVED_PACKAGES), 37)
        self.assertEqual(self.items(healthy())["removed-packages"].status, ck.OK)
        r = self.items(healthy(packages=("konsole", "nmap", "tcpdump")))["removed-packages"]
        self.assertEqual(r.status, ck.FAIL)
        self.assertIn("nmap", r.detail)
        # installed by Heiss for a Cyber profile: expected
        state = {"schema_version": 1, "applied": {"profile": "cyber", "addons": []}, "packages": ["nmap"], "services": [], "flatpaks": []}
        env = healthy(profile="cyber", packages=("nmap",), files={ck.STATE_FILE: json.dumps(state)})
        self.assertEqual(self.items(env)["removed-packages"].status, ck.OK)
        # a stray one on a Cyber system is only a warning
        env = healthy(profile="cyber", packages=("konsole", "nmap"))
        self.assertEqual(self.items(env)["removed-packages"].status, ck.WARN)

    def test_removed_list_matches_pr49_commit_message(self):
        # the packages must not be in the ISO list any more
        with open(os.path.join(REPO, "profile", "packages.x86_64"), encoding="utf-8") as f:
            iso = {l.strip() for l in f if l.strip() and not l.startswith("#")}
        self.assertEqual(iso & set(ck.REMOVED_PACKAGES), set())

    def test_shortcuts_and_terminal(self):
        env = healthy()
        self.assertEqual(self.items(env)["shortcuts-terminal"].status, ck.OK)
        del env.files["/usr/lib/qt6/plugins/kf6/parts/konsolepart.so"]
        self.assertEqual(self.items(env)["shortcuts-terminal"].status, ck.FAIL)
        env = healthy(files={"/usr/share/applications/org.kde.konsole.desktop": app("Konsole")})
        self.assertIn("Ctrl+Alt+T", self.items(env)["shortcuts-terminal"].detail)
        env = healthy(files={"/etc/xdg/kdeglobals": "[General]\nTerminalApplication=kitty\n"})
        self.assertEqual(self.items(env)["shortcuts-terminal"].status, ck.WARN)

    def test_helper(self):
        self.assertEqual(self.items(healthy())["helper"].status, ck.OK)
        env = healthy(commands={"busctl": (1, "Call failed: not activatable")})
        self.assertEqual(self.items(env)["helper"].status, ck.FAIL)
        env = healthy(commands={"busctl": (127, "")})
        self.assertEqual(self.items(env)["helper"].status, ck.WARN)
        env = healthy()
        del env.files[ck.HELPER_FILES[0]]
        r = self.items(env)["helper"]
        self.assertEqual(r.status, ck.FAIL)
        self.assertIn("org.heiss.helper.policy", r.detail)

    def test_live_leftovers(self):
        env = healthy(packages=("konsole", "cloud-init", "mkinitcpio-archiso"),
                      files={"/etc/passwd": "root:x:0:0::/root:/bin/bash\nliveuser:x:1000:1000::/home/liveuser:/bin/bash\n",
                             "/etc/shadow": "root:$6$abc:19000::::::\n"})
        r = self.items(env)["live-leftovers"]
        self.assertEqual(r.status, ck.FAIL)
        for word in ("liveuser", "cloud-init", "not locked"):
            self.assertIn(word, r.detail)

    def test_live_without_root_is_warn_and_live_session_is_warn(self):
        r = self.items(healthy(denied=["/etc/shadow"]))["live-leftovers"]
        self.assertEqual(r.status, ck.WARN)
        self.assertIn("root", r.detail)
        r = self.items(healthy(files={"/run/archiso/bootmnt": ""}))["live-leftovers"]
        self.assertEqual(r.status, ck.WARN)

    def test_missing_manifests_is_fail(self):
        with tempfile.TemporaryDirectory() as d:
            items = by_name(ck.run_checks(healthy(), FakeTheme(scheme="HeissDark"), d))
        self.assertEqual(items["profile-state"].status, ck.FAIL)


class Cli(unittest.TestCase):
    def test_exit_codes_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            report = os.path.join(d, "r.txt")
            out = io.StringIO()
            env = healthy()
            rc = cli.main(["--profiles", PROFILES, "check", "--report", report], out=out, check_env=env, theme_env=FakeTheme(scheme="HeissDark"))
            self.assertEqual(rc, 0, out.getvalue())
            self.assertEqual(len(out.getvalue().strip().splitlines()), 8)
            with open(report, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("$ systemctl --failed --no-legend --plain --no-pager", text)
            self.assertIn("busctl --system call org.heiss.Helper1", text)
            self.assertIn("heiss theme status", text)
            env = healthy(packages=("konsole", "nmap"))
            out = io.StringIO()
            rc = cli.main(["--profiles", PROFILES, "check"], out=out, check_env=env, theme_env=FakeTheme(scheme="HeissDark"))
            self.assertEqual(rc, 1)
            self.assertIn("FAIL  removed-packages", out.getvalue())

    def test_json(self):
        out = io.StringIO()
        cli.main(["--profiles", PROFILES, "--json", "check"], out=out, check_env=healthy(), theme_env=FakeTheme(scheme="HeissDark"))
        data = json.loads(out.getvalue())
        self.assertEqual({d["name"] for d in data}, {"failed-units", "profile-state", "theme-sync", "launcher-menu",
                                                     "removed-packages", "shortcuts-terminal", "helper", "live-leftovers"})

    def test_unwritable_report_is_an_error(self):
        rc = cli.main(["--profiles", PROFILES, "check", "--report", "/nonexistent-dir/x"], out=io.StringIO(),
                      check_env=healthy(), theme_env=FakeTheme(scheme="HeissDark"))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
