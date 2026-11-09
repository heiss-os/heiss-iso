"""GDBus client for org.heiss.Helper1, used by heiss-core and the GUIs.

call(method, args, on_output) starts a job, streams its output and returns when it
finishes. Signals can arrive before the reply that carries the job id, so they are
buffered until the id is known.
"""
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from heiss_core.errors import HeissError  # noqa: E402

from .actions import ACTIONS  # noqa: E402
from .service import BUS_NAME, ERROR_PREFIX, INTERFACE, OBJECT_PATH  # noqa: E402

CALL_TIMEOUT_MS = 10 * 60 * 1000   # a polkit dialog may wait for the user
JOB_TIMEOUT_S = 6 * 3600


class GioHelperClient:
    def __init__(self, connection=None, dest=BUS_NAME):
        self.connection = connection or Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.dest = dest

    def call(self, method, args, on_output):
        if method not in ACTIONS:
            raise HeissError("unknown helper method %r" % method)
        params = GLib.Variant("(%s)" % ACTIONS[method].signature, tuple(args))
        loop = GLib.MainLoop()
        state = {"job": None, "events": [], "result": None, "error": None}

        def handle(sig, p):
            job = p[0]
            if sig == "JobOutput":
                on_output(p[1])
            elif sig == "JobFinished":
                state["result"] = (p[1], p[2])
                loop.quit()
            return job

        def on_signal(conn, sender, path, iface, sig, p):
            ev = (sig, p.unpack())
            if state["job"] is None:
                state["events"].append(ev)          # reply not seen yet: keep in order
            elif ev[1][0] == state["job"]:
                handle(*ev)

        def on_reply(conn, task):
            try:
                state["job"] = conn.call_finish(task).unpack()[0]
            except GLib.Error as e:
                remote = Gio.DBusError.get_remote_error(e) or ""
                code = remote[len(ERROR_PREFIX):] if remote.startswith(ERROR_PREFIX) else "Failed"
                state["error"] = "%s: %s" % (code, e.message.split(": ", 1)[-1])
                loop.quit()
                return
            for ev in state["events"]:
                if ev[1][0] == state["job"]:
                    handle(*ev)
            state["events"] = []
            if state["result"] is not None:
                loop.quit()

        sub = self.connection.signal_subscribe(self.dest, INTERFACE, None, OBJECT_PATH, None,
                                               Gio.DBusSignalFlags.NONE, on_signal)
        timeout = GLib.timeout_add_seconds(JOB_TIMEOUT_S, loop.quit)
        try:
            self.connection.call(self.dest, OBJECT_PATH, INTERFACE, method, params, None,
                                 Gio.DBusCallFlags.NONE, CALL_TIMEOUT_MS, None, on_reply)
            loop.run()
        finally:
            GLib.source_remove(timeout)
            self.connection.signal_unsubscribe(sub)
        if state["error"]:
            raise HeissError(state["error"])
        if state["result"] is None:
            raise HeissError("the helper did not report a result")
        ok, message = state["result"]
        if not ok:
            raise HeissError(message)
