"""Keep every themed part of the desktop in line with the active Heiss theme.

Plasma itself applies the Look-and-Feel defaults (color scheme, accent, icons, Plasma style,
splash) when the Global Theme changes, and kde-gtk-config and the KDE portal handle GTK and
libadwaita. This module does what nothing else does (launcher icon, Konsole), and CHECKS the
rest, so a half-switched desktop is reported instead of staying silent.

One result line per target: changed, ok, skipped, warn or failed, with a reason. Nothing is
written to files that Plasma owns; only the launcher icon and Konsole's default profile are set.
"""
import contextlib
import fcntl
import os
import re
import subprocess
import time
from dataclasses import dataclass

THEME_OF = {"HeissDark": "dark", "HeissLight": "light"}
LAUNCHER_ICON = {"dark": "heiss-launcher-sand", "light": "heiss-launcher-sand-light"}
KONSOLE_PROFILE = {"dark": ("Heiss Dark", "Heiss-Dark.profile"), "light": ("Heiss Light", "Heiss-Light.profile")}
LNF_PACKAGE = {"dark": "org.heiss.dark.desktop", "light": "org.heiss.light.desktop"}
LNF_DIR = "/usr/share/plasma/look-and-feel"
KONSOLE_DIR = "/usr/share/konsole"
PORTAL_SCHEME = {"dark": "1", "light": "2"}                     # org.freedesktop.appearance color-scheme
GSETTINGS_OK = {"dark": {"prefer-dark"}, "light": {"default", "prefer-light"}}
# keys of the Look-and-Feel defaults that we compare; the accent color is left out on purpose (users may change it)
CHECKED_KEYS = {("kdeglobals", "General", "ColorScheme"), ("kdeglobals", "Icons", "Theme"),
                ("kdeglobals", "KDE", "widgetStyle"), ("plasmarc", "Theme", "name"),
                ("ksplashrc", "KSplash", "Theme")}
TARGETS_ORDER = ("launcher-icon", "konsole", "plasma-consistency", "gtk", "portal", "kitty")


@dataclass
class Result:
    target: str
    status: str   # changed | ok | skipped | warn | failed
    detail: str

    def line(self):
        return "theme-sync: %s: %s: %s" % (self.target, self.status, self.detail)


# ---------- real environment ----------

