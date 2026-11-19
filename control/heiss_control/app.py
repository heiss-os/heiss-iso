"""PySide6 glue: exposes the model to QML as one object. All logic lives in model.py."""
import os
import sys
import threading

from .model import Model


def main(argv=None):
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtGui import QDesktopServices, QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    class Bridge(QObject):
        changed = Signal()
        jobDone = Signal()   # emitted from the worker thread; delivered on the GUI thread

        def __init__(self, model):
            super().__init__()
            self.model, self._screen = model, model.screen()
            self.jobDone.connect(self._set)

        def _set(self):
            self._screen = self.model.screen()
            self.changed.emit()

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)

        def _work(self, job, arg):
            try:
                self.model.finish(job, arg)
            finally:
                self.jobDone.emit()

        @Slot(str, str)
        def run(self, job, arg):
            # theme switch, hyprctl, hardware detection and `heiss check` are never run on the GUI thread
            if self.model.begin(job, arg):
                threading.Thread(target=self._work, args=(job, arg), daemon=True).start()
            self._set()

        @Slot(str)
        def open(self, page):
            self.model.open(page)
            if page == "hardware" and self.model.hw_state == "idle":
                self.run("detect", "")
            self._set()

        @Slot()
        def copyReport(self):
            self.model.copy_report(QGuiApplication.clipboard().setText)
            self._set()

        @Slot(str)
        def openUrl(self, url):
            # only the links of os-release (https); QML never passes anything else
            if url.startswith("https://"):
                QDesktopServices.openUrl(QUrl(url))

    argv = sys.argv if argv is None else argv
    app = QGuiApplication(argv)
    app.setApplicationName("heiss-control")
    lang = "ru" if (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "").startswith("ru") else "en"
    bridge = Bridge(Model(language=lang))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("control", bridge)
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()
