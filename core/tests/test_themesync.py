import contextlib
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import cli, themesync as ts  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
LNF = {t: open(os.path.join(REPO, "profile/airootfs/usr/share/plasma/look-and-feel", pkg, "contents/defaults"), encoding="utf-8").read()
       for t, pkg in ts.LNF_PACKAGE.items()}


class FakeEnv:
    """Scripted desktop. `kde` maps (file, group, key) -> value."""

    def __init__(self, scheme="HeissDark", commands=("konsole", "kitty"), files=None, kde=None, gsettings="prefer-dark",
                 portal=1, kded_modules="as 2 gtkconfig foo", konsole_services=(), locked=False, plasma_ok=True):
        self.kde = {("kdeglobals", "General", "ColorScheme"): scheme}
        self.kde.update(kde or {})
        self.commands, self.files = set(commands), set(files if files is not None else [
            "/usr/share/konsole/Heiss-Dark.profile", "/usr/share/konsole/Heiss-Light.profile",
            "/etc/xdg/kitty/dark-theme.auto.conf", "/etc/xdg/kitty/light-theme.auto.conf"])
        self.gs, self.portal, self.kded = gsettings, portal, kded_modules
        self.konsole_services, self.locked, self.plasma_ok = list(konsole_services), locked, plasma_ok
        self.writes, self.evals, self.calls, self.logged = [], [], [], []
        self.running = True

    def kde_read(self, file, group, key): return self.kde.get((file, group, key))

    def kde_write(self, file, group, key, value):
        self.writes.append((file, group, key, value))
        self.kde[(file, group, key)] = value
        return True

    def plasma_eval(self, script):
        self.evals.append(script)
        return self.plasma_ok

    def busctl(self, args):
        self.calls.append(list(args))
        if args[0] == "list":
            return 0, "".join("%s 123 konsole\n" % s for s in self.konsole_services)
        if args[0] == "tree":
            return 0, "/Sessions\n/Sessions/1\n/Sessions/2\n/Windows/1\n"
        if args[:2] == ["call", "org.kde.kded6"]:
            return (0, self.kded) if self.kded is not None else (1, "")
        if "Settings" in " ".join(args):
            return (0, "v v u %s\n" % self.portal) if self.portal is not None else (1, "")
        return 0, ""

    def gsettings(self, schema, key): return self.gs
    def process_running(self, name): return self.running
    def command_exists(self, name): return name in self.commands
    def exists(self, path): return path in self.files

    def read_text(self, path):
        for t, pkg in ts.LNF_PACKAGE.items():
            if path.endswith("%s/contents/defaults" % pkg):
                return LNF[t]
        return None

    def append_log(self, line): self.logged.append(line)

    @contextlib.contextmanager
    def lock(self):
        yield not self.locked


def lnf_kde(theme):
    d = ts._parse_lnf_defaults(LNF[theme])
    return {k: v for k, v in d.items() if k in ts.CHECKED_KEYS}


def run(env, **kw):
    lines = []
    results, rc = ts.sync(env, wait=False, say=lines.append, **kw)
    return {r.target: r for r in results}, rc, lines