class RealEnv:
    """Runs fixed commands as the user. Never a shell."""

    def __init__(self):
        self.home = os.path.expanduser("~")

    def _run(self, argv, timeout=15):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout
        except (OSError, subprocess.TimeoutExpired):
            return 127, ""

    def kde_read(self, file, group, key):
        rc, out = self._run(["kreadconfig6", "--file", file, "--group", group, "--key", key])
        return out.rstrip("\n") if rc == 0 else None

    def kde_write(self, file, group, key, value):
        rc, _ = self._run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--", value])
        return rc == 0

    def plasma_eval(self, script):
        return self._run(["busctl", "--user", "call", "org.kde.plasmashell", "/PlasmaShell",
                          "org.kde.PlasmaShell", "evaluateScript", "s", script])[0] == 0

    def busctl(self, args):
        return self._run(["busctl", "--user"] + list(args))

    def gsettings(self, schema, key):
        rc, out = self._run(["gsettings", "get", schema, key])
        return out.strip().strip("'") if rc == 0 else None

    def process_running(self, name):
        return self._run(["pgrep", "-x", name])[0] == 0

    def command_exists(self, name):
        return any(os.access(os.path.join(d, name), os.X_OK) for d in os.environ.get("PATH", "/usr/bin").split(":"))

    def exists(self, path):
        return os.path.exists(path)

    def read_text(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def append_log(self, line):
        base = os.environ.get("XDG_STATE_HOME") or os.path.join(self.home, ".local", "state")
        path = os.path.join(base, "heiss", "theme-sync.log")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.exists(path) and os.path.getsize(path) > 200 * 1024:
                os.replace(path, path + ".1")
            with open(path, "a", encoding="utf-8") as f:
                f.write(time.strftime("%F %T ") + line + "\n")
        except OSError:
            pass   # stderr/journald still has the line

    @contextlib.contextmanager
    def lock(self):
        path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "heiss-theme-sync.lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            yield True
        finally:
            os.close(fd)


# ---------- targets ----------

def target_launcher(env, theme, dry):
    icon = LAUNCHER_ICON[theme]
    if dry:
        return Result("launcher-icon", "ok", "would set the launcher icon to %s" % icon)
    script = """
var icon = '%s';
for (var p of panels()) {
  for (var w of p.widgets()) {
    if (w.type != 'org.kde.plasma.kickoff') continue;
    w.currentConfigGroup = ['General'];
    var cur = String(w.readConfig('icon'));
    if (cur.indexOf('heiss-launcher-sand') == 0 && cur != icon) w.writeConfig('icon', icon);
  }
}""" % icon
    if env.plasma_eval(script):
        return Result("launcher-icon", "ok", "requested %s from plasmashell (a custom icon is left alone; result cannot be read back)" % icon)
    return Result("launcher-icon", "failed", "plasmashell did not accept the script (is it running?)")


def target_konsole(env, theme, dry):
    name, filename = KONSOLE_PROFILE[theme]
    if not env.command_exists("konsole"):
        return Result("konsole", "skipped", "Konsole is not installed")
    if not env.exists(os.path.join(KONSOLE_DIR, filename)):
        return Result("konsole", "skipped", "profile file %s is missing (package heiss-theme)" % filename)
    current = env.kde_read("konsolerc", "Desktop Entry", "DefaultProfile")
    changed = current != filename
    if changed and not dry and not env.kde_write("konsolerc", "Desktop Entry", "DefaultProfile", filename):
        return Result("konsole", "failed", "could not write the default profile")
    sessions, failed = 0, 0
    if not dry:
        rc, listing = env.busctl(["list", "--no-legend"])
        for svc in [l.split()[0] for l in listing.splitlines() if l.startswith("org.kde.konsole-")]:
            rc, tree = env.busctl(["tree", svc, "--list"])
            for path in [l.strip() for l in tree.splitlines() if re.fullmatch(r"/Sessions/\d+", l.strip())]:
                ok = env.busctl(["call", svc, path, "org.kde.konsole.Session", "setProfile", "s", name])[0] == 0
                sessions += ok
                failed += not ok
    detail = "default profile %s" % ("set to " + filename if changed else filename + " already set")
    if dry:
        return Result("konsole", "changed" if changed else "ok", "would use " + detail)
    detail += ", %d running session(s) switched" % sessions
    if failed:
        return Result("konsole", "warn", detail + ", %d session(s) refused the change" % failed)
    return Result("konsole", "changed" if changed or sessions else "ok", detail)


def _parse_lnf_defaults(text):
    """{(file, group, key): value} from a Look-and-Feel `defaults` file."""
    out, file, group = {}, None, None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.fullmatch(r"\[([^\]]+)\]\[([^\]]+)\]", line)
        if m:
            file, group = m.groups()
        elif re.fullmatch(r"\[([^\]]+)\]", line):
            file, group = ("ksplashrc", line[1:-1]) if line == "[KSplash]" else (None, line[1:-1])
        elif "=" in line and file:
            k, v = line.split("=", 1)
            out[(file, group, k)] = v
    return out


def target_plasma_consistency(env, theme, dry):
    path = os.path.join(LNF_DIR, LNF_PACKAGE[theme], "contents", "defaults")
    text = env.read_text(path)
    if text is None:
        return Result("plasma-consistency", "skipped", "no Look-and-Feel defaults at %s" % path)
    wrong = []
    for (file, group, key), expected in sorted(_parse_lnf_defaults(text).items()):
        if (file, group, key) not in CHECKED_KEYS:
            continue
        got = env.kde_read(file, group, key)
        if got != expected:
            wrong.append("%s/%s/%s expected %s got %s" % (file, group, key, expected, got))
    if wrong:
        return Result("plasma-consistency", "warn", "; ".join(wrong))
    return Result("plasma-consistency", "ok", "color scheme, icons, widget style, Plasma style and splash match %s" % LNF_PACKAGE[theme])


def target_gtk(env, theme, dry):
    rc, out = env.busctl(["call", "org.kde.kded6", "/kded", "org.kde.kded6", "loadedModules"])
    if rc != 0:
        return Result("gtk", "warn", "kded is not reachable, cannot tell whether GTK settings follow the theme")
    if "gtkconfig" not in out:
        return Result("gtk", "failed", "the kde-gtk-config module (gtkconfig) is not loaded: GTK apps will not follow the theme")
    value = env.gsettings("org.gnome.desktop.interface", "color-scheme")
    if value is None:
        return Result("gtk", "ok", "gtkconfig is loaded (GSettings not available to compare)")
    if value not in GSETTINGS_OK[theme]:
        return Result("gtk", "warn", "gtkconfig is loaded but GSettings color-scheme is %s, expected one of %s" % (value, sorted(GSETTINGS_OK[theme])))
    return Result("gtk", "ok", "gtkconfig is loaded and GSettings color-scheme is %s" % value)


def target_portal(env, theme, dry):
    rc, out = env.busctl(["call", "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                          "org.freedesktop.portal.Settings", "Read", "ss", "org.freedesktop.appearance", "color-scheme"])
    if rc != 0:
        return Result("portal", "warn", "the settings portal is not reachable: libadwaita apps may not follow the theme")
    m = re.search(r"\bu\s+(\d)\b", out)
    if not m:
        return Result("portal", "warn", "unexpected portal answer: %s" % out.strip()[:80])
    if m.group(1) != PORTAL_SCHEME[theme]:
        return Result("portal", "warn", "portal color-scheme is %s, expected %s" % (m.group(1), PORTAL_SCHEME[theme]))
    return Result("portal", "ok", "portal color-scheme is %s (%s)" % (m.group(1), theme))


def target_kitty(env, theme, dry):
    if not env.command_exists("kitty"):
        return Result("kitty", "skipped", "kitty is not installed")
    files = [os.path.join("/etc/xdg/kitty", "%s-theme.auto.conf" % t) for t in ("dark", "light")]
    if all(env.exists(f) for f in files):
        return Result("kitty", "ok", "follows the portal color scheme through kitty's automatic theme files, nothing to switch")
    return Result("kitty", "warn", "automatic theme files for kitty are missing (package heiss-theme)")


TARGETS = (("launcher-icon", target_launcher), ("konsole", target_konsole),
           ("plasma-consistency", target_plasma_consistency), ("gtk", target_gtk),
           ("portal", target_portal), ("kitty", target_kitty))
assert tuple(n for n, _ in TARGETS) == TARGETS_ORDER


# ---------- driver ----------

def sync(env, wait=True, dry_run=False, sleep=time.sleep, say=None):
    """Run every target once. Returns (results, exit_code). exit_code 1 only when a target failed."""
    say = say or (lambda line: None)
    with env.lock() as got:
        if not got:
            r = [Result("all", "skipped", "another theme sync is running")]
            for x in r:
                say(x.line())
            return r, 0
        if wait:
            for _ in range(60):
                if env.process_running("plasmashell"):
                    break
                sleep(1)
            sleep(2)   # a theme switch writes kdeglobals several times: read the final state
        scheme = env.kde_read("kdeglobals", "General", "ColorScheme")
        theme = THEME_OF.get(scheme)
        if scheme is None:
            results = [Result("all", "failed", "cannot read the color scheme (kreadconfig6 missing or not in a desktop session)")]
        elif theme is None:
            results = [Result(n, "skipped", "color scheme is %r, not a Heiss scheme: nothing is changed" % scheme) for n, _ in TARGETS]
        else:
            results = []
            for name, fn in TARGETS:
                try:
                    results.append(fn(env, theme, dry_run))
                except Exception as e:  # a bug in one target must not hide the others
                    results.append(Result(name, "failed", "internal error: %s: %s" % (type(e).__name__, e)))
        for r in results:
            say(r.line())
    return results, (1 if any(r.status == "failed" for r in results) else 0)
