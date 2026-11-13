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
                         kernel=lambda: "9.9.9-test", plasma=lambda: "6.8.2")

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
        self.assertNotIn("overview", s)
        self.assertNotIn("about", s)

    def test_every_language_has_every_key_of_english(self):
        self.assertEqual(set(S["ru"]), set(S["en"]))

    def test_every_page_has_title_and_keywords_in_both_languages(self):
        for lang in S:
            for p in m.PAGE_IDS:
                self.assertTrue(S[lang]["page." + p] and S[lang]["kw." + p], (lang, p))

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
        self.assertEqual(c["profile"]["value"], "cyber")
        self.assertEqual(c["privacy"]["value"], "Maximum")

    def test_user_answers_used_when_there_is_no_system_file(self):
        self.write("user/answers.toml", 'schema_version = 1\nprofile = "developer"\n')
        self.assertEqual(self.cards()["profile"]["value"], "developer")

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

    def test_parse_os_release_ignores_comments_and_quotes(self):
        self.assertEqual(m.parse_os_release('# c\nA="b c"\nD=e\n\nbad line\n'), {"A": "b c", "D": "e"})

    def test_default_env_callables_are_not_bound_as_methods(self):
        env = m.Env()
        self.assertTrue(env.kernel())


if __name__ == "__main__":
    unittest.main()
