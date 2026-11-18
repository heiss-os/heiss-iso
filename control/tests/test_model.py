import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import hyprcfg  # noqa: E402
from heiss_control import model as m  # noqa: E402
from heiss_control import system_tools as sysx  # noqa: E402
from heiss_control.strings import S  # noqa: E402

SHIPPED = os.path.join(REPO, "desktop", "hypr", "hyprland.lua")


class Calls:
    def __init__(self, reload_rc=0):
        self.runs, self.launched, self.themes, self.reload_rc = [], [], [], reload_rc

    def run(self, argv, timeout=10):
        self.runs.append(argv)
        if argv[0] == "hyprctl":
            return self.reload_rc, "" if self.reload_rc == 0 else "no instance"
        if argv[0] == "nmcli":
            return 0, "connected:full\n"
        return 127, ""

    def launch(self, key):
        self.launched.append(key)
        return (key != "bluetooth", "blueman-manager" if key == "bluetooth" else key)

    def apply_theme(self, theme):
        self.themes.append(theme)
        return (theme == "dark", "" if theme == "dark" else "boom")


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        os.makedirs(os.path.join(self.d, "hypr"))
        shutil.copy(SHIPPED, os.path.join(self.d, "hypr", "hyprland.lua"))
        self.calls = Calls()
        self.env = m.Env(cfg_dir=self.d, os_release=os.path.join(self.d, "os-release"), system_answers=os.path.join(self.d, "no.toml"),
                         state_file=os.path.join(self.d, "no.json"), profiles_dir=os.path.join(REPO, "profiles"),
                         theme_get=lambda: "dark", apply_theme=self.calls.apply_theme, run=self.calls.run, launch=self.calls.launch,
                         monitors=lambda: [{"name": "A", "width": 1920, "height": 1080, "refresh": 60.0, "scale": 1.0}],
                         layouts=lambda: {"us", "ru", "de"}, hardware_data=lambda: {"facts": [], "drivers": [], "report": "r"},
                         run_check=lambda: [], kernel=lambda: "6.1")
        self.m = m.Model(self.env)

    def do(self, job, arg=""):
        ok = self.m.begin(job, arg)
        if ok:
            self.m.finish(job, arg)
        return ok

    def blocks(self, page):
        self.m.open(page)
        return self.m.screen()["blocks"]

    def user(self):
        with open(os.path.join(self.d, "hypr", "heiss-user.lua"), encoding="utf-8") as f:
            return f.read()


