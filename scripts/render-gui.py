#!/usr/bin/env python3
"""Developer tool: render every Heiss GUI page to PNG files without a display.

Starts heiss-welcome (the key-binding window) and heiss-control (every Control Center page) with
QT_QPA_PLATFORM=offscreen, on fixture data, in dark and light and in en and ru, grabs each window to a PNG and
prints the paths. It also collects every Qt/QML warning and error that was logged while loading and drawing.

Safety: it never needs root, never calls the real helper, pacman, lspci, systemctl or plasma tools (every source
of both apps is replaced by fixture data), and writes only inside its output directory (default: a new directory
from tempfile.mkdtemp; --out DIR to choose one, it must be new or empty).

Requires PySide6 (`pacman -S pyside6`). Not run in CI. The QML under test is the real Main.qml of each app; only
the small Python bridge object (the glue in app.py) is re-implemented here, synchronously, with the same
properties and slots.

    python3 scripts/render-gui.py [--out DIR] [--only welcome|control] [--lang en,ru] [--theme dark,light]
"""
import argparse
import json
import os
import sys
import shutil
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("core", "welcome", "control"):
    sys.path.insert(0, os.path.join(REPO, sub))

# must be set before Qt starts: no display, no GPU, log every QML message
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_LOGGING_RULES"] = "qt.qml*=true"

QUIET = [False]   # True while a window is being torn down
WARNINGS = []   # (kind, text) of every Qt message that is a warning, critical or fatal, or mentions .qml


def fixture_hardware(name="nvidia-hybrid-laptop"):
    from heiss_core import hardware as hw
    facts = hw.load_fixture(os.path.join(REPO, "core", "tests", "fixtures", "hw", name))
    return facts, hw.load_profiles(os.path.join(REPO, "hardware"))


class FakeApplier:
    """Stands in for the real `heiss apply`: no process is started."""
    def __init__(self, fail=False):
        self.fail = fail

    def plan(self, answers, hardware=()):
        return {"install_packages": ["a", "b", "c"], "remove_packages": ["d"], "enable_services": ["firewalld"],
                "disable_services": []}

    def run(self, answers, on_line, on_step, hardware=()):
        from heiss_core.errors import HeissError
        on_step(1, 3, "installing packages")
        on_line("resolving dependencies...")
        if self.fail:
            raise HeissError("fixture failure: package not found")


# ---------------------------------------------------------------- welcome

def welcome_pages(out, lang, theme, shots):
    """The key-binding window on the shipped hyprland.lua (Alt, then Super) and on a configuration of the user's own."""
    from heiss_core import hyprcfg
    from heiss_welcome import model
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    scratch = tempfile.mkdtemp(prefix="scratch-", dir=out)
    shipped = os.path.join(REPO, "desktop", "hypr", "hyprland.lua")

    class Bridge(QObject):
        changed = Signal()

        def __init__(self, cfg_dir):
            super().__init__()
            self.cfg_dir, self._screen = cfg_dir, model.screen(lang, cfg_dir)

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)

        @Slot(str)
        def search(self, query):
            self._screen = model.screen(lang, self.cfg_dir, query)
            self.changed.emit()

    def config(name, text):
        d = os.path.join(scratch, name)
        os.makedirs(os.path.join(d, "hypr"))
        with open(os.path.join(d, "hypr", "hyprland.lua"), "w", encoding="utf-8") as f:
            f.write(text)
        return d

    with open(shipped, encoding="utf-8") as f:
        shipped_text = f.read()
    alt, sup = config("alt", shipped_text), config("super", shipped_text)
    hyprcfg.write_modifier(sup, "SUPER")
    own = config("own", 'local mainMod = "SUPER"\n-- Open the terminal\nhl.bind(mainMod .. " + T", f())\n')
    empty = os.path.join(scratch, "empty")
    os.makedirs(empty)

    for name, cfg_dir, size in (("alt", alt, (760, 640)), ("alt-small", alt, (520, 440)), ("super", sup, (760, 640)),
                                ("own-config", own, (760, 640)), ("no-config", empty, (760, 640))):
        bridge = Bridge(cfg_dir)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("welcome", bridge)
        engine.load(QUrl.fromLocalFile(qml_for_theme(out, "welcome", theme)))
        if not engine.rootObjects():
            WARNINGS.append(("error", "welcome: Main.qml did not load"))
            return
        win = engine.rootObjects()[0]
        set_size(win, *size)
        shots.append(grab(win, os.path.join(out, "welcome-%s-%s-%s.png" % (lang, theme, name))))
        if name == "alt":
            bridge.search("workspace")
            shots.append(grab(win, os.path.join(out, "welcome-%s-%s-search.png" % (lang, theme))))
        close(engine)


