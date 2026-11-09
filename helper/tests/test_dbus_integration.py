"""End-to-end test of the GDBus glue on a PRIVATE bus (Gio.TestDBus), with a fake polkit and runner.

Skipped when python-gobject or dbus-daemon is missing (the build VM has neither: CI runs it).
"""
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_helper import Env, FakeAuth  # noqa: E402

try:
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib
    HAVE = shutil.which("dbus-daemon") is not None
except (ImportError, ValueError, AttributeError):
    HAVE = False

if HAVE:
    from heiss_core.errors import HeissError
    from heiss_helper.audit import Audit
    from heiss_helper.client import GioHelperClient
    from heiss_helper.service import INTERFACE, OBJECT_PATH, HelperService


@unittest.skipUnless(HAVE, "python-gobject and dbus-daemon are required")
class BusBase(Env):
    def setUp(self):
        super().setUp()
        self.testbus = Gio.TestDBus.new(Gio.TestDBusFlags.NONE)
        self.testbus.up()
        self.addCleanup(self.testbus.down)
        flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
        addr = self.testbus.get_bus_address()
        self.server = Gio.DBusConnection.new_for_address_sync(addr, flags, None, None)
        self.client = Gio.DBusConnection.new_for_address_sync(addr, flags, None, None)
        self.auth = FakeAuth(True)
        self.svc = HelperService(self.server, self.auth, self.ctx, Audit(os.path.join(self.tmp, "audit.log")))
        self.svc.register()
        self.dest = self.server.get_unique_name()
        self.signals = []
        self.client.signal_subscribe(self.dest, INTERFACE, None, OBJECT_PATH, None, Gio.DBusSignalFlags.NONE,
                                     lambda c, s, p, i, sig, params: self.signals.append((sig, params.unpack())))

    def call(self, method, params=None):
        out, loop = {}, GLib.MainLoop()

        def done(conn, task):
            try:
                out["value"] = conn.call_finish(task).unpack()
            except GLib.Error as e:
                out["error"] = Gio.DBusError.get_remote_error(e) or e.message
            loop.quit()
        self.client.call(self.dest, OBJECT_PATH, INTERFACE, method, params, None, Gio.DBusCallFlags.NONE, 8000, None, done)
        GLib.timeout_add_seconds(15, loop.quit)
        loop.run()
        return out

    def wait_finished(self):
        loop = GLib.MainLoop()

        def poll():
            if any(s[0] == "JobFinished" for s in self.signals):
                loop.quit()
                return False
            return True
        GLib.timeout_add(50, poll)
        GLib.timeout_add_seconds(15, loop.quit)
        loop.run()


@unittest.skipUnless(HAVE, "python-gobject and dbus-daemon are required")
class DBusGlue(BusBase):
    def test_ping(self):
        self.assertEqual(self.call("Ping")["value"][0], "0.1.0")

    def test_install_streams_signals_to_caller(self):
        r = self.call("InstallPackages", GLib.Variant("(as)", (["kate"],)))
        job = r["value"][0]
        self.wait_finished()
        finished = [s for s in self.signals if s[0] == "JobFinished"][0]
        self.assertEqual(finished[1], (job, True, "done"))
        self.assertTrue(any(s[0] == "JobOutput" for s in self.signals))
        self.assertEqual(self.runner.calls[-1][:3], ["pacman", "-S", "--needed"])
        self.assertEqual(self.auth.asked[-1][1], "org.heiss.packages.install")

    def test_unauthorized_error_name(self):
        self.auth.allow = False
        r = self.call("InstallPackages", GLib.Variant("(as)", (["kate"],)))
        self.assertEqual(r["error"], "org.heiss.Helper1.Error.NotAuthorized")
        self.assertEqual(self.runner.calls, [])

    def test_invalid_error_name(self):
        r = self.call("InstallPackages", GLib.Variant("(as)", (["not-allowed"],)))
        self.assertEqual(r["error"], "org.heiss.Helper1.Error.Invalid")

    def test_unknown_method_is_rejected_by_the_bus(self):
        self.assertIn("error", self.call("RunShell", GLib.Variant("(s)", ("id",))))


@unittest.skipUnless(HAVE, "python-gobject and dbus-daemon are required")
class ClientAgainstService(BusBase):
    """The real GioHelperClient talking to the real service over the private bus."""

    def setUp(self):
        super().setUp()
        self.server_thread_note = "service and client share one process: the client spins a loop while the service answers from worker threads"
        self.client_api = GioHelperClient(self.client, self.dest)

    def test_call_streams_output_and_returns_on_success(self):
        lines = []
        self.client_api.call("InstallPackages", (["kate"],), lines.append)
        self.assertTrue(any("ran pacman" in l for l in lines))
        self.assertEqual(self.runner.calls[-1][:3], ["pacman", "-S", "--needed"])

    def test_many_calls_in_a_row_never_lose_the_final_signal(self):
        for _ in range(10):      # the job can finish before the reply with its id is processed
            self.client_api.call("RunPostAction", ("mkinitcpio",), lambda l: None)

    def test_failed_job_raises_with_message(self):
        self.runner.fail_on = "mkinitcpio"
        with self.assertRaises(HeissError) as cm:
            self.client_api.call("RunPostAction", ("mkinitcpio",), lambda l: None)
        self.assertIn("failed", str(cm.exception))

    def test_unauthorized_raises_with_code(self):
        self.auth.allow = False
        with self.assertRaises(HeissError) as cm:
            self.client_api.call("InstallPackages", (["kate"],), lambda l: None)
        self.assertIn("NotAuthorized", str(cm.exception))

    def test_invalid_raises_with_code(self):
        with self.assertRaises(HeissError) as cm:
            self.client_api.call("InstallPackages", (["not-allowed"],), lambda l: None)
        self.assertIn("Invalid", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
