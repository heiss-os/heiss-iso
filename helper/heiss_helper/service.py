"""GDBus glue for org.heiss.Helper1. Thin on purpose: all decisions are in dispatch.py.

NOT covered by automated tests on the build VM (python-gobject is not installed there).
"""
import threading

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from . import __version__  # noqa: E402
from .audit import clean  # noqa: E402
from .dispatch import Dispatcher  # noqa: E402
from .errors import HelperError  # noqa: E402

BUS_NAME = "org.heiss.Helper1"
OBJECT_PATH = "/org/heiss/Helper1"
INTERFACE = "org.heiss.Helper1"
ERROR_PREFIX = "org.heiss.Helper1.Error."
SIGNAL_TYPES = {"JobOutput": "(ss)", "JobFinished": "(sbs)"}

INTROSPECTION = """
<node>
  <interface name="org.heiss.Helper1">
    <method name="Ping"><arg type="s" direction="out" name="version"/></method>
    <method name="InstallPackages"><arg type="as" direction="in" name="packages"/><arg type="s" direction="out" name="job"/></method>
    <method name="RemovePackages"><arg type="as" direction="in" name="packages"/><arg type="s" direction="out" name="job"/></method>
    <method name="AdoptPackages"><arg type="as" direction="in" name="packages"/><arg type="s" direction="out" name="job"/></method>
    <method name="SetServices"><arg type="as" direction="in" name="enable"/><arg type="as" direction="in" name="disable"/><arg type="s" direction="out" name="job"/></method>
    <method name="WriteDropin"><arg type="s" direction="in" name="path"/><arg type="s" direction="out" name="job"/></method>
    <method name="WritePrivacy"><arg type="s" direction="in" name="level"/><arg type="s" direction="out" name="job"/></method>
    <method name="RunPostAction"><arg type="s" direction="in" name="action"/><arg type="s" direction="out" name="job"/></method>
    <method name="UpdateSystem"><arg type="s" direction="out" name="job"/></method>
    <method name="CreateSnapshot"><arg type="s" direction="in" name="description"/><arg type="s" direction="out" name="job"/></method>
    <signal name="JobOutput"><arg type="s" name="job"/><arg type="s" name="line"/></signal>
    <signal name="JobFinished"><arg type="s" name="job"/><arg type="b" name="ok"/><arg type="s" name="message"/></signal>
  </interface>
</node>
"""


class HelperService:
    def __init__(self, connection, authorizer, ctx=None, audit=None):
        self.connection = connection
        self.dispatcher = Dispatcher(authorizer, self._emit, ctx, audit)
        self._node = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION)
        self._reg_id = None

    def register(self):
        self._reg_id = self.connection.register_object(OBJECT_PATH, self._node.interfaces[0], self._on_call, None, None)

    def _emit(self, sender, signal, args):
        self.connection.emit_signal(sender, OBJECT_PATH, INTERFACE, signal, GLib.Variant(SIGNAL_TYPES[signal], args))

    def _uid(self, sender):
        try:
            r = self.connection.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                                          "GetConnectionUnixUser", GLib.Variant("(s)", (sender,)),
                                          GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, -1, None)
            return r.unpack()[0]
        except GLib.Error:
            return "?"

    def _on_call(self, connection, sender, path, iface, method, params, invocation):
        if method == "Ping":
            invocation.return_value(GLib.Variant("(s)", (__version__,)))
            return
        if not self.dispatcher.admit():     # a local user must not be able to exhaust threads
            invocation.return_dbus_error(ERROR_PREFIX + "Busy", "too many pending requests")
            return
        # polkit may block on a dialog: keep the main loop free
        threading.Thread(target=self._worker, args=(sender, method, params.unpack(), invocation), daemon=True).start()

    def _worker(self, sender, method, args, invocation):
        try:
            job = self.dispatcher.handle(sender, self._uid(sender), method, args)
            invocation.return_value(GLib.Variant("(s)", (job,)))
        except HelperError as e:
            invocation.return_dbus_error(ERROR_PREFIX + e.code, clean(e.message, 500))
        finally:
            self.dispatcher.leave()
