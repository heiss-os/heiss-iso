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
from heiss_control import runner  # noqa: E402
from heiss_control import security as sec  # noqa: E402
from heiss_control import theme as th  # noqa: E402
from heiss_control import tools  # noqa: E402
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
                         apply_theme=lambda theme: (True, ""),
                         run_check=lambda: [{"name": "units", "status": "OK", "detail": "fine", "commands": []}],
                         open_settings=lambda: (True, ""),
                         online=lambda: True, run_pending_item=lambda item, on_step: None,
                         security_facts=lambda: [{"id": "firewall", "status": "ok", "code": "active_enabled", "data": ""},
                                                 {"id": "listening", "status": "warn", "code": "some", "data": "22, 631"},
                                                 {"id": "secure_boot", "status": "info", "code": "bios", "data": ""}])

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
        mod.open("hardware")
        s = mod.screen()
        self.assertFalse(s["built"])
        for key in ("overview", "profiles", "appearance", "security", "advanced", "about"):
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
        self.assertEqual(self.page()["pending"], [{"id": 1, "text": "Apply profile Cyber", "status": "waiting", "error": ""}])

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


class FakeSystem:
    """Stands in for security.RealSystem: answers by argv, records every call."""
    def __init__(self, answers=None, files=None, paths=()):
        self.answers, self.files, self.paths, self.calls = answers or {}, files or {}, set(paths), []

    def run(self, argv):
        self.calls.append(list(argv))
        return self.answers.get(tuple(argv), (127, ""))

    def read_bytes(self, path):
        return self.files.get(path)

    def exists(self, path):
        return path in self.paths


