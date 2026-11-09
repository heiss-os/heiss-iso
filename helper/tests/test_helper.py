import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(REPO, "core"), os.path.join(REPO, "helper")]
from heiss_core import manifest as mf, state as st  # noqa: E402
from heiss_helper import actions, policy  # noqa: E402
from heiss_helper.actions import ACTIONS, Context  # noqa: E402
from heiss_helper.audit import Audit  # noqa: E402
from heiss_helper.dispatch import Dispatcher  # noqa: E402
from heiss_helper.errors import HelperError  # noqa: E402

DATA = os.path.join(REPO, "helper", "data")


class FakeRunner:
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def run(self, argv, emit, timeout=0):
        self.calls.append(argv)
        emit("ran " + argv[0])
        return 1 if self.fail_on and argv[0] == self.fail_on else 0


class FakeAuth:
    def __init__(self, allow=True):
        self.allow, self.asked = allow, []

    def is_authorized(self, sender, action_id):
        self.asked.append((sender, action_id))
        return self.allow


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "root")
        os.makedirs(os.path.join(self.root, "etc"))
        os.makedirs(os.path.join(self.root, "var/lib"))
        self.state = os.path.join(self.tmp, "state.json")
        self.runner = FakeRunner()
        self.ctx = Context(os.path.join(REPO, "profiles"), os.path.join(REPO, "hardware"), self.state, self.root,
                           strict=False, runner=self.runner)
        self.ctx.free_bytes = lambda: 10 << 30
        self.ctx.snapshots_available = lambda: False
        self.installed, self.explicit, self.enabled = set(), set(), set()
        self.ctx.installed_packages = lambda: set(self.installed)
        self.ctx.explicit_packages = lambda: set(self.explicit)
        self.ctx.enabled_services = lambda: set(self.enabled)

    def own(self, *pkgs):
        doc = st.load(self.state)
        doc["packages"] = list(pkgs)
        st.save(self.state, doc)


