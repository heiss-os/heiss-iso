import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import cli, themesync as ts  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
LNF = {t: open(os.path.join(REPO, "profile/airootfs/usr/share/plasma/look-and-feel", pkg, "contents/defaults"), encoding="utf-8").read()
       for t, pkg in ts.LNF_PACKAGE.items()}


class FakeEnv:
    """Scripted desktop. `kde` maps (file, group, key) -> value."""

    def __init__(self, scheme="HeissDark", commands=("konsole", "kitty"), files=None, kde=None, gsettings="prefer-dark",
                 portal=1, kded_modules="as 2 gtkconfig foo", konsole_services=(), locked=False, plasma_ok=True,
                 first_login_done=True, appletsrc=None, lnf_ok=True, touch_ok=True):
        self.kde = {("kdeglobals", "General", "ColorScheme"): scheme}
        self.kde.update(kde or {})
        self.commands, self.files = set(commands), set(files if files is not None else [
            "/usr/share/konsole/Heiss-Dark.profile", "/usr/share/konsole/Heiss-Light.profile",
            "/etc/xdg/kitty/dark-theme.auto.conf", "/etc/xdg/kitty/light-theme.auto.conf"])
        self.gs, self.portal, self.kded = gsettings, portal, kded_modules
        self.konsole_services, self.locked, self.plasma_ok = list(konsole_services), locked, plasma_ok
        self.writes, self.evals, self.calls, self.logged = [], [], [], []
        self.running = True
        self.home = "/home/test"
        self.touch_ok = touch_ok
        self.appletsrc, self.lnf_ok, self.lnf_applied, self.touched = appletsrc, lnf_ok, [], []
        if first_login_done:
            self.files.add("/home/test/" + ts.FIRST_LOGIN_MARK)

    def kde_read(self, file, group, key): return self.kde.get((file, group, key))

    def kde_read_nested(self, file, groups, key): return self.kde.get((file, tuple(groups), key))

    def kde_write(self, file, group, key, value):
        group = group if isinstance(group, str) else tuple(group)
        self.writes.append((file, group, key, value))
        self.kde[(file, group, key)] = value
        return True

    def apply_lnf(self, package):
        self.lnf_applied.append(package)
        if self.lnf_ok:
            self.kde[("kdeglobals", "General", "ColorScheme")] = "HeissDark"
            self.kde.update(lnf_kde("dark"))
        return self.lnf_ok

    def unmark(self, path):
        self.files.discard(path)
        self.touched = [t for t in self.touched if t != path]

    def touch(self, path):
        if not self.touch_ok:
            return False
        self.touched.append(path)
        self.files.add(path)
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
    def exists(self, path): return path in self.files or path.startswith(ts.WALLPAPER_DIR)

    def read_text(self, path):
        for t, pkg in ts.LNF_PACKAGE.items():
            if path.endswith("%s/contents/defaults" % pkg):
                return LNF[t]
        if path.endswith(ts.APPLETSRC):
            return self.appletsrc
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
                         {"launcher-icon": "ok", "wallpaper": "changed", "konsole": "changed", "plasma-consistency": "ok",
                          "gtk": "ok", "portal": "ok", "kitty": "ok"})
        self.assertIn("heiss-launcher-sand'", env.evals[0])
        self.assertIn("'file:///usr/share/wallpapers/Heiss-Everyday/'", env.evals[1])     # a package URL, not a bare id
        self.assertIn("FillMode', 2", env.evals[1])
        self.assertEqual(env.writes, [ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2], "file:///usr/share/wallpapers/Heiss-Everyday/"),
                                      ("konsolerc", "Desktop Entry", "DefaultProfile", "Heiss-Dark.profile")])

    def test_light_uses_light_values(self):
        env = FakeEnv(scheme="HeissLight", kde=lnf_kde("light"), gsettings="default", portal=2)
        results, rc, _ = run(env)
        self.assertEqual(rc, 0)
        self.assertIn("heiss-launcher-sand-light", env.evals[0])
        self.assertEqual(env.writes[0][3], "file:///usr/share/wallpapers/Heiss-Everyday-Light/")      # lock screen
        self.assertEqual(env.writes[-1][3], "Heiss-Light.profile")
        self.assertIn("'file:///usr/share/wallpapers/Heiss-Everyday-Light/'", env.evals[1])
        self.assertEqual(results["portal"].status, "ok")

    def test_idempotent_second_run_changes_nothing(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        run(env)
        env.writes.clear()
        results, _, _ = run(env)
        self.assertEqual(env.writes, [])
        self.assertEqual(results["konsole"].status, "ok")

    def test_switch_changes_scheme_wallpaper_and_konsole_together_and_back(self):
        env = FakeEnv(scheme="HeissLight", kde=lnf_kde("light"), gsettings="default", portal=2,
                      appletsrc="[C][1][Wallpaper][org.kde.image][General]\nImage=file:///usr/share/wallpapers/Heiss-Everyday-Light/\n")
        env.kde[ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])] = "file:///usr/share/wallpapers/Heiss-Everyday-Light/"
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "ok")       # already light: nothing to do
        env.kde[("kdeglobals", "General", "ColorScheme")] = "HeissDark"
        env.kde.update(lnf_kde("dark"))
        env.gs, env.portal = "prefer-dark", 1
        r, rc, _ = run(env)
        self.assertEqual((rc, r["wallpaper"].status, r["konsole"].status), (0, "changed", "changed"))
        self.assertIn("'file:///usr/share/wallpapers/Heiss-Everyday/'", env.evals[-1])
        self.assertEqual(env.kde[ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])], "file:///usr/share/wallpapers/Heiss-Everyday/")
        self.assertEqual(env.kde[("konsolerc", "Desktop Entry", "DefaultProfile")], "Heiss-Dark.profile")

    def test_sync_is_idempotent_for_wallpaper_too(self):
        env = FakeEnv(kde=lnf_kde("dark"), appletsrc="[C][1][Wallpaper][org.kde.image][General]\nImage=file:///usr/share/wallpapers/Heiss-Everyday/\n")
        env.kde[ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])] = "file:///usr/share/wallpapers/Heiss-Everyday/"
        run(env)
        env.writes.clear()
        env.evals.clear()
        r, _, _ = run(env)
        self.assertEqual((r["wallpaper"].status, r["konsole"].status), ("ok", "ok"))
        self.assertEqual(env.writes, [])
        self.assertFalse([e for e in env.evals if "writeConfig('Image'" in e])

    def test_a_wallpaper_the_user_chose_is_left_alone(self):
        env = FakeEnv(kde=lnf_kde("dark"), appletsrc="[C][1][Wallpaper][org.kde.image][General]\nImage=file:///home/u/me.jpg\n")
        env.kde[ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])] = "/home/u/lock.png"
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "skipped")
        self.assertFalse([e for e in env.evals if "writeConfig('Image'" in e])
        self.assertFalse([w for w in env.writes if w[0] == "kscreenlockerrc"])

    def test_a_bare_id_from_the_first_image_is_rewritten_to_the_url(self):
        lock = ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])
        env = FakeEnv(kde=lnf_kde("dark"), appletsrc="[C][1][Wallpaper][org.kde.image][General]\nImage=Heiss-Everyday\n")
        env.kde[lock] = "Heiss-Everyday"
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "changed")
        self.assertIn("'file:///usr/share/wallpapers/Heiss-Everyday/'", env.evals[1])
        self.assertEqual(env.kde[lock], "file:///usr/share/wallpapers/Heiss-Everyday/")
        env.evals.clear()
        env.appletsrc = "[C][1][Wallpaper][org.kde.image][General]\nImage=file:///usr/share/wallpapers/Heiss-Everyday/\n"
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "ok")

    def test_wallpaper_dry_run_and_plasma_refusal(self):
        env = FakeEnv(kde=lnf_kde("dark"))
        r, _, _ = run(env, dry_run=True)
        self.assertEqual((r["wallpaper"].status, env.writes, env.evals), ("changed", [], []))
        r, rc, _ = run(FakeEnv(kde=lnf_kde("dark"), plasma_ok=False))
        self.assertEqual((r["wallpaper"].status, rc), ("failed", 1))

    def test_first_login_on_another_theme_applies_heiss_dark_once(self):
        env = FakeEnv(scheme="BreezeDark", first_login_done=False)
        r, rc, lines = run(env)
        self.assertEqual(env.lnf_applied, ["org.heiss.dark.desktop"])
        self.assertEqual((r["first-login"].status, rc), ("changed", 0))
        self.assertIn("BreezeDark", r["first-login"].detail)
        self.assertEqual(r["konsole"].status, "changed")     # then the normal targets ran on Heiss Dark
        self.assertEqual(env.touched, ["/home/test/" + ts.FIRST_LOGIN_MARK])
        env.kde[("kdeglobals", "General", "ColorScheme")] = "BreezeDark"      # the user picks Breeze later
        env.lnf_applied.clear()
        r, _, _ = run(env)
        self.assertEqual(env.lnf_applied, [])
        self.assertNotIn("first-login", r)

    def test_first_login_already_heiss_only_writes_the_mark(self):
        env = FakeEnv(kde=lnf_kde("dark"), first_login_done=False)
        r, _, _ = run(env)
        self.assertEqual(env.lnf_applied, [])
        self.assertNotIn("first-login", r)
        self.assertEqual(len(env.touched), 1)

    def test_first_login_failure_is_visible_and_retried_next_login(self):
        env = FakeEnv(scheme="BreezeDark", first_login_done=False, lnf_ok=False)
        r, rc, _ = run(env)
        self.assertEqual((r["first-login"].status, rc), ("failed", 1))
        self.assertEqual(env.touched, [])

    def test_first_login_leaves_a_custom_scheme_alone(self):
        env = FakeEnv(scheme="MyOwnScheme", first_login_done=False)
        r, _, _ = run(env)
        self.assertEqual((env.lnf_applied, len(env.touched)), ([], 1))
        self.assertNotIn("first-login", r)

    def test_first_login_without_a_writable_mark_does_not_switch(self):
        env = FakeEnv(scheme="BreezeDark", first_login_done=False, touch_ok=False)
        r, rc, _ = run(env)
        self.assertEqual((env.lnf_applied, r["first-login"].status, rc), ([], "warn", 0))

    def test_wallpaper_ids_are_normalised_and_other_applets_ignored(self):
        lock = ts.LOCKSCREEN[:1] + (ts.LOCKSCREEN[1], ts.LOCKSCREEN[2])
        env = FakeEnv(kde=lnf_kde("dark"), appletsrc="[A][1]\nImage=/pic/frame.png\n[C][1][Wallpaper][org.kde.image][General]\n"
                      "Image=file:///usr/share/wallpapers/Heiss-Everyday/\n")
        env.kde[lock] = "file:///usr/share/wallpapers/Heiss-Everyday/"
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "ok")
        env = FakeEnv(kde=lnf_kde("dark"), appletsrc="[C][1][Wallpaper][org.kde.image][General]\nImage = Heiss-Everyday-Light\n")
        r, _, _ = run(env)
        self.assertEqual(r["wallpaper"].status, "changed")

    def test_first_login_is_skipped_by_dry_run(self):
        env = FakeEnv(scheme="BreezeDark", first_login_done=False)
        run(env, dry_run=True)
        self.assertEqual((env.lnf_applied, env.touched), ([], []))

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