class SecurityFacts(unittest.TestCase):
    def one(self, fn, sh):
        return fn(sh)

    def test_firewall_states(self):
        act = ("systemctl", "is-active", "firewalld")
        ena = ("systemctl", "is-enabled", "firewalld")
        self.assertEqual(sec.firewall(FakeSystem({act: (0, "active\n"), ena: (0, "enabled\n")}))["code"], "active_enabled")
        self.assertEqual(sec.firewall(FakeSystem({act: (0, "active\n"), ena: (1, "disabled\n")}))["code"], "active_not_enabled")
        self.assertEqual(sec.firewall(FakeSystem({act: (3, "inactive\n")}))["code"], "inactive")
        self.assertEqual(sec.firewall(FakeSystem())["code"], "unknown")   # systemctl missing (exit 127)

    def test_ssh(self):
        key = ("systemctl", "is-active", "sshd")
        self.assertEqual(sec.ssh(FakeSystem({key: (0, "active\n")}))["status"], "warn")
        self.assertEqual(sec.ssh(FakeSystem({key: (3, "inactive\n")}))["status"], "ok")
        self.assertEqual(sec.ssh(FakeSystem())["status"], "info")

    def test_disk_encryption_follows_the_ancestors_of_the_root_device(self):
        fm = ("findmnt", "-n", "-o", "SOURCE", "/")
        ls = lambda dev: ("lsblk", "-s", "-r", "-n", "-o", "TYPE", "--", dev)
        self.assertEqual(sec.disk_encryption(FakeSystem({fm: (0, "/dev/mapper/root\n"), ls("/dev/mapper/root"): (0, "crypt\npart\ndisk\n")}))["code"], "encrypted")
        self.assertEqual(sec.disk_encryption(FakeSystem({fm: (0, "/dev/sda2\n"), ls("/dev/sda2"): (0, "part\ndisk\n")}))["code"], "plain")
        # btrfs subvolume suffix is removed before the device name is used
        sh = FakeSystem({fm: (0, "/dev/sda2[/@]\n"), ls("/dev/sda2"): (0, "part\ndisk\n")})
        self.assertEqual(sec.disk_encryption(sh)["code"], "plain")
        self.assertIn(list(ls("/dev/sda2")), sh.calls)

    def test_disk_encryption_does_not_trust_odd_sources(self):
        fm = ("findmnt", "-n", "-o", "SOURCE", "/")
        for out in ("overlay\n", "-rf /\n", "", "tmpfs\n"):
            sh = FakeSystem({fm: (0, out)})
            self.assertEqual(sec.disk_encryption(sh)["code"], "unknown", out)
            self.assertEqual(sh.calls, [list(fm)])   # nothing else was run with that text
        self.assertEqual(sec.disk_encryption(FakeSystem())["code"], "unknown")

    def test_secure_boot(self):
        self.assertEqual(sec.secure_boot(FakeSystem())["code"], "bios")
        on = bytes([6, 0, 0, 0, 1])
        off = bytes([6, 0, 0, 0, 0])
        self.assertEqual(sec.secure_boot(FakeSystem(files={sec.SECURE_BOOT_VAR: on}, paths=["/sys/firmware/efi"]))["code"], "enabled")
        self.assertEqual(sec.secure_boot(FakeSystem(files={sec.SECURE_BOOT_VAR: off}, paths=["/sys/firmware/efi"]))["code"], "disabled")
        self.assertEqual(sec.secure_boot(FakeSystem(paths=["/sys/firmware/efi"]))["code"], "unknown")
        self.assertEqual(sec.secure_boot(FakeSystem(files={sec.SECURE_BOOT_VAR: b"\x06"}, paths=["/sys/firmware/efi"]))["code"], "unknown")

    def test_listening_ignores_loopback_and_lists_the_rest(self):
        key = ("ss", "-H", "-l", "-t", "-n")
        out = ("LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 128 [::]:22 [::]:*\nLISTEN 0 4096 127.0.0.1:631 0.0.0.0:*\n"
               "LISTEN 0 4096 [::1]:631 [::]:*\nLISTEN 0 4096 [::ffff:127.0.0.1]:9 [::]:*\nLISTEN 0 5 *:8080 *:*\nLISTEN 0 1 127.0.0.53%lo:53 0.0.0.0:*\ngarbage\n")
        r = sec.listening(FakeSystem({key: (0, out)}))
        self.assertEqual((r["code"], r["data"]), ("some", "22, 8080"))
        self.assertEqual(sec.listening(FakeSystem({key: (0, "LISTEN 0 1 127.0.0.1:631 0.0.0.0:*\n")}))["code"], "none")
        self.assertEqual(sec.listening(FakeSystem())["code"], "unknown")

    def test_many_ports_are_cut(self):
        key = ("ss", "-H", "-l", "-t", "-n")
        out = "".join("LISTEN 0 1 0.0.0.0:%d 0.0.0.0:*\n" % p for p in range(1000, 1100))
        data = sec.listening(FakeSystem({key: (0, out)}))["data"]
        self.assertTrue(data.endswith(" ..."))
        self.assertEqual(len(data.replace(" ...", "").split(", ")), sec.MAX_PORTS)

    def test_one_broken_fact_does_not_hide_the_others(self):
        class Bad(FakeSystem):
            def run(self, argv):
                if argv[0] == "ss":
                    raise RuntimeError("boom")
                return super().run(argv)
        facts = sec.collect(Bad())
        self.assertEqual([f["id"] for f in facts], ["firewall", "disk", "secure_boot", "ssh", "listening"])
        self.assertEqual(facts[-1], {"id": "listening", "status": "info", "code": "unknown", "data": ""})

    def test_every_command_is_a_literal_list_with_a_fixed_environment(self):
        sh = FakeSystem()
        sec.collect(sh)
        self.assertTrue(sh.calls)
        for argv in sh.calls:
            self.assertIn(argv[0], ("systemctl", "findmnt", "lsblk", "ss"))
        self.assertEqual(sec.ENV["PATH"], "/usr/bin:/bin")

    def test_real_system_never_raises_for_a_missing_tool(self):
        self.assertEqual(sec.RealSystem().run(["/nonexistent/tool"]), (127, ""))
        self.assertIsNone(sec.RealSystem().read_bytes("/nonexistent/file"))


