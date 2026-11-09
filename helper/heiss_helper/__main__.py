"""Entry point: run as root by systemd (Type=dbus, BusName=org.heiss.Helper1).

NOT covered by automated tests on the build VM (python-gobject is not installed there).
"""
import sys

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .polkit import Polkit  # noqa: E402
from .service import BUS_NAME, HelperService  # noqa: E402

IDLE_EXIT_SECONDS = 60


def main():
    loop = GLib.MainLoop()
    holder = {}

    def on_bus(connection, name):
        svc = HelperService(connection, Polkit(connection))
        svc.register()
        holder["svc"] = svc

    def on_lost(connection, name):
        loop.quit()

    def check_idle():
        svc = holder.get("svc")
        if svc is not None and svc.dispatcher.idle_for() > IDLE_EXIT_SECONDS:
            loop.quit()
            return False
        return True

    Gio.bus_own_name(Gio.BusType.SYSTEM, BUS_NAME, Gio.BusNameOwnerFlags.NONE, on_bus, None, on_lost)
    GLib.timeout_add_seconds(15, check_idle)   # exit when idle; D-Bus activation restarts the helper
    loop.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