class Jobs(Base):
    def test_unknown_jobs_and_values_are_refused_and_nothing_runs(self):
        for job, arg in (("rm", ""), ("theme", "blue"), ("modifier", "CTRL"), ("modifier", "alt"), ("scale", "3"), ("scale", "1;x"),
                         ("launch", "sh"), ("launch", "../bin/sh"), ("layout", "us;rm"), ("layout", "US"), ("layout", ""), ("theme", None)):
            self.assertFalse(self.m.begin(job, arg), (job, arg))
        self.assertEqual((self.calls.runs, self.calls.launched, self.calls.themes), ([], [], []))
        self.assertEqual(self.m.busy, "")

    def test_one_job_at_a_time(self):
        self.assertTrue(self.m.begin("theme", "dark"))
        self.assertFalse(self.m.begin("scale", "1"))
        self.m.finish("theme", "dark")
        self.assertEqual(self.m.busy, "")
        self.assertTrue(self.m.begin("scale", "1"))

    def test_theme_success_and_failure_show_their_message(self):
        self.do("theme", "dark")
        self.m.open("appearance")
        self.assertEqual(self.m.msg["theme"][0], "ok")
        self.do("theme", "light")
        self.assertEqual(self.m.msg["theme"][0], "error")
        self.assertIn("boom", self.m.msg["theme"][1])

    def test_modifier_is_written_and_hyprland_reloaded_and_the_page_shows_it(self):
        self.do("modifier", "SUPER")
        self.assertEqual(hyprcfg.read_modifier(self.d), "SUPER")
        self.assertIn(["hyprctl", "reload"], self.calls.runs)
        self.assertEqual(self.m.msg["modifier"][0], "ok")
        ch = [b for b in self.blocks("keyboard") if b["type"] == "choice"][0]
        self.assertEqual([o["value"] for o in ch["options"] if o["selected"]], ["SUPER"])
        self.assertTrue(ch["enabled"])
        # and the welcome window's reader sees the same
        self.assertTrue(all(b.keys[0] == "SUPER" for b in hyprcfg.load(self.d).bindings if b.keys[0] in ("ALT", "SUPER")))

    def test_a_failed_reload_is_a_warning_not_a_lost_setting(self):
        self.calls.reload_rc = 1
        self.do("modifier", "SUPER")
        self.assertEqual(hyprcfg.read_modifier(self.d), "SUPER")
        self.assertEqual(self.m.msg["modifier"][0], "warn")

    def test_an_own_configuration_disables_the_switch_and_says_why(self):
        with open(os.path.join(self.d, "hypr", "hyprland.lua"), "w", encoding="utf-8") as f:
            f.write('local mainMod = "SUPER"\n')
        blocks = self.blocks("keyboard")
        ch = [b for b in blocks if b["type"] == "choice"][0]
        self.assertFalse(ch["enabled"])
        self.assertEqual([o["value"] for o in ch["options"] if o["selected"]], ["SUPER"])
        self.assertTrue([b for b in blocks if b["type"] == "message" and b["tone"] == "warn"])

    def test_layout_is_validated_against_the_system_list_and_written_as_a_block(self):
        for bad in ("xx", "us,xx", "usa1", "us,ru,de,us,ru"):
            self.assertFalse(self.do("layout", bad), bad)
        self.assertEqual(self.m.msg["layout"][0], "error")
        self.assertFalse(os.path.exists(os.path.join(self.d, "hypr", "heiss-user.lua")))
        self.assertTrue(self.do("layout", "us,ru"))
        t = self.user()
        self.assertIn('kb_layout = "us,ru", kb_options = "grp:ctrl_shift_toggle"', t)
        self.assertTrue(self.do("layout", "de"))
        self.assertNotIn("ctrl_shift_toggle", self.user())
        field = [b for b in self.blocks("keyboard") if b["type"] == "field"][0]
        self.assertEqual(field["value"], "de")

    def test_layout_without_the_system_list_still_checks_the_shape(self):
        self.env.layouts = lambda: set()
        self.assertTrue(self.do("layout", "xx"))
        self.assertFalse(self.do("layout", "x"))

    def test_scale_is_written_and_shown(self):
        self.do("scale", "1.5")
        self.assertIn("scale = 1.5", self.user())
        ch = [b for b in self.blocks("display") if b["type"] == "choice"][0]
        self.assertEqual([o["value"] for o in ch["options"] if o["selected"]], ["1.5"])

    def test_user_lines_outside_the_blocks_survive(self):
        with open(os.path.join(self.d, "hypr", "heiss-user.lua"), "w", encoding="utf-8") as f:
            f.write("-- mine\nhl.config({ general = { gaps_out = 30 } })\n")
        self.do("scale", "2")
        self.do("layout", "ru")
        self.assertTrue(self.user().startswith("-- mine\nhl.config({ general = { gaps_out = 30 } })"))

    def test_an_unwritable_config_is_an_error_message(self):
        os.makedirs(os.path.join(self.d, "hypr", "heiss-user.lua"))
        self.do("scale", "2")
        self.assertEqual(self.m.msg["scale"][0], "error")
        self.assertEqual(self.m.busy, "")

    def test_launch_uses_the_fixed_table_and_reports_a_missing_program(self):
        self.do("launch", "audio")
        self.do("launch", "bluetooth")
        self.assertEqual(self.calls.launched, ["audio", "bluetooth"])
        acts = {b["id"]: b for b in self.blocks("network") if b["type"] == "action"}
        self.assertEqual(acts["launch:network"]["message"], "")
        self.assertIn("blueman-manager", acts["launch:bluetooth"]["message"])

    def test_detect_and_check_fill_their_pages(self):
        self.env.hardware_data = lambda: {"facts": [{"id": "form", "status": "info", "code": "vm", "data": "oracle"},
                                                     {"id": "cpu", "status": "info", "code": "other", "data": ""}],
                                          "drivers": [{"id": "d", "name": {"en": "Driver"}, "description": {}, "warning": {}, "state": "weird"}],
                                          "report": "R" * 20000}
        self.env.run_check = lambda: [{"name": "a", "status": "BAD", "detail": "x" * 1000}]
        self.do("detect")
        self.do("check")
        hw = self.blocks("hardware")
        rows = [b for b in hw if b["type"] == "rows"]
        self.assertEqual(rows[0]["rows"][0]["value"], "Virtual machine (oracle)")
        self.assertEqual(rows[1]["rows"][0]["value"], S["en"]["hardware.state.unknown"])
        report = [b for b in hw if b["type"] == "report"][0]
        self.assertLessEqual(len(report["text"]), m.MAX_REPORT + 20)
        items = [b for b in self.blocks("system") if b["type"] == "items"][0]["items"]
        self.assertEqual(items[0]["status"], "WARN")
        self.assertLessEqual(len(items[0]["detail"]), m.MAX_MESSAGE)

    def test_a_failing_source_never_stops_the_window(self):
        def boom(*a, **k):
            raise RuntimeError("source exploded")
        for name in ("theme_get", "monitors", "kernel", "hardware_data", "run_check", "layouts"):
            setattr(self.env, name, boom)
        self.env.run = lambda argv, timeout=10: (127, "x")
        self.do("detect")
        self.do("check")
        for p in m.PAGES:
            s = self.m.screen() if self.m.open(p) is None else None
            self.assertTrue(s["blocks"], p)
            self.assertEqual(s["page"], p)
        self.assertEqual(self.m.msg["hardware"][0], "error")

    def test_copy_report_puts_the_report_on_the_clipboard(self):
        got = []
        self.m.copy_report(got.append)
        self.assertEqual(got, [])
        self.do("detect")
        self.m.copy_report(got.append)
        self.assertEqual(got, ["r"])