class SecurityPage(Fixture):
    def mod(self, lang="en"):
        mod = m.Model(self.env, lang)
        mod.open("security")
        return mod

    def test_page_is_built_and_starts_idle(self):
        s = self.mod().screen()
        self.assertTrue(s["built"])
        self.assertEqual((s["security"]["state"], s["security"]["items"], s["security"]["summary"]), ("idle", [], ""))

    def test_facts_become_plain_language_with_advice_only_for_warnings(self):
        mod = self.mod()
        self.assertTrue(mod.begin_security())
        self.assertFalse(mod.begin_security())
        mod.finish_security()
        p = mod.screen()["security"]
        by = {i["id"]: i for i in p["items"]}
        self.assertEqual(by["firewall"]["detail"], "The firewall is on and starts at every boot.")
        self.assertEqual(by["firewall"]["advice"], "")
        self.assertIn("22, 631", by["listening"]["detail"])
        self.assertTrue(by["listening"]["advice"])
        self.assertEqual(by["secure_boot"]["statusLabel"], "For your information")
        self.assertEqual(p["summary"], "1 of 3 checks look fine, 1 need a look, the rest are for information.")
        self.assertNotIn("score", p["summary"].lower())

    def test_russian(self):
        mod = self.mod("ru")
        mod.begin_security()
        mod.finish_security()
        by = {i["id"]: i for i in mod.screen()["security"]["items"]}
        self.assertEqual(by["firewall"]["title"], "Брандмауэр")
        self.assertIn("22, 631", by["listening"]["detail"])

    def test_unknown_ids_codes_and_statuses_are_shown_safely(self):
        self.env.security_facts = lambda: [{"id": "zzz", "status": "<b>PANIC</b>", "code": "x%sy", "data": "d" * 5000},
                                           {"id": "firewall", "status": "ok", "code": "no_such_code", "data": ""}]
        mod = self.mod()
        mod.begin_security()
        mod.finish_security()
        items = mod.screen()["security"]["items"]
        self.assertEqual(items[0]["status"], "info")
        self.assertEqual(items[0]["detail"], "Could not be judged.")
        self.assertEqual(items[1]["detail"], "Could not be judged.")

    def test_percent_signs_in_data_never_break_the_text(self):
        self.env.security_facts = lambda: [{"id": "listening", "status": "warn", "code": "some", "data": "%s %d %(x)s"}]
        mod = self.mod()
        mod.begin_security()
        mod.finish_security()
        self.assertIn("%s %d %(x)s", mod.screen()["security"]["items"][0]["detail"])

    def test_a_failing_source_is_reported_and_frees_the_button(self):
        def boom():
            raise RuntimeError("no luck")
        self.env.security_facts = boom
        mod = self.mod()
        mod.begin_security()
        mod.finish_security()
        p = mod.screen()["security"]
        self.assertEqual((p["state"], p["items"]), ("failed", []))
        self.assertIn("no luck", p["message"])
        self.assertTrue(mod.begin_security())

    def test_malformed_results_are_a_failure_not_a_crash(self):
        for bad in (None, 5, [None], [{"id": 1}], [{"status": "ok"}]):
            self.env.security_facts = lambda bad=bad: bad
            mod = self.mod()
            mod.begin_security()
            mod.finish_security()
            self.assertEqual(mod.sec_state, "failed", bad)

    def test_every_code_the_checks_can_return_has_text_in_both_languages(self):
        import re
        with open(os.path.join(os.path.dirname(HERE), "heiss_control", "security.py"), encoding="utf-8") as f:
            src = f.read()
        pairs = set(re.findall(r'_item\("(\w+)", "(\w+)", "(\w+)"', src))
        self.assertGreater(len(pairs), 12)
        from heiss_control.strings import S
        for lang in S:
            for item_id, status, code in pairs:
                self.assertIn("sec.%s.%s" % (item_id, code), S[lang], (lang, item_id, code))
                self.assertIn("sec.status." + status, S[lang])
            for item_id in {p[0] for p in pairs if p[1] == "warn"}:
                self.assertIn("sec.%s.advice" % item_id, S[lang], (lang, item_id))


