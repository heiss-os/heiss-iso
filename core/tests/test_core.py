import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fakes import FakeSystem  # noqa: E402
from heiss_core import answers as ans, cli, manifest as mf, resolver, state as st  # noqa: E402
from heiss_core.errors import ValidationError  # noqa: E402

PROFILES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "profiles")
EMPTY_STATE = {"schema_version": 1, "applied": {"profile": None, "addons": []}, "packages": [], "services": [], "flatpaks": []}


def good(**over):
    d = {"schema_version": 1, "id": "x", "kind": "addon", "name": {"en": "X", "ru": "Икс"},
         "description": {"en": "d", "ru": "о"}, "packages": ["foo"]}
    d.update(over)
    return d


class Manifests(unittest.TestCase):
    def test_shipped_manifests_load(self):
        m = mf.load_dir(PROFILES)
        for pid in ("essentials", "base", "cyber", "developer", "custom"):
            self.assertEqual(m[pid].kind, "profile")

    def test_closure_order_and_conflicts(self):
        m = mf.load_dir(PROFILES)
        self.assertEqual(mf.closure(m, ["cyber"]), ["essentials", "base", "cyber"])

    def test_rejects_bad_input(self):
        for bad in (good(packages=["Foo Bar"]), good(packages=["--overwrite=*"]), good(packages=[".hidden"]), good(packages=["a", "a"]), good(unknown=1), good(id="Bad"),
                    good(services=["x.sh"]), good(post_actions=["rm -rf /"]),
                    good(dropins=[{"path": "/usr/lib/x.conf", "content": ""}]),
                    good(dropins=[{"path": "/etc/a.d/../../b.conf", "content": ""}]),
                    good(name={"en": "only"}), good(kind="other"), good(schema_version=2)):
            with self.assertRaises(ValidationError, msg=str(bad)):
                mf.parse(bad)

    def test_cycle_and_unknown_reference(self):
        a = mf.parse(good(id="a", requires=["b"]))
        b = mf.parse(good(id="b", requires=["a"]))
        with self.assertRaises(ValidationError):
            mf.check_graph({"a": a, "b": b})
        with self.assertRaises(ValidationError):
            mf.check_graph({"a": a})

    def test_conflict_detected(self):
        a = mf.parse(good(id="a", conflicts=["b"]))
        b = mf.parse(good(id="b"))
        with self.assertRaises(ValidationError):
            mf.closure({"a": a, "b": b}, ["a", "b"])


class TrailingNewline(unittest.TestCase):
    """`$` alone matches before a trailing newline; ids and file names are matched in full."""
    def test_ids_with_a_trailing_newline_are_refused(self):
        self.assertIsNone(mf.ID_RE.fullmatch("base\n"))
        doc = {"schema_version": 1, "id": "base\n", "kind": "profile", "tier": "important",
               "name": {"en": "x", "ru": "x"}, "description": {"en": "x", "ru": "x"}}
        with self.assertRaises(ValidationError):
            mf.parse(doc, "t.toml")

    def test_list_entries_with_a_trailing_newline_are_refused(self):
        doc = {"schema_version": 1, "id": "base", "kind": "profile", "tier": "important",
               "name": {"en": "x", "ru": "x"}, "description": {"en": "x", "ru": "x"}, "requires": ["essentials\n"]}
        with self.assertRaises(ValidationError):
            mf.parse(doc, "t.toml")


class Answers(unittest.TestCase):
    def test_defaults_and_roundtrip(self):
        doc = ans.validate({"profile": "cyber", "addons": ["addon-kitty"]})
        self.assertEqual(ans.loads(ans.dumps(doc)), doc)
        self.assertEqual(doc["appearance"]["animations"], "full")

    def test_rejects(self):
        for bad in ({"level": "god"}, {"nope": 1}, {"appearance": {"theme": "pink"}}, {"addons": ["a", "a"]},
                    {"software": {"flathub": "yes"}}, {"privacy": {"x": 1}}):
            with self.assertRaises(ValidationError, msg=str(bad)):
                ans.validate(bad)

    def test_unknown_profile(self):
        with self.assertRaises(ValidationError):
            ans.validate({"profile": "zzz"}, known_profiles={"base"})

    def test_migration_chain_and_future_version(self):
        mig = {0: lambda d: dict(d, profile=d.pop("old_profile"))}
        old = {"schema_version": 0, "old_profile": "custom"}
        self.assertEqual(ans.migrate(old, mig)["profile"], "custom")
        with self.assertRaises(ValidationError):
            ans.migrate({"schema_version": 99})
        with self.assertRaises(ValidationError):
            ans.migrate({"schema_version": 0}, {})
        with self.assertRaises(ValidationError):
            ans.migrate({})


