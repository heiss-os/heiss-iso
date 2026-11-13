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
        themeDone = Signal()   # emitted from the worker thread; delivered on the GUI thread
        checkDone = Signal()
        securityDone = Signal()
        pendingProgress = Signal()   # every step and the end of a saved-actions run, from the worker thread

        def __init__(self, model):
            super().__init__()
            self.model, self._screen, self._results = model, model.screen(), []
            self.themeDone.connect(self._set)
            self.checkDone.connect(self._set)
            self.securityDone.connect(self._set)
            self.pendingProgress.connect(self._set)

        def _set(self):
            self._screen = self.model.screen()
            self.changed.emit()

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)
        results = Property("QVariantList", lambda self: self._results, notify=changed)

        @Slot(str)
        def open(self, page_id):
            self.model.open(page_id)
            self._set()
            if page_id == "security" and self.model.sec_state == "idle":
                self.runSecurity()

        @Slot()
        def runPending(self):
            # installs through the helper (the system asks for the password): only on a click, in a worker thread
            if self.model.begin_pending():
                threading.Thread(target=self._pending, daemon=True).start()
            self._set()

        def _pending(self):
            try:
                self.model.finish_pending(self.pendingProgress.emit)
            finally:
                self.pendingProgress.emit()

        @Slot(int)
        def removePending(self, item_id):
            self.model.remove_pending(item_id)
            self._set()

        @Slot()
        def runSecurity(self):
            # a handful of short commands, but still never on the GUI thread
            if self.model.begin_security():
                threading.Thread(target=self._security, daemon=True).start()
                self._set()

        def _security(self):
            try:
                self.model.finish_security()
            finally:
                self.securityDone.emit()

        @Slot(str)
        def search(self, query):
            self._results = self.model.search(query)
            self.changed.emit()

        @Slot(str)
        def setTheme(self, theme):
            # plasma-apply-lookandfeel can take seconds: never on the GUI thread
            if self.model.begin_theme(theme):
                threading.Thread(target=self._switch, args=(theme,), daemon=True).start()
                self._set()

        def _switch(self, theme):
            self.model.finish_theme(theme)
            self.themeDone.emit()

        @Slot()
        def runCheck(self):
            # `heiss check` runs several commands (up to 30 s each): never on the GUI thread
            if self.model.begin_check():
                threading.Thread(target=self._check, daemon=True).start()
                self._set()

        def _check(self):
            try:
                self.model.finish_check()
            finally:
                self.checkDone.emit()

        @Slot()
        def openSettings(self):
            self.model.open_stock_settings()
            self._set()

        @Slot(str)
        def setLanguage(self, language):
            self.model.set_language(language)
            self._set()

        @Slot(str)
        def openUrl(self, url):
            # only links that came from os-release; QML never passes anything else
            if url.startswith("https://"):
                QDesktopServices.openUrl(QUrl(url))

    argv = sys.argv if argv is None else argv
    app = QGuiApplication(argv)
    app.setApplicationName("heiss-control")
    lang = (os.environ.get("LANG") or "en")[:2]
    bridge = Bridge(Model(language=lang))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("control", bridge)
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()
