import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_control import model as m  # noqa: E402
from heiss_control import theme as th  # noqa: E402
from heiss_control.strings import S  # noqa: E402

OS_RELEASE = 'NAME="Heiss OS"\nPRETTY_NAME="Heiss OS"\nBUILD_ID=rolling\nHOME_URL="https://example.org/h"\n' \
             'BUG_REPORT_URL="https://example.org/b"\n'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.env = m.Env(os_release=self.p("os-release"), system_answers=self.p("profile.toml"),
                         user_dir=self.p("user"), state_file=self.p("state.json"),
                         kernel=lambda: "9.9.9-test", plasma=lambda: "6.8.2",
                         profiles_dir=os.path.join(REPO, "profiles"), kde_value=lambda f, g, k: "HeissDark",
                         apply_theme=lambda theme: (True, ""))

    def p(self, name):
        return os.path.join(self.d, name)

    def write(self, name, text):
        os.makedirs(os.path.dirname(self.p(name)), exist_ok=True)
        with open(self.p(name), "w", encoding="utf-8") as f:
            f.write(text)

    def cards(self, model=None):
        return {c["id"]: c for c in (model or m.Model(self.env)).overview()["cards"]}


class Pages(Fixture):
    def test_sidebar_has_every_page_once_and_marks_the_current_one(self):
        side = m.Model(self.env).sidebar()
        self.assertEqual([s["id"] for s in side], list(m.PAGE_IDS))
        self.assertEqual([s["id"] for s in side if s["current"]], ["overview"])

    def test_open_ignores_unknown_pages(self):
        mod = m.Model(self.env)
        mod.open("about")
        mod.open("../etc/passwd")
        self.assertEqual(mod.page, "about")

    def test_unbuilt_page_is_marked_soon_and_has_no_data(self):
        mod = m.Model(self.env)
        mod.open("security")
        s = mod.screen()
        self.assertFalse(s["built"])
        for key in ("overview", "profiles", "appearance", "about"):
            self.assertNotIn(key, s)

    def test_every_language_has_every_key_of_english(self):
        self.assertEqual(set(S["ru"]), set(S["en"]))

    def test_every_page_has_title_and_keywords_in_both_languages(self):
        for lang in S:
            for p in m.PAGE_IDS:
                self.assertTrue(S[lang]["page." + p] and S[lang]["kw." + p], (lang, p))

    def test_no_string_key_is_defined_twice_in_one_language(self):
        import ast
        with open(os.path.join(os.path.dirname(HERE), "heiss_control", "strings.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        table = next(n.value for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "S")
        for lang, sub in zip(table.keys, table.values):
            keys = [k.value for k in sub.keys]
            self.assertEqual([k for k in set(keys) if keys.count(k) > 1], [], lang.value)

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(m.Model(self.env, "de").language, "en")


class Search(Fixture):
    def test_empty_query_finds_nothing(self):
        self.assertEqual(m.Model(self.env).search("   "), [])

    def test_title_match_comes_before_keyword_match(self):
        ids = [h["id"] for h in m.Model(self.env).search("update")]
        self.assertEqual(ids[0], "updates")

    def test_keyword_and_case_insensitive(self):
        self.assertEqual([h["id"] for h in m.Model(self.env).search("WIREGUARD")], ["network"])

    def test_all_words_must_match(self):
        self.assertEqual(m.Model(self.env).search("wireguard nvidia"), [])

    def test_russian_search(self):
        self.assertEqual([h["id"] for h in m.Model(self.env, "ru").search("брандмауэр")], ["security"])

    def test_hit_says_whether_the_page_is_built(self):
        self.assertEqual(m.Model(self.env).search("kernel")[0], {"id": "about", "title": "About", "built": True})


class Overview(Fixture):
    def test_nothing_saved_yet_is_shown_as_not_set_not_as_an_error(self):
        c = self.cards()
        self.assertEqual(c["profile"]["value"], "not set yet")
        self.assertEqual(c["profile"]["error"], "")
        self.assertEqual(c["managed"]["value"], "0")
        self.assertEqual(c["pending"]["value"], "0")
        self.assertEqual(c["kernel"]["value"], "9.9.9-test")

    def test_system_answers_win_over_user_answers(self):
        self.write("profile.toml", 'schema_version = 1\nprofile = "cyber"\n[privacy]\nlevel = "maximum"\n')
        self.write("user/answers.toml", 'schema_version = 1\nprofile = "developer"\n')
        c = self.cards()
        self.assertEqual(c["profile"]["value"], "Cyber")
        self.assertEqual(c["privacy"]["value"], "Maximum")

    def test_user_answers_used_when_there_is_no_system_file(self):
        self.write("user/answers.toml", 'schema_version = 1\nprofile = "developer"\n')
        self.assertEqual(self.cards()["profile"]["value"], "Developer")

    def test_broken_answers_give_an_error_on_the_card_and_other_cards_still_work(self):
        self.write("profile.toml", "this is = = not toml")
        c = self.cards()
        self.assertEqual(c["profile"]["value"], "unknown")
        self.assertTrue(c["profile"]["error"].startswith("Could not read"))
        self.assertEqual(c["kernel"]["value"], "9.9.9-test")

    def test_state_file_counts_packages(self):
        self.write("state.json", json.dumps({"schema_version": 1, "packages": ["a", "b"], "services": [], "flatpaks": []}))
        self.assertEqual(self.cards()["managed"]["value"], "2")

    def test_broken_state_is_an_error_on_its_card_only(self):
        self.write("state.json", "{")
        c = self.cards()
        self.assertTrue(c["managed"]["error"])
        self.assertEqual(c["pending"]["error"], "")

    def test_pending_counts_and_detail(self):
        from heiss_core import wizard as wz
        q = wz.PendingQueue(self.p("user/pending.json"))
        q.add("apply-profile", {"profile": "base", "addons": []}, now=1)
        c = self.cards()["pending"]
        self.assertEqual((c["value"], c["detail"]), ("1", "1 waiting"))

    def test_russian_labels(self):
        c = self.cards(m.Model(self.env, "ru"))
        self.assertEqual(c["profile"]["title"], "Профиль")
        self.assertEqual(c["profile"]["value"], "пока не задан")

    def test_reading_changes_nothing(self):
        self.write("profile.toml", 'schema_version = 1\nprofile = "base"\n')
        before = sorted(os.listdir(self.d))
        m.Model(self.env).screen()
        self.assertEqual(sorted(os.listdir(self.d)), before)


class Profiles(Fixture):
    def page(self, lang="en"):
        mod = m.Model(self.env, lang)
        mod.open("profiles")
        return mod.screen()["profiles"]

    def rows(self, lang="en"):
        return {r["label"]: r["value"] for r in self.page(lang)["rows"]}

    def test_nothing_chosen_nothing_installed(self):
        r = self.rows()
        self.assertEqual((r["Chosen profile"], r["Applied profile"], r["Add-ons"]), ("not set yet", "not set yet", "none"))
        self.assertEqual([s["items"] for s in self.page()["sections"]], [[], [], []])
        self.assertEqual(self.page()["errors"], [])

    def test_names_come_from_the_manifests_in_both_languages(self):
        self.write("profile.toml", 'schema_version = 1\nprofile = "cyber"\n')
        self.assertEqual(self.rows()["Chosen profile"], "Cyber")
        self.assertEqual(self.rows("ru")["Выбранный профиль"], "Кибербезопасность")
        self.write("profile.toml", 'schema_version = 1\nprofile = "base"\n')
        self.assertEqual(self.rows("ru")["Выбранный профиль"], "Базовый")

    def test_unknown_profile_id_is_shown_as_it_is(self):
        self.write("profile.toml", 'schema_version = 1\nprofile = "zzz"\n')
        self.assertEqual(self.rows()["Chosen profile"], "zzz")

    def test_state_lists_are_sorted_and_counted(self):
        self.write("state.json", json.dumps({"schema_version": 1, "applied": {"profile": "base", "addons": []},
                                             "packages": ["b", "a"], "services": ["s.service"], "flatpaks": []}))
        p = self.page()
        self.assertEqual(self.rows()["Applied profile"], "Base")
        self.assertEqual(p["sections"][0], {"title": "Packages installed by Heiss OS (2)", "items": ["a", "b"]})
        self.assertEqual(p["sections"][2]["title"], "Flatpak apps installed by Heiss OS (0)")

    def test_long_lists_are_cut(self):
        pk = ["p%04d" % i for i in range(m.MAX_LIST + 5)]
        self.write("state.json", json.dumps({"schema_version": 1, "applied": {"profile": None, "addons": []},
                                             "packages": pk, "services": [], "flatpaks": []}))
        items = self.page()["sections"][0]["items"]
        self.assertEqual((len(items), items[-1]), (m.MAX_LIST + 1, "... +5"))

    def test_pending_items_are_listed_with_status(self):
        from heiss_core import wizard as wz
        wz.PendingQueue(self.p("user/pending.json")).add("apply-profile", {"profile": "cyber", "addons": []}, now=1)
        self.assertEqual(self.page()["pending"], [{"text": "Apply profile Cyber", "status": "waiting", "error": ""}])

    def test_each_broken_source_is_its_own_error(self):
        self.write("profile.toml", "= = =")
        self.write("state.json", "{")
        self.write("user/pending.json", "{")
        self.assertEqual(len(self.page()["errors"]), 3)

    def test_missing_manifests_directory_is_reported_and_ids_are_shown(self):
        self.env.profiles_dir = self.p("nope")
        self.write("profile.toml", 'schema_version = 1\nprofile = "cyber"\n')
        self.assertEqual(len(self.page()["errors"]), 1)
        self.assertEqual(self.rows()["Chosen profile"], "cyber")

    def test_overview_card_uses_the_profile_name(self):
        self.write("profile.toml", 'schema_version = 1\nprofile = "base"\n')
        self.assertEqual(self.cards()["profile"]["value"], "Base")


class Appearance(Fixture):
    def mod(self):
        mod = m.Model(self.env)
        mod.open("appearance")
        return mod

    def test_current_scheme_is_read_and_marked(self):
        a = self.mod().screen()["appearance"]
        self.assertEqual(a["current"], "Dark")
        self.assertEqual([(c["id"], c["selected"]) for c in a["choices"]], [("dark", True), ("light", False)])

    def test_other_or_unreadable_scheme_is_unknown(self):
        for fn in (lambda f, g, k: "BreezeDark", lambda f, g, k: None, lambda f, g, k: 1 / 0):
            self.env.kde_value = fn
            a = self.mod().screen()["appearance"]
            self.assertEqual(a["current"], "unknown")
            self.assertFalse(any(c["selected"] for c in a["choices"]))

    def test_only_dark_and_light_are_accepted_and_one_at_a_time(self):
        mod = self.mod()
        for bad in ("auto", "", None, "../x", "DARK"):
            self.assertFalse(mod.begin_theme(bad))
        self.assertEqual(mod.theme_state, "idle")
        self.assertTrue(mod.begin_theme("light"))
        self.assertFalse(mod.begin_theme("dark"))
        self.assertEqual(mod.screen()["appearance"]["state"], "running")

    def test_switch_runs_the_applier_and_reports_success(self):
        seen = []
        self.env.apply_theme = lambda t: (seen.append(t), (True, ""))[1]
        mod = self.mod()
        mod.begin_theme("light")
        mod.finish_theme("light")
        self.assertEqual((seen, mod.theme_state), (["light"], "ok"))
        self.assertTrue(mod.begin_theme("dark"))   # free again

    def test_failure_and_exception_are_reported_not_raised(self):
        mod = self.mod()
        self.env.apply_theme = lambda t: (False, "No such package")
        mod.begin_theme("dark")
        mod.finish_theme("dark")
        self.assertEqual((mod.theme_state, mod.theme_message), ("failed", "No such package"))

        def boom(t):
            raise RuntimeError("x")
        self.env.apply_theme = boom
        mod.begin_theme("dark")
        mod.finish_theme("dark")
        self.assertEqual((mod.theme_state, mod.theme_message), ("failed", "x"))


class Hardening(Fixture):
    def test_every_qml_text_is_plain_text(self):
        # Text defaults to AutoText: a package name or error string that looks like HTML would be rendered
        import re
        with open(os.path.join(os.path.dirname(HERE), "heiss_control", "qml", "Main.qml"), encoding="utf-8") as f:
            qml = f.read()
        texts = re.findall(r"(?<![A-Za-z])Text \{([^\n]*)", qml)
        self.assertGreater(len(texts), 10)
        for line in texts:
            self.assertIn("textFormat: Text.PlainText", line)

    def test_error_texts_are_cut_and_flattened(self):
        self.write("profile.toml", "x = '" + "A" * 2000 + "\n" + "B" * 50 + "'")
        err = {c["id"]: c for c in m.Model(self.env).overview()["cards"]}["profile"]["error"]
        self.assertLessEqual(len(err), m.MAX_MESSAGE)
        self.assertNotIn("\n", err)

    def test_theme_failure_message_is_cut(self):
        self.env.apply_theme = lambda t: (False, "x" * 5000)
        mod = m.Model(self.env)
        mod.begin_theme("dark")
        mod.finish_theme("dark")
        self.assertEqual(len(mod.theme_message), m.MAX_MESSAGE)

    def test_markup_in_a_pending_error_is_kept_as_text_and_cut(self):
        import json as j
        q = [{"id": 1, "kind": "apply-profile", "payload": {"profile": "base", "addons": []}, "created": 1,
              "status": "failed", "error": "<img src='http://x'>" + "y" * 1000}]
        self.write("user/pending.json", j.dumps(q))
        p = m.Model(self.env)
        p.open("profiles")
        item = p.screen()["profiles"]["pending"][0]
        self.assertTrue(item["error"].startswith("<img"))
        self.assertLessEqual(len(item["error"]), m.MAX_MESSAGE)


class ThemeModule(unittest.TestCase):
    class Run:
        def __init__(self, rc=0, out="", err="", raises=None):
            self.calls, self.rc, self.out, self.err, self.raises = [], rc, out, err, raises

        def __call__(self, argv, **kw):
            import subprocess
            self.calls.append(argv)
            if self.raises:
                raise self.raises
            return subprocess.CompletedProcess(argv, self.rc, self.out, self.err)

    def test_uses_the_shipped_look_and_feel_ids(self):
        for theme, lnf in (("dark", "org.heiss.dark.desktop"), ("light", "org.heiss.light.desktop")):
            run = self.Run()
            self.assertEqual(th.apply_theme(theme, run), (True, ""))
            self.assertEqual(run.calls, [["plasma-apply-lookandfeel", "--apply", lnf]])
            self.assertTrue(os.path.isdir(os.path.join(REPO, "profile", "airootfs", "usr", "share", "plasma",
                                                       "look-and-feel", lnf)))

    def test_unknown_theme_runs_nothing(self):
        run = self.Run()
        self.assertFalse(th.apply_theme("auto", run)[0])
        self.assertEqual(run.calls, [])

    def test_failures_return_the_last_line(self):
        self.assertEqual(th.apply_theme("dark", self.Run(rc=1, err="a\nCould not find theme")), (False, "Could not find theme"))
        ok, msg = th.apply_theme("dark", self.Run(raises=FileNotFoundError("x")))
        self.assertFalse(ok)
        self.assertIn("cannot switch the theme", msg)

    def test_kreadconfig_reads_with_a_fixed_argument_list(self):
        run = self.Run(out="HeissLight\n")
        self.assertEqual(th.kreadconfig("kdeglobals", "General", "ColorScheme", run), "HeissLight")
        self.assertEqual(run.calls, [["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"]])
        self.assertEqual(th.kreadconfig("a", "b", "c", self.Run(rc=1)), "")


class About(Fixture):
    def test_rows_and_links_from_os_release(self):
        self.write("os-release", OS_RELEASE)
        mod = m.Model(self.env)
        mod.open("about")
        a = mod.screen()["about"]
        rows = {r["label"]: r["value"] for r in a["rows"]}
        self.assertEqual(rows, {"System": "Heiss OS", "Build": "rolling", "Kernel": "9.9.9-test", "Plasma": "6.8.2"})
        self.assertEqual([l["label"] for l in a["links"]], ["Project", "Report a problem"])
        self.assertIn("Heiss OS is not affiliated with Arch Linux.", a["notes"])

    def test_missing_os_release_and_failing_plasma_do_not_raise(self):
        def boom():
            raise FileNotFoundError("plasmashell")
        mod = m.Model(m.Env(os_release=self.p("none"), kernel=lambda: "k", plasma=boom))
        a = mod.about()
        rows = {r["label"]: r["value"] for r in a["rows"]}
        self.assertEqual((rows["System"], rows["Plasma"]), ("unknown", "unknown"))
        self.assertEqual(a["links"], [])

    def test_non_utf8_os_release_does_not_raise(self):
        with open(self.p("os-release"), "wb") as f:
            f.write(b"\xff\xfe\x00PRETTY_NAME=\xc3\nBUILD_ID=rolling\n")
        rows = {r["label"]: r["value"] for r in m.Model(self.env).about()["rows"]}
        self.assertEqual(rows["Build"], "rolling")

    def test_any_exception_from_plasma_or_kernel_is_contained(self):
        def boom():
            raise RuntimeError("x")
        mod = m.Model(m.Env(os_release=self.p("none"), user_dir=self.p("u"), state_file=self.p("s"),
                            system_answers=self.p("a"), kernel=boom, plasma=boom))
        rows = {r["label"]: r["value"] for r in mod.about()["rows"]}
        self.assertEqual((rows["Kernel"], rows["Plasma"]), ("unknown", "unknown"))
        card = {c["id"]: c for c in mod.overview()["cards"]}["kernel"]
        self.assertEqual(card["value"], "unknown")
        self.assertTrue(card["error"])

    def test_parse_os_release_ignores_comments_and_quotes(self):
        self.assertEqual(m.parse_os_release('# c\nA="b c"\nD=e\n\nbad line\n'), {"A": "b c", "D": "e"})

    def test_default_env_callables_are_not_bound_as_methods(self):
        env = m.Env()
        self.assertTrue(env.kernel())


if __name__ == "__main__":
    unittest.main()