# ---------------------------------------------------------------- control

def control_pages(out, lang, theme, shots):
    from heiss_core import answers as ans
    from heiss_core import wizard as wz
    from heiss_control import hardware_view as hwv
    from heiss_control import model as m
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    scratch = tempfile.mkdtemp(prefix="scratch-", dir=out)   # everything the model writes or reads lives here
    with open(os.path.join(scratch, "os-release"), "w", encoding="utf-8") as f:
        f.write('NAME="Heiss OS"\nPRETTY_NAME="Heiss OS"\nBUILD_ID=rolling\nHOME_URL="https://example.org/home"\n'
                'DOCUMENTATION_URL="https://example.org/docs"\nBUG_REPORT_URL="https://example.org/bugs"\n'
                'SUPPORT_URL="https://example.org/support"\n')
    answers = dict(ans.DEFAULTS, profile="cyber", addons=["addon-lts-kernel"])
    ans.save(os.path.join(scratch, "profile.toml"), answers)
    state = {"schema_version": 1, "applied": {"profile": "cyber", "addons": []},
             "packages": ["pkg-%03d" % i for i in range(40)], "services": ["firewalld.service"], "flatpaks": []}
    with open(os.path.join(scratch, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    user = os.path.join(scratch, "user")
    queue = wz.PendingQueue(os.path.join(user, "pending.json"))
    queue.add("apply-profile", {"profile": "developer", "addons": []})

    facts, profiles = fixture_hardware()
    # the NVIDIA driver is installed by Heiss here, so the page shows the "Remove this driver" button
    nv = ["nvidia-open", "nvidia-utils", "linux-lts", "nvidia-open-lts"]
    with open(os.path.join(scratch, "hw-state.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "applied": {"profile": "base", "addons": []}, "packages": nv, "services": [],
                   "flatpaks": []}, f)
    hwdata = hwv.collect(os.path.join(REPO, "hardware"), facts, {"mesa", "vulkan-icd-loader"} | set(nv), "6.12.1-arch1-1",
                         caps={"safe-graphics-entry"}, manifests_dir=os.path.join(REPO, "profiles"),
                         state_file=os.path.join(scratch, "hw-state.json"))

    def item(i, s, c, d=""):
        return {"id": i, "status": s, "code": c, "data": d}

    env = m.Env(
        os_release=os.path.join(scratch, "os-release"), system_answers=os.path.join(scratch, "profile.toml"),
        user_dir=user, state_file=os.path.join(scratch, "state.json"), profiles_dir=os.path.join(REPO, "profiles"),
        theme_get=lambda: theme,
        apply_theme=lambda t: (True, ""), online=lambda: True, run_pending_item=lambda it, step: None,
        run_check=lambda: [{"name": "units", "status": "OK", "detail": "all units active", "commands": []},
                           {"name": "firewall", "status": "WARN", "detail": "firewalld is not enabled", "commands": []},
                           {"name": "network", "status": "FAIL", "detail": "no default route", "commands": []}],
        open_settings=lambda: (True, ""), kernel=lambda: "6.12.1-arch1-1", plasma=lambda: "6.4.5",
        security_facts=lambda: [item("firewall", "warn", "inactive"), item("ssh", "warn", "on"),
                                item("disk", "warn", "plain"), item("secure_boot", "info", "disabled"),
                                item("listening", "warn", "some", "22, 631, 5353, 8080, 9090")],
        privacy_facts=lambda chosen: [item("level", "info", chosen or "unset"), item("wifi_mac", "warn", "preserve"),
                                      item("lock", "ok", "on", "3"), item("firewall", "ok", "active_enabled")],
        update_facts=lambda: [item("pending", "warn", "some", "128"), item("last", "warn", "old", "2026-09-14"),
                              item("reboot", "warn", "yes"), item("snapshots", "info", "btrfs_no_snapper")],
        hardware_data=lambda: hwdata)

    model = m.Model(env, language=lang)

    class Bridge(QObject):
        changed = Signal()

        def __init__(self):
            super().__init__()
            self._screen, self._results = model.screen(), []

        def refresh(self):
            self._screen = model.screen()
            self.changed.emit()

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)
        results = Property("QVariantList", lambda self: self._results, notify=changed)

        @Slot(str)
        def open(self, page_id):
            model.open(page_id)
            self.refresh()
        @Slot()
        def runHardware(self): pass
        @Slot()
        def copyReport(self): pass
        @Slot(str)
        def removeDriver(self, i): pass
        @Slot()
        def runUpdates(self): pass
        @Slot()
        def runNetwork(self): pass
        @Slot()
        def runPending(self): pass
        @Slot(int)
        def removePending(self, i): pass
        @Slot()
        def runSecurity(self): pass
        @Slot(str)
        def search(self, q):
            self._results = model.search(q)
            self.changed.emit()
        @Slot(str)
        def setTheme(self, t): pass
        @Slot()
        def runCheck(self): pass
        @Slot()
        def openSettings(self): pass
        @Slot(str)
        def setLanguage(self, lang_): pass
        @Slot(str)
        def openUrl(self, url): pass

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("control", bridge)
    engine.load(QUrl.fromLocalFile(qml_for_theme(out, "control", theme)))
    if not engine.rootObjects():
        WARNINGS.append(("error", "control: Main.qml did not load"))
        return
    win = engine.rootObjects()[0]
    set_size(win, 1000, 1500)   # tall, so the whole page is visible; the real window scrolls

    def shot(name):
        shots.append(grab(win, os.path.join(out, "control-%s-%s-%s.png" % (lang, theme, name))))

    for n, page in enumerate(m.PAGE_IDS):
        model.open(page)
        # the same data the background workers would have collected
        if page == "security":
            model.begin_security(); model.finish_security()
        elif page == "network":
            model.begin_network(); model.finish_network()
        elif page == "updates":
            model.begin_updates(); model.finish_updates()
        elif page == "hardware":
            model.begin_hardware(); model.finish_hardware()
        elif page == "advanced":
            model.begin_check(); model.finish_check()
        elif page == "appearance":
            model.theme_state = "ok"
        bridge.refresh()
        shot("%02d-%s" % (n, page))
    model.open("overview")
    bridge.refresh()
    query = "net" if lang == "en" else "сет"
    win.findChild(QObject, "searchField").setProperty("text", query)   # the QML calls control.search(text)
    pump()
    shot("%02d-search" % len(m.PAGE_IDS))
    # the smallest window the app allows (minimumWidth/minimumHeight in Main.qml): the worst case for long Russian text
    model.open("hardware")
    bridge.refresh()
    set_size(win, 640, 420)
    shot("%02d-hardware-smallest-window" % (len(m.PAGE_IDS) + 1))
    close(engine)


# ---------------------------------------------------------------- plumbing

SCHEME_TEST = "Qt.styleHints.colorScheme !== Qt.Light"


def qml_for_theme(out, app, theme):
    """Path of the app's Main.qml for this theme. The offscreen platform has no colour scheme and ignores
    QStyleHints.setColorScheme(), so a copy in the output directory gets that one test replaced by true/false.
    Fails when the line is not found exactly once (the QML changed: update SCHEME_TEST)."""
    src = os.path.join(REPO, app, "heiss_" + app, "qml", "Main.qml")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    if text.count(SCHEME_TEST) != 1:
        sys.exit("render-gui: %s must contain %r exactly once" % (src, SCHEME_TEST))
    d = tempfile.mkdtemp(prefix="qml-%s-%s-" % (app, theme), dir=out)
    dst = os.path.join(d, "Main.qml")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text.replace(SCHEME_TEST, "true" if theme == "dark" else "false"))
    for name in os.listdir(os.path.dirname(src)):   # shared components next to Main.qml, if any
        if name.endswith(".qml") and name != "Main.qml":
            shutil.copy(os.path.join(os.path.dirname(src), name), os.path.join(d, name))
    return dst


