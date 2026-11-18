import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import cli, theme as th  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
GENERATED = os.path.join(REPO, "branding", "tokens", "generated", "desktop")


class FakeEnv(th.RealEnv):
    """Real file handling in a temporary home and source tree; commands are scripted and recorded."""

    def __init__(self, tmp, session=True, scripted=None, wallpapers=True, src=GENERATED):
        super().__init__(home=os.path.join(tmp, "home"), src_root=src,
                         environ={"HYPRLAND_INSTANCE_SIGNATURE": "x"} if session else {})
        os.makedirs(self.home, exist_ok=True)
        self.tmp = tmp
        self.calls, self.spawned, self.scripted = [], [], dict(scripted or {})
        self.gs = "'prefer-dark'"
        self.wall = {}
        if wallpapers:
            for t, p in th.WALLPAPERS.items():
                self.wall[p] = os.path.join(tmp, "wall-" + t)
                open(self.wall[p], "w").close()

    def exists(self, path):
        return path in self.wall or super().exists(path)

    def run(self, argv, timeout=10):
        self.calls.append(list(argv))
        key = " ".join(argv)
        for prefix, res in self.scripted.items():
            if key.startswith(prefix):
                return res
        if argv[:3] == ["gsettings", "get", "org.gnome.desktop.interface"]:
            return 0, self.gs
        if argv[:3] == ["gsettings", "set", "org.gnome.desktop.interface"]:
            self.gs = "'%s'" % argv[4]
            return 0, ""
        return 0, ""

    def spawn(self, argv):
        self.spawned.append(list(argv))
        return True

    def uid(self):
        return "1000"


class Generated(unittest.TestCase):
    def test_both_themes_ship_every_file_the_command_copies(self):
        for t in th.THEMES:
            for name in th.COLOR_FILES + ("qt6ct-colors.conf", "gtk-3.0.css", "gtk-4.0.css"):
                self.assertTrue(os.path.isfile(os.path.join(GENERATED, t, name)), (t, name))

    def test_wallpapers_are_the_shipped_packages(self):
        for p in th.WALLPAPERS.values():
            self.assertTrue(os.path.isfile(os.path.join(REPO, "profile/airootfs", p.lstrip("/"))), p)