class Sync(unittest.TestCase):
    def test_one_line_per_target_in_a_fixed_order(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        results, rc, lines = run(env)
        self.assertEqual(list(results), list(ts.TARGETS_ORDER))
        self.assertEqual(len(lines), len(ts.TARGETS_ORDER))
        self.assertTrue(all(l.startswith("theme-sync: ") for l in lines))

    def test_dark_everything_consistent(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        results, rc, _ = run(env)
        self.assertEqual(rc, 0)
        self.assertEqual({t: r.status for t, r in results.items()},
                         {"launcher-icon": "ok", "konsole": "changed", "plasma-consistency": "ok", "gtk": "ok", "portal": "ok", "kitty": "ok"})
        self.assertIn("heiss-launcher-sand'", env.evals[0])
        self.assertEqual(env.writes, [("konsolerc", "Desktop Entry", "DefaultProfile", "Heiss-Dark.profile")])

    def test_light_uses_light_values(self):
        env = FakeEnv(scheme="HeissLight", kde=lnf_kde("light"), gsettings="default", portal=2)
        results, rc, _ = run(env)
        self.assertEqual(rc, 0)
        self.assertIn("heiss-launcher-sand-light", env.evals[0])
        self.assertEqual(env.writes[0][3], "Heiss-Light.profile")
        self.assertEqual(results["portal"].status, "ok")

    def test_idempotent_second_run_changes_nothing(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        run(env)
        env.writes.clear()
        results, _, _ = run(env)
        self.assertEqual(env.writes, [])
        self.assertEqual(results["konsole"].status, "ok")

    def test_custom_scheme_is_left_alone(self):
        env = FakeEnv(scheme="BreezeDark")
        results, rc, _ = run(env)
        self.assertEqual(rc, 0)
        self.assertTrue(all(r.status == "skipped" for r in results.values()))
        self.assertEqual((env.writes, env.evals, env.calls), ([], [], []))

    def test_unreadable_scheme_is_a_failure_not_silence(self):
        env = FakeEnv(scheme=None)
        results, rc, lines = run(env)
        self.assertEqual(rc, 1)
        self.assertEqual(results["all"].status, "failed")

    def test_dry_run_writes_nothing(self):
        env = FakeEnv(kde=lnf_kde("dark"), konsole_services=["org.kde.konsole-99"])
        results, rc, _ = run(env, dry_run=True)
        self.assertEqual((env.writes, env.evals), ([], []))
        self.assertEqual([c for c in env.calls if c[0] in ("tree", "call") and "setProfile" in c], [])
        self.assertIn("would", results["konsole"].detail)

    def test_locked_means_another_sync_is_running(self):
        results, rc, _ = run(FakeEnv(locked=True))
        self.assertEqual(rc, 0)
        self.assertEqual(results["all"].status, "skipped")

    def test_waits_for_plasmashell_then_debounces(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        env.running = False
        slept = []
        ts.sync(env, wait=True, sleep=slept.append)
        self.assertEqual(slept.count(1), 60)      # gave plasmashell 60 s
        self.assertEqual(slept[-1], 2)            # then waited for the settings to settle


class Targets(unittest.TestCase):
    def test_konsole_running_sessions_switched(self):
        env = FakeEnv(kde=lnf_kde("light"), scheme="HeissLight", konsole_services=["org.kde.konsole-7"])
        r, _, _ = run(env)
        sets = [c for c in env.calls if "setProfile" in c]
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0][-1], "Heiss Light")
        self.assertIn("2 running session", r["konsole"].detail)

    def test_konsole_missing_profile_file_changes_nothing(self):
        env = FakeEnv(kde=lnf_kde("dark"), files=[])
        r, _, _ = run(env)
        self.assertEqual(r["konsole"].status, "skipped")
        self.assertEqual(env.writes, [])

    def test_konsole_not_installed(self):
        r, _, _ = run(FakeEnv(kde=lnf_kde("dark"), commands=()))
        self.assertEqual(r["konsole"].status, "skipped")
        self.assertEqual(r["kitty"].status, "skipped")

    def test_plasma_mismatch_is_reported_with_values(self):
        kde = lnf_kde("dark")
        kde[("kdeglobals", "Icons", "Theme")] = "breeze"
        r, rc, _ = run(FakeEnv(kde=kde))
        self.assertEqual(r["plasma-consistency"].status, "warn")
        self.assertIn("expected breeze-dark got breeze", r["plasma-consistency"].detail)
        self.assertEqual(rc, 0)    # warnings do not fail the unit

    def test_accent_color_is_not_compared(self):
        kde = lnf_kde("dark")
        kde[("kdeglobals", "General", "AccentColor")] = "10,20,30"
        self.assertEqual(run(FakeEnv(kde=kde))[0]["plasma-consistency"].status, "ok")

    def test_gtk_module_missing_fails(self):
        r, rc, _ = run(FakeEnv(kde=lnf_kde("dark"), kded_modules="as 1 other"))
        self.assertEqual(r["gtk"].status, "failed")
        self.assertEqual(rc, 1)

    def test_gtk_gsettings_mismatch_warns(self):
        r, rc, _ = run(FakeEnv(kde=lnf_kde("dark"), gsettings="default"))
        self.assertEqual(r["gtk"].status, "warn")

    def test_portal_wrong_value_warns_and_unreachable_warns(self):
        self.assertEqual(run(FakeEnv(kde=lnf_kde("dark"), portal=2))[0]["portal"].status, "warn")
        self.assertEqual(run(FakeEnv(kde=lnf_kde("dark"), portal=None))[0]["portal"].status, "warn")

    def test_plasmashell_refusal_fails_launcher_target(self):
        r, rc, _ = run(FakeEnv(kde=lnf_kde("dark"), plasma_ok=False))
        self.assertEqual(r["launcher-icon"].status, "failed")
        self.assertEqual(rc, 1)

    def test_a_crashing_target_does_not_hide_the_others(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        env.gsettings = lambda *a: 1 / 0
        r, rc, _ = run(env)
        self.assertEqual(r["gtk"].status, "failed")
        self.assertIn("ZeroDivisionError", r["gtk"].detail)
        self.assertEqual(r["portal"].status, "ok")

    def test_light_and_dark_defaults_are_complete(self):
        for t in ("dark", "light"):
            self.assertEqual(len(lnf_kde(t)), len(ts.CHECKED_KEYS), t)


class Cli(unittest.TestCase):
    def test_status_is_read_only_and_prints_lines(self):
        env, out = FakeEnv(kde=lnf_kde("dark")), io.StringIO()
        rc = cli.main(["theme", "status"], out=out, theme_env=env)
        self.assertEqual(rc, 0)
        self.assertEqual((env.writes, env.evals, env.logged), ([], [], []))
        self.assertEqual(len(out.getvalue().splitlines()), len(ts.TARGETS_ORDER))

    def test_sync_logs_every_line_and_returns_failure_code(self):
        env, out = FakeEnv(kde=lnf_kde("dark"), kded_modules="as 0"), io.StringIO()
        rc = cli.main(["theme", "sync", "--no-wait"], out=out, theme_env=env)
        self.assertEqual(rc, 1)
        self.assertEqual(len(env.logged), len(ts.TARGETS_ORDER))


if __name__ == "__main__":
    unittest.main()