def set_size(win, w, h):
    from PySide6.QtGui import QWindow
    win.setVisibility(QWindow.Visibility.Windowed)
    win.resize(w, h)
    pump()


def close(engine):
    """Tear a window down; the bindings that fire while the bridge object goes away are not defects."""
    QUIET[0] = True
    engine.rootObjects()[0].close()
    engine.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    pump()
    QUIET[0] = False


def pump(ms=150):
    """Run the event loop for a moment so QML re-evaluates bindings and the scene is repainted."""
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def grab(win, path):
    pump()
    img = win.screen().grabWindow(win.winId()).toImage()   # the offscreen platform renders the Quick scene into it
    if img.isNull() or not img.save(path):
        WARNINGS.append(("error", "could not grab %s" % path))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="output directory (new or empty); default: a new temporary directory")
    ap.add_argument("--only", choices=("welcome", "control"))
    ap.add_argument("--lang", default="en,ru")
    ap.add_argument("--theme", default="dark,light")
    a = ap.parse_args()
    for opt, allowed in (("lang", ("en", "ru")), ("theme", ("dark", "light"))):
        if not set(getattr(a, opt).split(",")) <= set(allowed):
            ap.error("--%s must be a comma-separated list of %s" % (opt, ", ".join(allowed)))
    if os.geteuid() == 0:
        sys.exit("refusing to run as root: this tool never needs it")
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        sys.exit("PySide6 is required: sudo pacman -S pyside6")
    out = a.out or tempfile.mkdtemp(prefix="heiss-gui-")
    if os.path.islink(out):
        sys.exit("output directory must not be a symlink")
    try:
        os.makedirs(out, mode=0o700, exist_ok=True)
    except OSError as e:
        sys.exit("cannot create the output directory: %s" % e)
    if os.listdir(out):
        sys.exit("output directory %s is not empty" % out)
    for var, sub in (("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                     ("XDG_RUNTIME_DIR", "run")):   # Qt caches and settings go inside the output directory too
        d = os.path.join(out, "xdg", sub)
        os.makedirs(d, mode=0o700, exist_ok=True)
        os.environ[var] = d

    def handler(kind, ctx, msg):
        if not QUIET[0] and kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            WARNINGS.append((kind.name, msg))

    qInstallMessageHandler(handler)
    _app = QGuiApplication(["render-gui"])   # keeps the Qt application alive
    shots = []
    for lang in a.lang.split(","):
        for theme in a.theme.split(","):
            if a.only != "control":
                welcome_pages(out, lang, theme, shots)
            if a.only != "welcome":
                control_pages(out, lang, theme, shots)
    for p in shots:
        print(p)
    seen = set()
    print("\nQt/QML warnings and errors: %d" % len(WARNINGS))
    for kind, text in WARNINGS:
        if (kind, text) not in seen:
            seen.add((kind, text))
            print("  [%s] %s" % (kind, text))
    return 1 if any("did not load" in t or "could not grab" in t for _, t in WARNINGS) else 0


if __name__ == "__main__":
    sys.exit(main())