class Validation(Env):
    def test_install_accepts_manifest_packages_only(self):
        steps = actions.build_install(self.ctx, ["nmap", "kate"])
        argv = [s.argv for s in steps if s.argv][0]
        self.assertEqual(argv, ["pacman", "-S", "--needed", "--noconfirm", "--", "nmap", "kate"])
        for bad in (["evil-pkg"], ["nmap; rm -rf /"], ["--overwrite=*"], ["-Syu"], [], ["nmap", "nmap"], "nmap", [1],
                    ["$(id)"], ["nmap\n"], ["a" * 200]):
            with self.assertRaises(HelperError, msg=str(bad)) as cm:
                actions.build_install(self.ctx, bad)
            self.assertEqual(cm.exception.code, "Invalid")

    def test_install_limit(self):
        with self.assertRaises(HelperError):
            actions.build_install(self.ctx, ["kate"] * 600)

    def test_remove_only_owned_and_never_essentials(self):
        self.own("nmap", "linux")
        argv = [s.argv for s in actions.build_remove(self.ctx, ["nmap"]) if s.argv][0]
        self.assertEqual(argv, ["pacman", "-R", "--noconfirm", "--", "nmap"])   # no -s, no -c
        with self.assertRaises(HelperError):
            actions.build_remove(self.ctx, ["tcpdump"])      # allowed name, not installed by Heiss
        with self.assertRaises(HelperError):
            actions.build_remove(self.ctx, ["linux"])         # essential: owned but protected

    def test_services(self):
        steps = actions.build_services(self.ctx, ["bluetooth.service"], ["power-profiles-daemon.service"])
        argvs = [s.argv for s in steps if s.argv]
        self.assertEqual(argvs, [["systemctl", "enable", "--", "bluetooth.service"],
                                 ["systemctl", "disable", "--", "power-profiles-daemon.service"]])
        self.assertNotIn("--now", " ".join(sum(argvs, [])))
        for en, dis in ((["sshd.service"], []), (["a.service"], ["a.service"]), ([], []), (["x.sh"], []),
                        (["bluetooth.service"], ["bluetooth.service"])):
            with self.assertRaises(HelperError, msg=str((en, dis))):
                actions.build_services(self.ctx, en, dis)

    def test_dropin_content_comes_from_manifest_not_client(self):
        path = "/etc/systemd/zram-generator.conf.d/heiss.conf"
        steps = actions.build_dropin(self.ctx, path)
        actions.execute(steps, self.ctx, lambda l: None)
        with open(os.path.join(self.root, path.lstrip("/"))) as f:
            self.assertEqual(f.read(), "[zram0]\nzram-size = min(ram / 2, 4096)\n")
        for bad in ("/etc/passwd", "/etc/sudoers.d/x", "../../etc/shadow", "", None, 5):
            with self.assertRaises(HelperError, msg=str(bad)):
                actions.build_dropin(self.ctx, bad)

    def test_write_dropin_refuses_symlinks_and_outside_etc(self):
        os.makedirs(os.path.join(self.root, "etc/x.d"))
        os.symlink("/tmp", os.path.join(self.root, "etc/evil.d"))
        with self.assertRaises(HelperError):
            policy.write_dropin("/etc/evil.d/a.conf", "x", self.root)
        os.symlink("/etc/passwd", os.path.join(self.root, "etc/x.d/link.conf"))
        with self.assertRaises(HelperError):
            policy.write_dropin("/etc/x.d/link.conf", "x", self.root)
        for bad in ("/usr/lib/a.conf", "/etc/../usr/a.conf", "/etc//a.conf", "etc/a.conf"):
            with self.assertRaises(HelperError, msg=bad):
                policy.write_dropin(bad, "x", self.root)

    def test_write_dropin_atomic_leaves_no_temp_files(self):
        policy.write_dropin("/etc/a.d/b.conf", "hello", self.root)
        files = os.listdir(os.path.join(self.root, "etc/a.d"))
        self.assertEqual(files, ["b.conf"])
        self.assertEqual(oct(os.stat(os.path.join(self.root, "etc/a.d/b.conf")).st_mode & 0o777), "0o644")

    def test_post_actions_fixed_argv(self):
        self.assertEqual(actions.build_post_action(self.ctx, "mkinitcpio")[0].argv, ["mkinitcpio", "-P"])
        for bad in ("sh -c id", "", "mkinitcpio -P", None):
            with self.assertRaises(HelperError):
                actions.build_post_action(self.ctx, bad)
        self.assertEqual(set(policy.POST_ACTION_ARGV), mf.POST_ACTIONS)

    def test_snapshot_description(self):
        self.assertTrue(actions.build_snapshot(self.ctx, "Before update"))
        for bad in ("", "x" * 81, "a;b", "a\nb", "$(id)", None):
            with self.assertRaises(HelperError, msg=str(bad)):
                actions.build_snapshot(self.ctx, bad)

    def test_update_is_always_full_upgrade(self):
        argv = [s.argv for s in actions.build_update(self.ctx) if s.argv][0]
        self.assertEqual(argv, ["pacman", "-Syu", "--noconfirm"])
        for steps in (actions.build_install(self.ctx, ["kate"]),):
            for s in steps:
                self.assertNotIn("-Sy", s.argv or [])

    def test_untrusted_directory_rejected_when_strict(self):
        d = os.path.join(self.tmp, "writable")
        os.makedirs(d)
        os.chmod(d, 0o777)
        with self.assertRaises(HelperError):
            policy.load_trusted(d, d, strict=True)


class Ownership(Env):
    def go(self, steps):
        ok, msg = actions.execute(steps, self.ctx, lambda l: None)
        return ok

    def owned(self):
        return set(st.load(self.state)["packages"])

    def test_install_records_only_newly_installed_packages(self):
        self.installed = {"kate"}                       # the user already had kate: not Heiss-owned
        steps = actions.build_install(self.ctx, ["kate", "ark"])
        self.assertTrue(self.go(steps))
        self.assertEqual(self.owned(), {"ark"})

    def test_failed_install_records_nothing(self):
        self.runner.fail_on = "pacman"
        self.assertFalse(self.go(actions.build_install(self.ctx, ["ark"])))
        self.assertEqual(self.owned(), set())

    def test_remove_forgets_ownership(self):
        self.own("ark", "kate")
        self.assertTrue(self.go(actions.build_remove(self.ctx, ["ark"])))
        self.assertEqual(self.owned(), {"kate"})

    def test_failed_remove_keeps_ownership(self):
        self.own("ark")
        self.runner.fail_on = "pacman"
        self.assertFalse(self.go(actions.build_remove(self.ctx, ["ark"])))
        self.assertEqual(self.owned(), {"ark"})

    def test_adopt_only_installed_explicit_unowned(self):
        self.installed, self.explicit = {"kate", "ark", "okular"}, {"kate", "ark"}
        self.own("ark")
        self.assertTrue(self.go(actions.build_adopt(self.ctx, ["kate", "ark", "okular", "gwenview"])))
        self.assertEqual(self.owned(), {"kate", "ark"})          # okular not explicit, gwenview not installed, ark already owned

    def test_adopt_rejects_unlisted_packages(self):
        with self.assertRaises(HelperError):
            actions.build_adopt(self.ctx, ["bash"])

    def test_services_ownership(self):
        self.enabled = {"bluetooth.service"}            # already enabled by someone else
        steps = actions.build_services(self.ctx, ["bluetooth.service", "fstrim.timer"], [])
        self.assertTrue(self.go(steps))
        self.assertEqual(set(st.load(self.state)["services"]), {"fstrim.timer"})
        self.assertTrue(self.go(actions.build_services(self.ctx, [], ["fstrim.timer"])))
        self.assertEqual(st.load(self.state)["services"], [])