class PendingActions(Fixture):
    def queue(self):
        from heiss_core import wizard as wz
        return wz.PendingQueue(self.p("user/pending.json"))

    def add(self, profile="cyber", addons=()):
        return self.queue().add("apply-profile", {"profile": profile, "addons": list(addons)}, now=1)["id"]

    def mod(self):
        mod = m.Model(self.env)
        mod.open("profiles")
        return mod

    def test_nothing_waiting_means_nothing_starts(self):
        mod = self.mod()
        self.assertFalse(mod.begin_pending())
        self.assertEqual(mod.pend_state, "idle")

    def test_offline_starts_nothing_and_says_so(self):
        self.add()
        self.env.online = lambda: False
        called = []
        self.env.run_pending_item = lambda item, on_step: called.append(item)
        mod = self.mod()
        self.assertFalse(mod.begin_pending())
        self.assertEqual(mod.screen()["profiles"]["run"]["state"], "offline")
        self.assertEqual(called, [])
        self.assertEqual(len(self.queue().list()), 1)

    def test_run_applies_in_order_removes_the_done_items_and_reports_steps(self):
        a, b = self.add("base"), self.add("cyber", ["wireshark"])
        seen, steps = [], []

        def run_item(item, on_step):
            seen.append((item["id"], item["payload"]))
            on_step(1, 2, "install packages")
        self.env.run_pending_item = run_item
        mod = self.mod()
        self.assertTrue(mod.begin_pending())
        self.assertFalse(mod.begin_pending())   # one run at a time
        mod.finish_pending(lambda: steps.append(mod.pend_step))
        self.assertEqual([i for i, _ in seen], [a, b])
        self.assertEqual(steps, ["1/2 install packages"] * 2)
        self.assertEqual((mod.pend_state, mod.pend_step), ("ok", ""))
        self.assertEqual(self.queue().list(), [])

    def test_a_failure_stops_the_run_and_keeps_the_item_with_its_message(self):
        from heiss_core.errors import HeissError
        self.add("base")
        self.add("cyber")

        def run_item(item, on_step):
            raise HeissError("pacman is locked " + "x" * 1000)
        self.env.run_pending_item = run_item
        mod = self.mod()
        mod.begin_pending()
        mod.finish_pending()
        self.assertEqual(mod.pend_state, "failed")
        self.assertLessEqual(len(mod.pend_message), m.MAX_MESSAGE)
        items = self.queue().list()
        self.assertEqual([i["status"] for i in items], ["failed", "pending"])
        self.assertTrue(mod.begin_pending())   # retry is possible

    def test_unexpected_exceptions_do_not_leave_the_button_stuck(self):
        self.add()

        def run_item(item, on_step):
            raise RuntimeError("boom")
        self.env.run_pending_item = run_item
        mod = self.mod()
        mod.begin_pending()
        mod.finish_pending()
        self.assertEqual(mod.pend_state, "failed")
        self.assertTrue(mod.begin_pending())

    def test_broken_queue_file_is_an_error_not_a_crash(self):
        self.write("user/pending.json", "{")
        mod = self.mod()
        self.assertFalse(mod.begin_pending())
        self.assertEqual(mod.pend_state, "failed")
        self.assertTrue(mod.pend_message)

    def test_remove_drops_one_item_and_refuses_bad_ids_and_a_running_run(self):
        a, b = self.add("base"), self.add("cyber")
        mod = self.mod()
        for bad in ("1", None, True, 1.0, [1]):
            self.assertFalse(mod.remove_pending(bad))
        self.assertEqual(len(self.queue().list()), 2)
        self.assertTrue(mod.remove_pending(a))
        self.assertEqual([i["id"] for i in self.queue().list()], [b])
        mod.begin_pending()
        self.assertFalse(mod.remove_pending(b))
        self.assertEqual(len(self.queue().list()), 1)

    def test_removing_the_failed_item_clears_its_error(self):
        from heiss_core.errors import HeissError
        a = self.add("base")

        def run_item(item, on_step):
            raise HeissError("pacman is locked")
        self.env.run_pending_item = run_item
        mod = self.mod()
        mod.begin_pending()
        mod.finish_pending()
        self.assertEqual(mod.pend_state, "failed")
        self.assertTrue(mod.remove_pending(a))
        run = mod.screen()["profiles"]["run"]
        self.assertEqual((run["state"], run["message"]), ("idle", ""))

    def test_screen_offers_the_labels_and_the_warning_in_both_languages(self):
        for lang, word in (("en", "password"), ("ru", "пароль")):
            mod = m.Model(self.env, lang)
            mod.open("profiles")
            run = mod.screen()["profiles"]["run"]
            self.assertIn(word, run["warning"])
            self.assertTrue(run["label"] and run["removeLabel"])