class Apply(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.env = FakeEnv(self.d.name)

    def cfg(self, *p):
        return self.env.config(*p)

    def test_set_light_writes_everything_and_reloads(self):
        results, rc = th.apply(self.env, "light")
        self.assertEqual(rc, 0, [r.line() for r in results])
        self.assertEqual([r.target for r in results], list(th.TARGETS))
        for name in th.COLOR_FILES:
            with open(os.path.join(GENERATED, "light", name), encoding="utf-8") as f, open(self.cfg("heiss/theme", name), encoding="utf-8") as g:
                self.assertEqual(f.read(), g.read(), name)
        self.assertEqual(th.get(self.env), "light")
        self.assertEqual(os.readlink(self.cfg("heiss/theme/wallpaper")), th.WALLPAPERS["light"])
        with open(self.cfg("gtk-3.0/settings.ini"), encoding="utf-8") as f:
            self.assertIn("gtk-application-prefer-dark-theme=0", f.read())
        with open(self.cfg("gtk-4.0/gtk.css"), encoding="utf-8") as f:
            self.assertIn("@define-color accent_bg_color #8c7448;", f.read())
        with open(self.cfg("qt6ct/qt6ct.conf"), encoding="utf-8") as f:
            self.assertIn("style=Fusion", f.read())
        self.assertTrue(os.path.isfile(self.cfg("qt6ct/colors/heiss.conf")))
        self.assertIn(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-light"], self.env.calls)
        self.assertIn(["hyprctl", "setcursor", "Adwaita", "24"], self.env.calls)
        self.assertIn(["hyprctl", "reload"], self.env.calls)
        self.assertIn(["makoctl", "reload"], self.env.calls)
        self.assertIn(["pkill", "-USR2", "-u", "1000", "-x", "waybar"], self.env.calls)
        self.assertEqual(self.env.spawned, [["heiss-wallpaper"]])

    def test_dark_after_light_switches_back_and_is_idempotent(self):
        th.apply(self.env, "light")
        th.apply(self.env, "dark")
        self.assertEqual(th.get(self.env), "dark")
        self.assertEqual(os.readlink(self.cfg("heiss/theme/wallpaper")), th.WALLPAPERS["dark"])
        results, rc = th.apply(self.env, "dark", live=False)
        self.assertEqual(rc, 0)
        self.assertEqual([r.status for r in results if r.target in ("colors", "wallpaper", "gtk", "qt", "color-scheme")], ["ok"] * 5)

    def test_dry_run_changes_nothing_and_runs_no_set_command(self):
        results, rc = th.apply(self.env, "light", dry_run=True)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.cfg("heiss")))
        self.assertFalse(os.path.exists(self.cfg("gtk-3.0")))
        self.assertEqual([c for c in self.env.calls if c[:2] in (["gsettings", "set"], ["hyprctl", "reload"])], [])
        self.assertEqual(self.env.spawned, [])
        self.assertTrue(any(r.status == "changed" and r.detail.startswith("would") for r in results))

    def test_outside_a_session_nothing_is_reloaded(self):
        env = FakeEnv(self.d.name, session=False)
        results, rc = th.apply(env, "light")
        self.assertEqual(rc, 0)
        by = {r.target: r for r in results}
        self.assertEqual(by["cursor"].status, "skipped")
        self.assertEqual(by["reload"].status, "skipped")
        self.assertFalse([c for c in env.calls if c[0] in ("hyprctl", "makoctl", "pkill")])

    def test_a_chosen_wallpaper_and_foreign_files_are_left_alone(self):
        os.makedirs(self.cfg("heiss/theme"))
        os.symlink("/home/me/pic.png", self.cfg("heiss/theme/wallpaper"))
        os.makedirs(self.cfg("gtk-3.0"))
        mine = self.cfg("gtk-3.0/gtk.css")
        with open(mine, "w", encoding="utf-8") as f:
            f.write("/* my own */\n")
        os.makedirs(self.cfg("qt6ct"))
        with open(self.cfg("qt6ct/qt6ct.conf"), "w", encoding="utf-8") as f:
            f.write("[Appearance]\nstyle=Breeze\n")
        results, rc = th.apply(self.env, "light")
        self.assertEqual(rc, 0)
        by = {r.target: r for r in results}
        self.assertEqual(by["wallpaper"].status, "skipped")
        self.assertEqual(os.readlink(self.cfg("heiss/theme/wallpaper")), "/home/me/pic.png")
        self.assertEqual(by["gtk"].status, "warn")
        with open(mine, encoding="utf-8") as f:
            self.assertEqual(f.read(), "/* my own */\n")
        self.assertEqual(by["qt"].status, "warn")
        with open(self.cfg("qt6ct/qt6ct.conf"), encoding="utf-8") as f:
            self.assertIn("style=Breeze", f.read())
        self.assertTrue(os.path.isfile(self.cfg("qt6ct/colors/heiss.conf")))

    def test_missing_theme_files_fail_visibly_and_do_not_hide_the_others(self):
        env = FakeEnv(self.d.name, src=os.path.join(self.d.name, "empty"))
        results, rc = th.apply(env, "light")
        by = {r.target: r for r in results}
        self.assertEqual(rc, 1)
        for t in ("colors", "gtk", "qt"):
            self.assertEqual(by[t].status, "failed", t)
        self.assertEqual(by["color-scheme"].status, "changed")

    def test_gsettings_missing_or_failing(self):
        env = FakeEnv(self.d.name, scripted={"gsettings": (127, "no such file")})
        self.assertEqual({r.target: r for r in th.apply(env, "light")[0]}["color-scheme"].status, "skipped")
        env = FakeEnv(self.d.name, scripted={"gsettings get": (0, "'prefer-dark'"), "gsettings set": (1, "no dconf")})
        results, rc = th.apply(env, "light")
        self.assertEqual(rc, 1)
        self.assertEqual({r.target: r for r in results}["color-scheme"].status, "failed")

    def test_a_crash_in_one_target_is_reported(self):
        env = FakeEnv(self.d.name)
        env.set_link = lambda *a: 1 / 0
        results, rc = th.apply(env, "light")
        self.assertEqual({r.target: r for r in results}["wallpaper"].status, "failed")
        self.assertEqual(rc, 1)
        self.assertEqual({r.target: r for r in results}["gtk"].status, "changed")

    def test_unknown_names_are_refused(self):
        for bad in ("auto", "", "DARK", "../x", None):
            with self.assertRaises(ValueError):
                th.apply(self.env, bad)

    def test_only_fixed_argument_lists_and_no_shell(self):
        th.apply(self.env, "light")
        for argv in self.env.calls:
            self.assertIsInstance(argv, list)
            self.assertNotIn(argv[0], ("sh", "bash"))
        with open(th.__file__, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("shell=True", text)


class InitAndStatus(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.env = FakeEnv(self.d.name, session=False)

    def test_init_puts_dark_in_place_once_and_never_reloads(self):
        results, rc = th.init(self.env)
        self.assertEqual(rc, 0)
        self.assertEqual(th.get(self.env), "dark")
        self.assertFalse([c for c in self.env.calls if c[0] in ("hyprctl", "makoctl", "pkill")])
        th.apply(self.env, "light", live=False)
        self.env.calls.clear()
        results, rc = th.init(self.env)                       # a later choice is never overridden
        self.assertEqual(th.get(self.env), "light")
        self.assertEqual(self.env.calls, [])
        self.assertEqual(results[0].status, "ok")

    def test_status_is_read_only_and_reports_drift(self):
        results, rc = th.status(self.env)
        self.assertEqual(results[0].status, "warn")           # nothing set yet
        th.apply(self.env, "dark", live=False)
        results, rc = th.status(self.env)
        self.assertEqual([r.status for r in results[1:]], ["ok"] * 5)
        path = self.env.config("heiss/theme/mako.conf")
        with open(path, "w", encoding="utf-8") as f:
            f.write("edited\n")
        calls = len(self.env.calls)
        results, rc = th.status(self.env)
        self.assertEqual({r.target: r.status for r in results}["colors"], "warn")
        self.assertIn("differs from the dark theme", {r.target: r.detail for r in results}["colors"])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "edited\n")           # status wrote nothing
        self.assertEqual([c for c in self.env.calls[calls:] if c[:2] == ["gsettings", "set"]], [])


class Cli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.env = FakeEnv(self.d.name, session=False)

    def run_cli(self, *argv):
        out = io.StringIO()
        rc = cli.main(["theme", *argv], out=out, theme_env=self.env)
        return rc, out.getvalue()

    def test_get_set_and_status(self):
        self.assertEqual(self.run_cli("get"), (1, ""))
        rc, out = self.run_cli("set", "light")
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.splitlines()), len(th.TARGETS))
        self.assertTrue(all(l.startswith("theme: ") for l in out.splitlines()))
        self.assertEqual(self.run_cli("get"), (0, "light\n"))
        rc, out = self.run_cli("status")
        self.assertEqual(rc, 0)
        self.assertIn("current theme: light", out)

    def test_set_rejects_unknown_names(self):
        with self.assertRaises(SystemExit):
            self.run_cli("set", "auto")

    def test_set_dry_run_prints_would_and_writes_nothing(self):
        rc, out = self.run_cli("set", "dark", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("would write", out)
        self.assertEqual(self.run_cli("get")[0], 1)

    def test_a_failure_gives_exit_code_1(self):
        self.env.src_root = os.path.join(self.d.name, "nothing")
        rc, out = self.run_cli("set", "dark")
        self.assertEqual(rc, 1)
        self.assertIn("failed", out)


class RealCommands(unittest.TestCase):
    def test_real_env_runs_in_a_temporary_home(self):
        with tempfile.TemporaryDirectory() as d:
            env = th.RealEnv(home=d, src_root=GENERATED, environ={"PATH": "/usr/bin:/bin"})
            results, rc = th.apply(env, "dark", live=False)
            self.assertIn(rc, (0, 1))
            self.assertTrue(os.path.isfile(os.path.join(d, ".config/heiss/theme/hypr-colors.conf")))
            self.assertEqual(sorted(os.listdir(d)), [".config"])      # nothing outside the config directory
            if os.path.lexists(os.path.join(d, ".config/heiss/theme/wallpaper")):
                self.assertEqual(os.readlink(os.path.join(d, ".config/heiss/theme/wallpaper")), th.WALLPAPERS["dark"])
            self.assertEqual(subprocess.run(["true"]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
