"""PySide6 glue: exposes the view model to QML as one object. All logic lives in viewmodel.py."""
import os
import sys

from heiss_core import manifest as mf
from heiss_core import wizard as wz

from .viewmodel import ViewModel

PROFILES = os.environ.get("HEISS_PROFILES", "/usr/share/heiss/profiles")


def build(config_dir, profiles_dir=PROFILES):
    manifests = mf.load_dir(profiles_dir)
    store = wz.Store(config_dir)
    wiz = store.load(manifests) or wz.Wizard(manifests)
    return ViewModel(wiz, manifests, store, wz.PendingQueue(store.p("pending.json"))), store


def main(argv=None):
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    class Bridge(QObject):
        changed = Signal()

        def __init__(self, vm):
            super().__init__()
            self.vm, self._screen = vm, vm.screen()

        def _set(self, screen):
            self._screen = screen
            self.changed.emit()

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)

        @Slot(str, "QVariant")
        def choose(self, path, value): self._set(self.vm.choose(path, value))

        @Slot(str)
        def toggleAddon(self, addon_id): self._set(self.vm.toggle_addon(addon_id))

        @Slot()
        def next(self): self._set(self.vm.next())

        @Slot()
        def back(self): self._set(self.vm.back())

        @Slot()
        def skip(self): self._set(self.vm.skip())

        @Slot()
        def skipAll(self): self._set(self.vm.skip_whole())

        @Slot()
        def saveLater(self): self._set(self.vm.save_later())

    argv = sys.argv if argv is None else argv
    config = os.environ.get("HEISS_CONFIG_DIR") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "heiss")
    vm, store = build(config)
    if store.is_done() and "--force" not in argv:
        return 0
    app = QGuiApplication(argv)
    app.setApplicationName("heiss-welcome")
    bridge = Bridge(vm)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("wizard", bridge)
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()
