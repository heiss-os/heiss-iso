"""PySide6 glue: exposes the screen of model.py to QML. All logic lives in model.py and heiss_core.hyprcfg.

    heiss-welcome              show the window
    heiss-welcome --force      show it even when it was shown before
    heiss-welcome --first-run  from the session start: shows it once per user, never in the live session
"""
import os
import sys

from heiss_core import hyprcfg

from . import model


def main(argv=None):
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    class Bridge(QObject):
        changed = Signal()

        def __init__(self, lang, cfg_dir):
            super().__init__()
            self.lang, self.cfg_dir, self._query = lang, cfg_dir, ""
            self._screen = model.screen(lang, cfg_dir)

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)

        @Slot(str)
        def search(self, query):
            self._query = query
            self._screen = model.screen(self.lang, self.cfg_dir, query)
            self.changed.emit()

    argv = sys.argv if argv is None else argv
    cfg_dir = hyprcfg.config_dir()
    if not model.should_show("--first-run" in argv, "--force" in argv, cfg_dir):
        return 0
    app = QGuiApplication([a for a in argv if a not in ("--force", "--first-run")])
    app.setApplicationName("heiss-welcome")
    lang = "ru" if (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "").startswith("ru") else "en"
    bridge = Bridge(lang, cfg_dir)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("welcome", bridge)
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    if "--first-run" in argv:
        try:
            model.mark_done(cfg_dir)   # shown: do not show it at the next login
        except OSError:
            pass
    return app.exec()