class Execution(Env):
    def run_steps(self, steps):
        lines = []
        ok, msg = actions.execute(steps, self.ctx, lines.append)
        return ok, msg, lines

    def test_lock_blocks(self):
        os.makedirs(os.path.join(self.root, "var/lib/pacman"))
        open(os.path.join(self.root, "var/lib/pacman/db.lck"), "w").close()
        ok, msg, _ = self.run_steps(actions.build_install(self.ctx, ["kate"]))
        self.assertFalse(ok)
        self.assertIn("db.lck", msg)
        self.assertEqual(self.runner.calls, [])

    def test_low_space_blocks(self):
        self.ctx.free_bytes = lambda: 1 << 20
        ok, msg, _ = self.run_steps(actions.build_install(self.ctx, ["kate"]))
        self.assertFalse(ok)
        self.assertEqual(self.runner.calls, [])

    def test_snapshot_taken_when_available_and_failure_is_not_fatal(self):
        self.ctx.snapshots_available = lambda: True
        self.runner.fail_on = "snapper"
        ok, _, lines = self.run_steps(actions.build_install(self.ctx, ["kate"]))
        self.assertTrue(ok)
        self.assertEqual([c[0] for c in self.runner.calls], ["snapper", "pacman"])
        self.assertTrue(any("warning" in l for l in lines))

    def test_explicit_snapshot_failure_is_fatal(self):
        self.ctx.snapshots_available = lambda: True
        self.runner.fail_on = "snapper"
        ok, _, _ = self.run_steps(actions.build_snapshot(self.ctx, "manual"))
        self.assertFalse(ok)

    def test_failed_command_stops_sequence(self):
        self.runner.fail_on = "systemctl"
        steps = actions.build_services(self.ctx, ["bluetooth.service"], ["power-profiles-daemon.service"])
        ok, msg, _ = self.run_steps(steps)
        self.assertFalse(ok)
        self.assertEqual(len(self.runner.calls), 1)


class DispatcherTests(Env):
    def make(self, allow=True):
        self.events = []
        self.auth = FakeAuth(allow)
        audit = Audit(os.path.join(self.tmp, "audit.log"))
        self.d = Dispatcher(self.auth, lambda sender, sig, args: self.events.append((sender, sig, args)), self.ctx, audit)
        return self.d

    def test_unauthorized_runs_nothing_and_leaks_nothing(self):
        d = self.make(allow=False)
        with self.assertRaises(HelperError) as cm:
            d.handle(":1.5", 1000, "InstallPackages", (["evil"],))
        self.assertEqual(cm.exception.code, "NotAuthorized")     # not "Invalid": no allowlist oracle
        self.assertEqual(self.runner.calls, [])
        self.assertEqual(self.auth.asked, [(":1.5", "org.heiss.packages.install")])

    def test_authorized_job_streams_to_caller_only(self):
        d = self.make()
        job = d.handle(":1.5", 1000, "InstallPackages", (["kate"],))
        d.join()
        self.assertEqual(re.fullmatch(r"[0-9a-f]{16}", job) is not None, True)
        self.assertTrue(all(e[0] == ":1.5" for e in self.events))
        self.assertEqual(self.events[-1][1:], ("JobFinished", (job, True, "done")))
        self.assertTrue(any(e[1] == "JobOutput" for e in self.events))
        self.assertEqual(self.runner.calls[-1][:3], ["pacman", "-S", "--needed"])

    def test_invalid_after_authorization(self):
        d = self.make()
        with self.assertRaises(HelperError) as cm:
            d.handle(":1.5", 1000, "InstallPackages", (["evil"],))
        self.assertEqual(cm.exception.code, "Invalid")
        self.assertEqual(self.runner.calls, [])

    def test_only_one_job_at_a_time(self):
        gate = threading.Event()
        original = self.runner.run

        def slow(argv, emit, timeout=0):
            gate.wait(5)
            return original(argv, emit, timeout)
        self.runner.run = slow
        d = self.make()
        d.handle(":1.5", 1000, "InstallPackages", (["kate"],))
        with self.assertRaises(HelperError) as cm:
            d.handle(":1.6", 1000, "RunPostAction", ("mkinitcpio",))
        self.assertEqual(cm.exception.code, "Busy")
        gate.set()
        d.join()
        d.handle(":1.6", 1000, "RunPostAction", ("mkinitcpio",))   # free again
        d.join()

    def test_unexpected_exception_in_validation_is_a_clean_refusal(self):
        d = self.make()
        self.ctx.trusted = lambda: 1 / 0
        with self.assertRaises(HelperError) as cm:
            d.handle(":1.5", 1000, "InstallPackages", (["kate"],))
        self.assertEqual(cm.exception.code, "Failed")
        self.assertFalse(d._busy.locked())

    def test_admission_control_caps_pending_requests(self):
        d = self.make()
        got = [d.admit() for _ in range(12)]
        self.assertEqual(got.count(True), 8)
        d.leave()
        self.assertTrue(d.admit())

    def test_unknown_method(self):
        with self.assertRaises(HelperError):
            self.make().handle(":1.5", 1000, "RunShell", ("id",))
        self.assertEqual(self.auth.asked, [])

    def test_internal_error_still_finishes(self):
        self.runner.run = lambda *a, **k: 1 / 0
        d = self.make()
        d.handle(":1.5", 1000, "RunPostAction", ("mkinitcpio",))
        d.join()
        self.assertEqual(self.events[-1][2][1], False)
        self.assertFalse(d._busy.locked())

    def test_audit_has_uid_and_action_but_never_dropin_content(self):
        d = self.make()
        d.handle(":1.5", 1000, "WriteDropin", ("/etc/systemd/zram-generator.conf.d/heiss.conf",))
        d.join()
        log = open(os.path.join(self.tmp, "audit.log")).read()
        self.assertIn("uid=1000", log)
        self.assertIn("action=WriteDropin", log)
        self.assertNotIn("zram-size", log)

    def test_audit_neutralizes_control_characters(self):
        from heiss_helper.audit import clean
        self.assertNotIn("\n", clean("a\nb\x1b[31m"))