class Runner(unittest.TestCase):
    def item(self, profile="cyber", addons=("wireshark",), kind="apply-profile"):
        return {"id": 1, "kind": kind, "payload": {"profile": profile, "addons": list(addons)}, "status": "pending"}

    def test_argv_uses_the_equals_form_and_no_shell(self):
        self.assertEqual(runner.argv_for(self.item(), ["heiss"]),
                         ["heiss", "profile", "apply", "--yes", "--adopt", "--profile=cyber", "--addon=wireshark"])

    def test_bad_ids_and_kinds_are_refused_before_anything_runs(self):
        for bad in (self.item("--yes"), self.item("base\n"), self.item("Base"), self.item("a b"), self.item("base", ["x;y"]),
                    self.item("base", [""]), self.item(kind="rm"), {"kind": "apply-profile"}, {}, self.item("x" * 50)):
            from heiss_core.errors import HeissError
            with self.assertRaises(HeissError):
                runner.argv_for(bad, ["heiss"])

    def test_the_child_is_isolated_and_gets_a_clean_environment(self):
        seen = {}

        class P:
            stdout = iter(())
            returncode = 0

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def popen(argv, **kw):
            seen["argv"], seen["kw"] = argv, kw
            return P()
        env = {"PATH": "/usr/bin", "HOME": "/home/u", "XDG_RUNTIME_DIR": "/run/user/1000", "PYTHONPATH": "/tmp/evil",
               "PYTHONSTARTUP": "/tmp/x.py", "LD_PRELOAD": "/tmp/e.so", "LD_LIBRARY_PATH": "/tmp",
               "GCONV_PATH": "/tmp", "GIO_EXTRA_MODULES": "/tmp", "HEISS_PROFILES": "/tmp/m", "LOCPATH": "/tmp"}
        runner.run_item(self.item(), None, None, popen, env)
        self.assertEqual(seen["argv"][1:4], ["-I", "-m", "heiss_core"])
        self.assertEqual(seen["kw"]["cwd"], "/")
        self.assertEqual(seen["kw"]["env"], {"PATH": "/usr/bin", "HOME": "/home/u", "XDG_RUNTIME_DIR": "/run/user/1000"})
        self.assertNotIn("shell", seen["kw"])

    def fake(self, script):
        import stat
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d)
        path = os.path.join(d, "fakeheiss")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n" + script)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return [path]

    def test_steps_are_reported_and_success_returns(self):
        steps = []
        base = self.fake('echo "[1/2] install packages"; echo noise; echo "[2/2] enable services"; exit 0')
        runner.run_item(self.item(), lambda n, t, d: steps.append((n, t, d)), base)
        self.assertEqual(steps, [(1, 2, "install packages"), (2, 2, "enable services")])

    def test_the_child_gets_exactly_the_expected_arguments(self):
        import tempfile
        log = os.path.join(tempfile.mkdtemp(), "args")
        self.addCleanup(__import__("shutil").rmtree, os.path.dirname(log))
        base = self.fake('printf "%%s\\n" "$@" > %s' % log)
        runner.run_item(self.item(), None, base)
        with open(log) as f:
            self.assertEqual(f.read().split(), ["profile", "apply", "--yes", "--adopt", "--profile=cyber", "--addon=wireshark"])

    def test_failure_reports_the_heiss_line_or_the_last_line(self):
        from heiss_core.errors import HeissError
        with self.assertRaises(HeissError) as e:
            runner.run_item(self.item(), None, self.fake('echo "heiss: pacman is locked"; echo trailing; exit 1'))
        self.assertEqual(str(e.exception), "pacman is locked")
        with self.assertRaises(HeissError) as e:
            runner.run_item(self.item(), None, self.fake('echo only line; exit 2'))
        self.assertEqual(str(e.exception), "only line")
        with self.assertRaises(HeissError) as e:
            runner.run_item(self.item(), None, self.fake('exit 3'))
        self.assertIn("without a message", str(e.exception))

    def test_a_broken_step_callback_does_not_stop_the_command(self):
        def bad(n, t, d):
            raise RuntimeError("x")
        runner.run_item(self.item(), bad, self.fake('echo "[1/1] a"; echo "[1/1] b"; exit 0'))

    def test_missing_command_and_non_utf8_output(self):
        from heiss_core.errors import HeissError
        with self.assertRaises(HeissError):
            runner.run_item(self.item(), None, ["/nonexistent/heiss"])
        runner.run_item(self.item(), None, self.fake("printf '\\377\\376\\n'; exit 0"))