class RealLock(unittest.TestCase):
    """RealEnv.lock against a scratch directory: never /tmp, never a symlink, never someone else's file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = os.path.join(self.tmp.name, "run")
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.run_dir, mode=0o700)
        os.makedirs(self.home)
        self.env = ts.RealEnv()
        self.env.home = self.home
        self.env.append_log = lambda line: self.logged.append(line)
        self.logged = []

    def patched(self, **kw):
        base = {"XDG_RUNTIME_DIR": self.run_dir, "XDG_STATE_HOME": os.path.join(self.home, "state")}
        base.update(kw)
        return mock.patch.dict(os.environ, base, clear=False)

    def test_lock_file_is_in_the_runtime_dir_mode_0600(self):
        with self.patched(), self.env.lock() as got:
            self.assertTrue(got)
        st = os.stat(os.path.join(self.run_dir, "heiss-theme-sync.lock"))
        self.assertEqual(st.st_mode & 0o777, 0o600)

    def test_second_lock_while_held_is_refused(self):
        with self.patched(), self.env.lock() as first:
            with self.env.lock() as second:
                self.assertEqual((first, second), (True, False))

    def test_world_writable_runtime_dir_is_not_used_and_tmp_is_never_used(self):
        os.chmod(self.run_dir, 0o777)
        with self.patched(), self.env.lock() as got:
            self.assertTrue(got)
        self.assertEqual(os.listdir(self.run_dir), [])
        self.assertTrue(os.path.exists(os.path.join(self.home, "state", "heiss", "heiss-theme-sync.lock")))
        self.assertEqual(oct(os.stat(os.path.join(self.home, "state", "heiss")).st_mode & 0o777), "0o700")

    def test_unset_or_relative_runtime_dir_falls_back_to_the_state_dir(self):
        for value in ("", "relative/dir"):
            with self.patched(XDG_RUNTIME_DIR=value), self.env.lock() as got:
                self.assertTrue(got, value)
        self.assertTrue(os.path.exists(os.path.join(self.home, "state", "heiss", "heiss-theme-sync.lock")))

    def test_a_planted_symlink_is_not_followed(self):
        target = os.path.join(self.tmp.name, "victim")
        os.symlink(target, os.path.join(self.run_dir, "heiss-theme-sync.lock"))
        with self.patched(), self.env.lock() as got:
            self.assertTrue(got)          # runs without a lock instead
        self.assertFalse(os.path.exists(target))
        self.assertTrue(any("without a lock" in l for l in self.logged))

    def test_a_lock_file_of_another_user_is_not_used(self):
        real = os.fstat

        def foreign(fd):
            st = real(fd)
            return os.stat_result((st.st_mode,) + tuple(st)[1:4] + (st.st_uid + 1,) + tuple(st)[5:])
        with self.patched(), mock.patch("heiss_core.themesync.os.fstat", foreign), self.env.lock() as got:
            self.assertTrue(got)
        self.assertTrue(any("without a lock" in l for l in self.logged))

    def test_a_loose_state_dir_of_ours_is_tightened_and_a_symlinked_one_refused(self):
        state = os.path.join(self.home, "state")
        os.makedirs(os.path.join(state, "heiss"), mode=0o775)
        os.chmod(os.path.join(state, "heiss"), 0o775)
        with self.patched(XDG_RUNTIME_DIR=""), self.env.lock() as got:
            self.assertTrue(got)
        self.assertEqual(os.stat(os.path.join(state, "heiss")).st_mode & 0o777, 0o700)
        self.assertEqual(self.logged, [])
        os.rename(os.path.join(state, "heiss"), os.path.join(state, "real"))
        os.symlink(os.path.join(state, "real"), os.path.join(state, "heiss"))
        with self.patched(XDG_RUNTIME_DIR=""), self.env.lock() as got:
            self.assertTrue(got)
        self.assertTrue(any("without a lock" in l for l in self.logged))

    def test_relative_state_home_is_ignored(self):
        with self.patched(XDG_RUNTIME_DIR="", XDG_STATE_HOME="rel/state"), self.env.lock() as got:
            self.assertTrue(got)
        self.assertTrue(os.path.exists(os.path.join(self.home, ".local", "state", "heiss", "heiss-theme-sync.lock")))
        self.assertFalse(os.path.exists("rel/state"))

    def test_no_usable_directory_runs_without_a_lock(self):
        blocker = os.path.join(self.tmp.name, "file")
        open(blocker, "w").close()
        self.env.home = blocker
        with self.patched(XDG_RUNTIME_DIR="", XDG_STATE_HOME=""), self.env.lock() as got:
            self.assertTrue(got)
        self.assertTrue(self.logged)


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
        self.assertEqual([w for w in env.writes if w[0] == "konsolerc"], [])

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
