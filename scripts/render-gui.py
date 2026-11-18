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
    """Every page of the settings window on fixture data: no hyprctl, no nmcli, no pacman, no real home."""
    from heiss_core import hyprcfg
    from heiss_control import hardware_view as hwv
    from heiss_control import model as m
    from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    scratch = tempfile.mkdtemp(prefix="scratch-", dir=out)   # everything the model writes or reads lives here
    cfg_dir = os.path.join(scratch, "config")
    os.makedirs(os.path.join(cfg_dir, "hypr"))
    shutil.copy(os.path.join(REPO, "desktop", "hypr", "hyprland.lua"), os.path.join(cfg_dir, "hypr", "hyprland.lua"))
    hyprcfg.set_block(cfg_dir, "keyboard", 'hl.config({ input = { kb_layout = "us,ru", kb_options = "grp:ctrl_shift_toggle" } })')
    with open(os.path.join(scratch, "os-release"), "w", encoding="utf-8") as f:
        f.write('NAME="Heiss OS"\nPRETTY_NAME="Heiss OS"\nBUILD_ID=rolling\nHOME_URL="https://example.org/home"\n'
                'DOCUMENTATION_URL="https://example.org/docs"\nBUG_REPORT_URL="https://example.org/bugs"\n')
    facts, profiles = fixture_hardware()
    installed = {"nvidia-open", "nvidia-utils"}

    def hardware_data():
        return hwv.collect(facts=facts, installed=installed, kernel="6.12.1-arch1-1", caps=set(), hardware_dir=os.path.join(REPO, "hardware"))

    def run(argv, timeout=10):
        if argv[0] == "nmcli":
            return 0, "connected:full\n"
        return 0, ""

    env = m.Env(cfg_dir=cfg_dir, os_release=os.path.join(scratch, "os-release"), system_answers=os.path.join(scratch, "none.toml"),
                state_file=os.path.join(scratch, "state.json"), profiles_dir=os.path.join(REPO, "profiles"),
                theme_get=lambda: theme, apply_theme=lambda t: (True, ""), run=run, launch=lambda key: (key != "bluetooth", "blueman-manager"),
                monitors=lambda: [{"name": "Virtual-1", "width": 1920, "height": 1080, "refresh": 60.0, "scale": 1.0},
                                  {"name": "HDMI-A-1", "width": 2560, "height": 1440, "refresh": 143.9, "scale": 1.5}],
                layouts=lambda: {"us", "ru", "de"}, hardware_data=hardware_data, kernel=lambda: "6.12.1-arch1-1",
                run_check=lambda: [{"name": "theme", "status": "OK", "detail": theme}, {"name": "firewall", "status": "WARN", "detail": "firewalld is not enabled"},
                                   {"name": "services", "status": "FAIL", "detail": "one unit failed"}])

    class Bridge(QObject):
        changed = Signal()

        def __init__(self, model):
            super().__init__()
            self.model, self._screen = model, model.screen()

        def _set(self):
            self._screen = self.model.screen()
            self.changed.emit()

        screen = Property("QVariantMap", lambda self: self._screen, notify=changed)

        @Slot(str, str)
        def run(self, job, arg):
            if self.model.begin(job, arg):
                self.model.finish(job, arg)   # synchronously: the render waits for the result
            self._set()

        @Slot(str)
        def open(self, page): self.model.open(page); self._set()
        @Slot()
        def copyReport(self): self.model.copy_report(lambda text: None); self._set()
        @Slot(str)
        def openUrl(self, url): pass

    model = m.Model(env, language=lang)
    bridge = Bridge(model)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("control", bridge)
    engine.load(QUrl.fromLocalFile(qml_for_theme(out, "control", theme)))
    if not engine.rootObjects():
        WARNINGS.append(("error", "control: Main.qml did not load"))
        return
    win = engine.rootObjects()[0]
    set_size(win, 1000, 680)
    for page in m.PAGES:
        bridge.open(page)
        if page == "hardware":
            bridge.run("detect", "")
        if page == "system":
            bridge.run("check", "")
        if page == "network":
            bridge.run("launch", "bluetooth")
        shots.append(grab(win, os.path.join(out, "control-%s-%s-%s.png" % (lang, theme, page))))
    bridge.open("keyboard")
    bridge.run("modifier", "SUPER")
    bridge.run("layout", "xx")           # refused: shows the layout hint error
    shots.append(grab(win, os.path.join(out, "control-%s-%s-keyboard-after.png" % (lang, theme))))
    set_size(win, 640, 420)
    shots.append(grab(win, os.path.join(out, "control-%s-%s-keyboard-small.png" % (lang, theme))))
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