class Advanced(Fixture):
    def mod(self):
        mod = m.Model(self.env)
        mod.open("advanced")
        return mod

    def test_page_is_built_and_starts_idle(self):
        s = self.mod().screen()
        self.assertTrue(s["built"])
        self.assertEqual((s["advanced"]["state"], s["advanced"]["items"]), ("idle", []))

    def test_check_runs_once_at_a_time_and_lists_the_items(self):
        mod = self.mod()
        self.assertTrue(mod.begin_check())
        self.assertFalse(mod.begin_check())
        mod.finish_check()
        a = mod.screen()["advanced"]
        self.assertEqual(a["state"], "done")
        self.assertEqual(a["items"], [{"name": "units", "status": "OK", "detail": "fine"}])
        self.assertTrue(mod.begin_check())   # free again

    def test_unknown_status_becomes_warn_and_text_is_cut(self):
        self.env.run_check = lambda: [{"name": "n" * 1000, "status": "<b>HACK</b>", "detail": "d\n" * 1000}]
        mod = self.mod()
        mod.begin_check()
        mod.finish_check()
        item = mod.screen()["advanced"]["items"][0]
        self.assertEqual(item["status"], "WARN")
        self.assertLessEqual(len(item["name"]), m.MAX_MESSAGE)
        self.assertLessEqual(len(item["detail"]), m.MAX_MESSAGE)
        self.assertNotIn("\n", item["detail"])

    def test_a_failing_check_is_reported_not_raised(self):
        def boom():
            raise RuntimeError("no luck")
        self.env.run_check = boom
        mod = self.mod()
        mod.begin_check()
        mod.finish_check()
        a = mod.screen()["advanced"]
        self.assertEqual((a["state"], a["items"]), ("failed", []))
        self.assertIn("no luck", a["message"])
        self.assertTrue(mod.begin_check())

    def test_malformed_check_result_is_a_failure_not_a_crash(self):
        for bad in (None, 5, [{"name": "x"}], {"name": 1, "status": "OK", "detail": 2}):
            self.env.run_check = lambda bad=bad: bad
            mod = self.mod()
            mod.begin_check()
            mod.finish_check()
            self.assertEqual((mod.check_state, mod.check_items), ("failed", []), bad)
            self.assertTrue(mod.check_message)

    def test_open_settings_reports_a_failure_and_clears_it(self):
        mod = self.mod()
        self.env.open_settings = lambda: (False, "nope")
        mod.open_stock_settings()
        self.assertEqual(mod.screen()["advanced"]["settingsMessage"], "nope")
        self.env.open_settings = lambda: (True, "")
        mod.open_stock_settings()
        self.assertEqual(mod.screen()["advanced"]["settingsMessage"], "")
        def boom():
            raise RuntimeError("x")
        self.env.open_settings = boom
        mod.open_stock_settings()
        self.assertEqual(mod.settings_message, "x")


class Tools(unittest.TestCase):
    def test_open_settings_uses_a_fixed_argument_list_and_detaches(self):
        seen = {}

        def popen(argv, **kw):
            seen["argv"], seen["kw"] = argv, kw
        self.assertEqual(tools.open_settings(popen), (True, ""))
        self.assertEqual(seen["argv"], ["systemsettings"])
        self.assertTrue(seen["kw"]["start_new_session"])
        self.assertNotIn("shell", seen["kw"])

    def test_open_settings_failure_is_returned(self):
        def popen(argv, **kw):
            raise FileNotFoundError("systemsettings")
        ok, msg = tools.open_settings(popen)
        self.assertFalse(ok)
        self.assertIn("cannot start System Settings", msg)

    def test_run_check_returns_plain_dicts(self):
        from heiss_core import check as ck
        orig = (ck.run_checks, ck.CheckEnv)
        ck.run_checks = lambda env, theme_env, profiles_dir: [ck.Item("x", ck.OK, "d", [["a", "b"]])]
        try:
            self.assertEqual(tools.run_check(), [{"name": "x", "status": "OK", "detail": "d", "commands": ["a b"]}])
        finally:
            ck.run_checks, ck.CheckEnv = orig


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

    def test_tool_output_is_decoded_leniently_and_bounded(self):
        self.assertEqual(th.apply_theme("dark", self.Run(rc=1, err="x" * 100000))[1], "x" * th.MAX_OUTPUT)
        self.assertEqual(len(th.kreadconfig("a", "b", "c", self.Run(out="y" * 100000))), th.MAX_OUTPUT)
        ok, msg = th.apply_theme("dark", self.Run(raises=UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")))
        self.assertFalse(ok)

    def test_subprocess_is_asked_to_replace_bad_bytes(self):
        seen = {}

        def run(argv, **kw):
            import subprocess
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 0, "", "")
        th.apply_theme("dark", run)
        self.assertEqual(seen["errors"], "replace")

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
