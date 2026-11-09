"""polkit authorization for D-Bus callers (GDBus). The subject is the caller's unique bus name."""
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

AUTHORITY = ("org.freedesktop.PolicyKit1", "/org/freedesktop/PolicyKit1/Authority",
             "org.freedesktop.PolicyKit1.Authority")
ALLOW_USER_INTERACTION = 1


class Polkit:
    """is_authorized(sender, action_id) -> bool. Fails closed on any error."""

    def __init__(self, connection):
        self.connection = connection

    def is_authorized(self, sender, action_id):
        args = GLib.Variant("((sa{sv})sa{ss}us)",
                            (("system-bus-name", {"name": GLib.Variant("s", sender)}), action_id, {},
                             ALLOW_USER_INTERACTION, ""))
        try:
            reply = self.connection.call_sync(AUTHORITY[0], AUTHORITY[1], AUTHORITY[2], "CheckAuthorization",
                                              args, GLib.VariantType("((bba{ss}))"), Gio.DBusCallFlags.NONE, -1, None)
        except GLib.Error:
            return False
        return bool(reply.unpack()[0][0])   # (is_authorized, is_challenge, details)