class DataFiles(unittest.TestCase):
    def polkit_ids(self):
        root = ET.parse(os.path.join(DATA, "org.heiss.helper.policy")).getroot()
        return root, {a.get("id") for a in root.findall("action")}

    def test_every_action_has_a_polkit_policy_and_vice_versa(self):
        _, ids = self.polkit_ids()
        self.assertEqual(ids, {a.polkit for a in ACTIONS.values()})

    def test_policy_defaults_require_admin_and_are_translated(self):
        root, _ = self.polkit_ids()
        xml_lang = "{http://www.w3.org/XML/1998/namespace}lang"
        for a in root.findall("action"):
            d = a.find("defaults")
            self.assertEqual(d.find("allow_any").text, "no")
            self.assertEqual(d.find("allow_inactive").text, "no")
            self.assertIn(d.find("allow_active").text, ("auth_admin", "auth_admin_keep"))
            for tag in ("description", "message"):
                self.assertEqual(sorted(e.get(xml_lang) or "en" for e in a.findall(tag)), ["en", "ru"], a.get("id"))

    def test_introspection_matches_actions(self):
        text = open(os.path.join(REPO, "helper", "heiss_helper", "service.py"), encoding="utf-8").read()
        methods = set(re.findall(r'<method name="(\w+)"', text))
        self.assertEqual(methods, set(ACTIONS) | {"Ping"})

    def test_dbus_and_systemd_files(self):
        ET.parse(os.path.join(DATA, "org.heiss.Helper1.conf"))
        conf = open(os.path.join(DATA, "org.heiss.Helper1.conf")).read()
        self.assertIn('<allow own="org.heiss.Helper1"/>', conf)
        self.assertEqual(conf.count("allow own"), 1)
        unit = open(os.path.join(DATA, "heiss-helper.service")).read()
        self.assertIn("Type=dbus", unit)
        self.assertIn("BusName=org.heiss.Helper1", unit)
        self.assertIn("NoNewPrivileges=yes", unit)
        self.assertIn("SystemdService=heiss-helper.service", open(os.path.join(DATA, "org.heiss.Helper1.service")).read())

    def test_glue_files_compile(self):
        for fn in ("service.py", "polkit.py", "__main__.py"):
            path = os.path.join(REPO, "helper", "heiss_helper", fn)
            with open(path, encoding="utf-8") as f:
                compile(f.read(), path, "exec")

    def test_no_shell_use_in_helper(self):
        src = ""
        for fn in os.listdir(os.path.join(REPO, "helper", "heiss_helper")):
            if fn.endswith(".py"):
                src += open(os.path.join(REPO, "helper", "heiss_helper", fn), encoding="utf-8").read()
        self.assertNotIn("shell=True", src)
        self.assertNotIn("os.system", src)
        self.assertNotIn("eval(", src)
        self.assertNotIn("exec(", src)


if __name__ == "__main__":
    unittest.main()