class Resolver(unittest.TestCase):
    def setUp(self):
        self.m = mf.load_dir(PROFILES)

    def plan(self, profile, addons=(), state=None, system=None, adopt=False):
        a = ans.validate({"profile": profile, "addons": list(addons)})
        return resolver.resolve(a, self.m, state or dict(EMPTY_STATE), system or FakeSystem(), adopt)

    def test_fresh_install_base(self):
        p = self.plan("base")
        self.assertIn("kate", p.install_packages)
        self.assertIn("NetworkManager.service", p.enable_services)
        self.assertEqual(p.remove_packages, [])
        self.assertEqual(len(p.install_packages), len(set(p.install_packages)))
        self.assertTrue(set(p.install_packages) <= set(p.next_state["packages"]))

    def test_idempotent_when_applied(self):
        p1 = self.plan("base")
        files = {d["path"]: d["content"] for d in p1.dropins}
        sysm = FakeSystem(installed=p1.next_state["packages"], services=p1.next_state["services"], files=files)
        p2 = self.plan("base", state=p1.next_state, system=sysm)
        self.assertTrue(p2.is_empty(), p2.to_text())
        files[p1.dropins[0]["path"]] = "changed by hand\n"
        self.assertEqual(len(self.plan("base", state=p1.next_state, system=sysm).dropins), 1)

    def test_profile_change_removes_only_owned_and_unneeded(self):
        p1 = self.plan("cyber")
        owned = p1.next_state["packages"]
        installed = set(owned) | {"manual-tool"}            # a package the user installed themselves
        sysm = FakeSystem(installed=installed, services=p1.next_state["services"],
                          required_by={"nmap": ["zenmap-user-pkg"]})
        installed.add("zenmap-user-pkg")
        p2 = self.plan("base", state=p1.next_state, system=sysm)
        self.assertNotIn("manual-tool", p2.remove_packages)
        self.assertIn("wireshark-qt", p2.remove_packages)
        self.assertNotIn("nmap", p2.remove_packages)          # still required by another package
        self.assertEqual(p2.kept_packages["nmap"], ["zenmap-user-pkg"])
        self.assertNotIn("kate", p2.remove_packages)

    def test_shared_package_stays_when_still_wanted(self):
        p1 = self.plan("developer", ["addon-kitty"])
        sysm = FakeSystem(installed=p1.next_state["packages"], services=p1.next_state["services"])
        p2 = self.plan("developer", state=p1.next_state, system=sysm)
        self.assertEqual(p2.remove_packages, ["kitty"])

    def test_adopt_only_explicit_and_unowned(self):
        sysm = FakeSystem(installed={"kate", "ark", "libfoo"}, explicit={"kate"})
        p = self.plan("base", system=sysm, adopt=True)
        self.assertEqual(p.adopt_packages, ["kate"])
        self.assertNotIn("kate", p.install_packages)
        self.assertEqual(self.plan("base", system=sysm).adopt_packages, [])

    def test_forget_vanished_packages(self):
        st1 = dict(EMPTY_STATE, packages=["kitty"])
        p = self.plan("base", state=st1)
        self.assertEqual(p.forget_packages, ["kitty"])
        self.assertNotIn("kitty", p.next_state["packages"])

    def test_wrong_kinds(self):
        with self.assertRaises(ValidationError):
            self.plan("addon-kitty")
        with self.assertRaises(ValidationError):
            self.plan("base", ["base"])

    def test_services_disabled_only_if_owned(self):
        stt = dict(EMPTY_STATE, services=["bluetooth.service"])
        p = self.plan("custom", state=stt, system=FakeSystem(services={"bluetooth.service", "sshd.service"}))
        self.assertEqual(p.disable_services, [])            # essentials still wants bluetooth
        p = self.plan("custom", state=dict(EMPTY_STATE, services=["old.service"]), system=FakeSystem(services={"old.service", "sshd.service"}))
        self.assertEqual(p.disable_services, ["old.service"])

    def test_never_partial_upgrade_wording(self):
        # the plan only names packages; it never contains pacman flags
        self.assertNotIn("-Sy", self.plan("base").to_text())


class StateAndCli(unittest.TestCase):
    def test_state_roundtrip_atomic_and_lock(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "state.json")
            self.assertEqual(st.load(path)["packages"], [])
            doc = st.load(path)
            doc["packages"] = ["b", "a", "a"]
            with st.lock(path):
                st.save(path, doc)
                with self.assertRaises(ValidationError):
                    with st.lock(path):
                        pass
            self.assertEqual(st.load(path)["packages"], ["a", "b"])
            self.assertEqual([f for f in os.listdir(os.path.dirname(path)) if f.startswith(".tmp")], [])

    def test_state_rejects_garbage(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                f.write('{"schema_version": 7}')
            with self.assertRaises(ValidationError):
                st.load(path)

    def run_cli(self, *argv, env=None):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            os.environ["HEISS_STATE"] = os.path.join(d, "state.json")
            os.environ["HEISS_ETC"] = d
            rc = cli.main(["--profiles", PROFILES, *argv], system=FakeSystem(), out=out)
        return rc, out.getvalue()

    def test_cli_dry_run_and_refuse_real_apply(self):
        rc, text = self.run_cli("profile", "apply", "--dry-run", "--profile", "cyber")
        self.assertEqual(rc, 0)
        self.assertIn("install packages", text)
        rc, _ = self.run_cli("profile", "apply", "--profile", "cyber")
        self.assertEqual(rc, 1)

    def test_cli_diff_json_and_show(self):
        rc, text = self.run_cli("--json", "profile", "diff", "--profile", "base")
        self.assertEqual(rc, 0)
        self.assertIn('"install_packages"', text)
        rc, text = self.run_cli("profile", "show", "base")
        self.assertIn('"requires"', text)
        self.assertEqual(self.run_cli("profile", "show", "nope")[0], 1)


if __name__ == "__main__":
    unittest.main()
