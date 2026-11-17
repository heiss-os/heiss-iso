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
import stat
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
WALLPAPER = {"dark": "Heiss-Everyday", "light": "Heiss-Everyday-Light"}   # plain wallpaper packages, one per theme
WALLPAPER_DIR = "/usr/share/wallpapers"
WALLPAPER_URL = "file://" + WALLPAPER_DIR + "/%s/"   # how Plasma stores a wallpaper package; a bare id does not resolve
FILL_MODE_CROP = "2"        # Image.PreserveAspectCrop: always covers the screen, never letterboxed
APPLETSRC = ".config/plasma-org.kde.plasma.desktop-appletsrc"
LOCKSCREEN = ("kscreenlockerrc", ("Greeter", "Wallpaper", "org.kde.image", "General"), "Image")
FIRST_LOGIN_MARK = ".local/state/heiss/theme-first-login"
FIRST_LOGIN_LNF = "org.heiss.dark.desktop"
TARGETS_ORDER = ("launcher-icon", "wallpaper", "konsole", "plasma-consistency", "gtk", "portal", "kitty")


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

    def kde_read_nested(self, file, groups, key):
        argv = ["kreadconfig6", "--file", file]
        for g in groups:
            argv += ["--group", g]
        rc, out = self._run(argv + ["--key", key])
        return out.rstrip("\n") if rc == 0 else None

    def kde_write(self, file, group, key, value):
        """`group` is one name or a tuple of nested group names."""
        groups = [group] if isinstance(group, str) else list(group)
        argv = ["kwriteconfig6", "--file", file]
        for g in groups:
            argv += ["--group", g]
        rc, _ = self._run(argv + ["--key", key, "--", value])
        return rc == 0

    def apply_lnf(self, package):
        return self._run(["plasma-apply-lookandfeel", "--apply", package], timeout=60)[0] == 0

    def unmark(self, path):
        try:
            os.unlink(path)
        except OSError:
            pass

    def touch(self, path):
        try:
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            with open(path, "a", encoding="utf-8"):
                pass
            return True
        except OSError:
            return False

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
            os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
            if os.path.exists(path) and os.path.getsize(path) > 200 * 1024:
                os.replace(path, path + ".1")
            with open(path, "a", encoding="utf-8") as f:
                f.write(time.strftime("%F %T ") + line + "\n")
        except OSError:
            pass   # stderr/journald still has the line

    def _private_dir(self, path):
        """True when `path` is a real directory owned by this user that no one else can write to."""
        try:
            st = os.lstat(path)
        except OSError:
            return False
        return stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o022

    def lock_dir(self):
        """A directory only this user controls: $XDG_RUNTIME_DIR, else the state directory. Never /tmp:
        another local user could plant the lock file (a symlink, or a file held locked forever) there."""
        run_dir = os.environ.get("XDG_RUNTIME_DIR", "")
        if os.path.isabs(run_dir) and self._private_dir(run_dir):
            return run_dir
        base = os.environ.get("XDG_STATE_HOME", "")
        if not os.path.isabs(base):
            base = os.path.join(self.home, ".local", "state")
        path = os.path.join(base, "heiss")
        try:
            os.makedirs(path, mode=0o700, exist_ok=True)
            st = os.lstat(path)
            if stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and st.st_mode & 0o022:
                os.chmod(path, 0o700)     # made earlier under a loose umask: tighten our own directory
        except OSError:
            return None
        return path if self._private_dir(path) else None

    @contextlib.contextmanager
    def lock(self):
        d = self.lock_dir()
        fd = None
        if d:
            try:
                fd = os.open(os.path.join(d, "heiss-theme-sync.lock"),
                             os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid():
                    os.close(fd)
                    fd = None
            except OSError:
                fd = None
        if fd is None:
            # no safe place for a lock: run without one (two syncs at once are harmless, a planted lock is not)
            self.append_log("no private directory for the lock file; running without a lock")
            yield True
            return
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


def _wallpaper_id(value):
    """`Heiss-Everyday`, `file:///usr/share/wallpapers/Heiss-Everyday/` and `/usr/share/wallpapers/Heiss-Everyday` are
    the same package; anything else is returned unchanged."""
    v = value.strip()
    if v.startswith("file://"):
        v = v[len("file://"):]
    if v.startswith(WALLPAPER_DIR + "/"):
        v = v[len(WALLPAPER_DIR) + 1:].strip("/")
    return v


def _desktop_images(text):
    """`Image=` values of the desktop wallpaper groups only (not another applet's picture)."""
    out, in_wall = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_wall = line.endswith("[Wallpaper][org.kde.image][General]")
        elif in_wall:
            m = re.fullmatch(r"Image\s*=\s*(.*)", line)
            if m and m.group(1).strip():
                out.append(m.group(1))
    return out


def target_wallpaper(env, theme, dry):
    """Desktop and lock-screen wallpaper follow the theme. A wallpaper the user chose is never replaced."""
    pid = WALLPAPER[theme]
    if not env.exists(os.path.join(WALLPAPER_DIR, pid)):
        return Result("wallpaper", "skipped", "wallpaper package %s is missing" % pid)
    ours = set(WALLPAPER.values())
    text = env.read_text(os.path.join(env.home, APPLETSRC)) or ""
    images = [_wallpaper_id(i) for i in _desktop_images(text)]
    lock_file, lock_groups, lock_key = LOCKSCREEN
    lock_now = env.kde_read_nested(lock_file, lock_groups, lock_key)
    lock_now = _wallpaper_id(lock_now) if lock_now else lock_now
    desktop_custom = any(i not in ours for i in images)
    lock_custom = lock_now not in (None, "") and lock_now not in ours
    changes = []
    if not desktop_custom and (not images or any(i != pid for i in images)):
        changes.append("desktop")
    if not lock_custom and lock_now != pid:
        changes.append("lock screen")
    custom = [n for n, c in (("desktop", desktop_custom), ("lock screen", lock_custom)) if c]
    note = " (custom %s wallpaper left alone)" % " and ".join(custom) if custom else ""
    if not changes:
        return Result("wallpaper", "skipped" if custom else "ok",
                      "custom wallpaper left alone" if custom else "%s already in place" % pid)
    if dry:
        return Result("wallpaper", "changed", "would set %s on the %s%s" % (pid, " and ".join(changes), note))
    if "desktop" in changes:
        script = """
for (var d of desktops()) {
  d.wallpaperPlugin = 'org.kde.image';
  d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
  d.writeConfig('Image', '%s');
  d.writeConfig('FillMode', %s);
}""" % (WALLPAPER_URL % pid, FILL_MODE_CROP)
        if not env.plasma_eval(script):
            return Result("wallpaper", "failed", "plasmashell did not accept the wallpaper script (is it running?)")
    if "lock screen" in changes and not env.kde_write(lock_file, lock_groups, lock_key, WALLPAPER_URL % pid):
        return Result("wallpaper", "failed", "could not write the lock screen wallpaper")
    return Result("wallpaper", "changed", "set %s on the %s%s" % (pid, " and ".join(changes), note))


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


TARGETS = (("launcher-icon", target_launcher), ("wallpaper", target_wallpaper), ("konsole", target_konsole),
           ("plasma-consistency", target_plasma_consistency), ("gtk", target_gtk),
           ("portal", target_portal), ("kitty", target_kitty))
assert tuple(n for n, _ in TARGETS) == TARGETS_ORDER


# ---------- driver ----------

def _first_login(env, scheme, out, sleep):
    """Once per user: a fresh account must start on Heiss Dark. System defaults (/etc/xdg/kdeglobals) normally do
    that; if the desktop still started on a Breeze scheme (Plasma's own default), apply Heiss Dark
    one time. The mark is written either way, so a theme the user picks later is never overridden. Returns the
    color scheme to continue with."""
    mark = os.path.join(env.home, FIRST_LOGIN_MARK)
    if env.exists(mark):
        return scheme
    if scheme not in THEME_OF and scheme.startswith("Breeze"):    # a custom scheme the user chose is never replaced
        if not env.touch(mark):
            # without the mark the switch would repeat at every login and override a later choice
            out.append(Result("first-login", "warn", "cannot write %s: not switching the theme" % mark))
            return scheme
        if env.apply_lnf(FIRST_LOGIN_LNF):
            sleep(2)    # the switch writes kdeglobals several times
            now = env.kde_read("kdeglobals", "General", "ColorScheme")
            out.append(Result("first-login", "changed", "started on color scheme %s, applied %s" % (scheme, FIRST_LOGIN_LNF)))
            scheme = now if now is not None else scheme
        else:
            out.append(Result("first-login", "failed", "started on color scheme %s and plasma-apply-lookandfeel could not apply %s"
                              % (scheme, FIRST_LOGIN_LNF)))
            env.unmark(mark)    # no mark: try again at the next login
            return scheme
    elif not env.touch(mark):
        pass                    # harmless: nothing was changed, the check repeats
    return scheme


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
        first = []
        if scheme is not None and not dry_run:
            scheme = _first_login(env, scheme, first, sleep)
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
        results = first + results
        for r in results:
            say(r.line())
    return results, (1 if any(r.status == "failed" for r in results) else 0)