class Pages(Base):
    def test_every_page_has_a_title_and_a_sidebar_entry_in_both_languages(self):
        for lang in ("en", "ru"):
            self.m.set_language(lang)
            for p in m.PAGES:
                s = self.m.screen() if self.m.open(p) is None else None
                self.assertEqual(s["title"], S[lang]["page." + p])
                self.assertEqual([x["id"] for x in s["sidebar"]], list(m.PAGES))
        self.m.set_language("xx")
        self.assertEqual(self.m.language, "ru")
        self.m.open("nope")
        self.assertIn(self.m.page, m.PAGES)

    def test_system_page_links_are_https_only(self):
        with open(self.env.os_release, "w", encoding="utf-8") as f:
            f.write('PRETTY_NAME="Heiss OS"\nHOME_URL="javascript:alert(1)"\nDOCUMENTATION_URL="https://example.org/d"\nBUG_REPORT_URL="file:///etc/passwd"\n')
        links = [b for b in self.blocks("system") if b["type"] == "links"][0]["links"]
        self.assertEqual([l["url"] for l in links], ["https://example.org/d"])

    def test_network_page_shows_the_nmcli_state(self):
        rows = [b for b in self.blocks("network") if b["type"] == "rows"][0]["rows"]
        self.assertEqual(rows[0]["value"], "connected, full")

    def test_the_display_page_lists_the_screens(self):
        rows = [b for b in self.blocks("display") if b["type"] == "rows"][0]["rows"]
        self.assertEqual(rows, [{"label": "A", "value": "1920x1080, 60 Hz, 100%"}])


class Tools(unittest.TestCase):
    def test_launch_table_is_fixed_and_missing_programs_are_reported(self):
        started = []
        ok, name = sysx.launch("audio", which=lambda n: "/usr/bin/" + n, popen=lambda argv, **kw: started.append(argv))
        self.assertEqual((ok, name, started), (True, "pavucontrol", [["pavucontrol"]]))
        self.assertEqual(sysx.launch("rm -rf", which=lambda n: "x", popen=lambda *a, **k: 1 / 0), (False, "rm -rf"))
        self.assertEqual(sysx.launch("audio", which=lambda n: None)[0], False)

        def fail(*a, **k):
            raise OSError("no")
        self.assertEqual(sysx.launch("audio", which=lambda n: "x", popen=fail)[0], False)

    def test_monitors_parses_hyprctl_json_and_drops_junk(self):
        out = '[{"name":"A","width":1920,"height":1080,"refreshRate":59.94,"scale":1.5},{"name":"B"},"x",{"name":"C","width":"a","height":1}]'
        rows = sysx.monitors(lambda argv: (0, out))
        self.assertEqual(rows, [{"name": "A", "width": 1920, "height": 1080, "refresh": 59.9, "scale": 1.5}])
        for bad in ((1, ""), (0, "not json"), (0, "{}")):
            try:
                self.assertEqual(sysx.monitors(lambda argv, b=bad: b), [])
            except RuntimeError:
                pass

    def test_run_never_raises(self):
        rc, out = sysx.run(["/nonexistent-program-xyz"])
        self.assertEqual(rc, 127)

    def test_known_layouts_reads_the_xkb_list(self):
        with tempfile.NamedTemporaryFile("w", suffix=".lst") as f:
            f.write("! model\n  pc105  Generic\n\n! layout\n  us  English (US)\n  ru  Russian\n\n! variant\n  intl  us: English (intl)\n")
            f.flush()
            self.assertEqual(sysx.known_layouts(f.name), {"us", "ru"})
        self.assertEqual(sysx.known_layouts("/nonexistent"), set())


class Strings(unittest.TestCase):
    def test_every_key_the_model_uses_exists_in_both_languages(self):
        import re
        with open(os.path.join(os.path.dirname(HERE), "heiss_control", "model.py"), encoding="utf-8") as f:
            text = f.read()
        used = set(re.findall(r'self\.tr\("([a-z_.]+)"\)', text)) | set(re.findall(r'self\.tr\("([a-z_.]+)" \+', text))
        for key in used:
            if key.endswith("."):
                continue
            for lang in ("en", "ru"):
                self.assertIn(key, S[lang], key)
        for pref in ("keyboard.alt", "keyboard.super", "theme.dark", "theme.light", "hardware.state.installed", "hardware.state.missing",
                     "hardware.state.nothing", "hardware.state.unknown", "fact.form.laptop", "fact.form.desktop", "fact.form.vm",
                     "fact.cpu.named", "fact.cpu.other", "fact.gpu.some", "fact.gpu.none", "fact.hybrid.yes", "fact.bluetooth.yes",
                     "fact.bluetooth.no"):
            self.assertIn(pref, S["en"])


if __name__ == "__main__":
    unittest.main()
