"""`heiss theme`: Heiss Dark and Heiss Light for the Hyprland session, applied as the user (no privileges, no shell).

The colours come from the design tokens (generated files in /usr/share/heiss/desktop/theme/<dark|light>/, package
heiss-theme). `set` copies them into the user's configuration and tells the running programs to reload:

  colors        Hyprland, Waybar, fuzzel and mako colour files in ~/.config/heiss/theme/
  wallpaper     the Heiss wallpaper of the theme (a wallpaper the user chose is left alone)
  gtk           ~/.config/gtk-3.0 and gtk-4.0: settings.ini and gtk.css (only files that carry the Heiss header)
  qt            qt6ct.conf and the colour scheme file (only a qt6ct.conf that carries the Heiss header)
  color-scheme  GSettings color-scheme (GTK 4 and libadwaita apps, the portal, and kitty through its *-theme.auto.conf)
  cursor        the cursor theme of the running Hyprland
  reload        Hyprland, Waybar, mako and the wallpaper process

`init` does the file part once, at the first login (before the compositor runs). Everything runs through an injected
environment so the tests need neither a session nor root. Only fixed argument lists are run, never a shell.
"""
import os
import subprocess
import tempfile
from dataclasses import dataclass

THEMES = ("dark", "light")
SRC_ROOT = "/usr/share/heiss/desktop/theme"
COLOR_FILES = ("hypr-colors.conf", "waybar-colors.css", "fuzzel.ini", "mako.conf")
WALLPAPERS = {"dark": "/usr/share/wallpapers/Heiss-Everyday/contents/images/3840x2160.png",
              "light": "/usr/share/wallpapers/Heiss-Everyday-Light/contents/images/3840x2160.png"}
COLOR_SCHEME = {"dark": "prefer-dark", "light": "prefer-light"}
CURSOR, CURSOR_SIZE, ICONS, FONT = "Adwaita", "24", "Adwaita", "Inter 10"
MARK = "# Heiss theme file: written by `heiss theme`, edit heiss-user.conf or remove this line to take over"
CSS_MARK = "/* Heiss theme file: written by `heiss theme`, remove this line to take over */"
TARGETS = ("colors", "wallpaper", "gtk", "qt", "color-scheme", "cursor", "reload")
# Programs the reload step talks to: fixed argument lists
RELOAD_COMMANDS = (("hyprctl", "reload"), ("makoctl", "reload"))


@dataclass
class Result:
    target: str
    status: str          # ok, changed, skipped, warn, failed
    detail: str

    def line(self):
        return "theme: %s: %s: %s" % (self.target, self.status, self.detail)


class RealEnv:
    def __init__(self, home=None, src_root=SRC_ROOT, environ=None):
        self.home = home or os.path.expanduser("~")
        self.src_root = src_root
        self.environ = os.environ if environ is None else environ

    def config(self, *parts):
        base = self.environ.get("XDG_CONFIG_HOME") or os.path.join(self.home, ".config")
        return os.path.join(base, *parts)

    def in_session(self):
        return bool(self.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))

    def read(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None

    def write(self, path, text):
        """Atomic: a reader never sees half a file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".heiss-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.chmod(tmp, 0o644)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def link_target(self, path):
        try:
            return os.readlink(path)
        except OSError:
            return None

    def set_link(self, path, target):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".heiss-tmp"
        try:
            os.unlink(tmp)
        except OSError:
            pass
        os.symlink(target, tmp)
        os.replace(tmp, path)

    def exists(self, path):
        return os.path.exists(path)

    def run(self, argv, timeout=10):
        try:
            r = subprocess.run(list(argv), capture_output=True, text=True, errors="replace", timeout=timeout,
                               env=dict(self.environ), stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout + r.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, str(e)

    def spawn(self, argv):
        try:
            subprocess.Popen(list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True, env=dict(self.environ))
            return True
        except OSError:
            return False

    def uid(self):
        return str(os.getuid())


def check_theme_name(theme):
    if theme not in THEMES:
        raise ValueError("unknown theme %r (dark or light)" % (theme,))
    return theme


def current_path(env):
    return env.config("heiss", "theme", "current")


def get(env):
    """'dark', 'light' or '' (never set, or not a Heiss theme)."""
    text = env.read(current_path(env))
    name = (text or "").strip()
    return name if name in THEMES else ""


# ---------- the targets ----------

def _src(env, theme, name):
    return os.path.join(env.src_root, theme, name)


def target_colors(env, theme, dry):
    changed, missing = [], []
    for name in COLOR_FILES:
        text = env.read(_src(env, theme, name))
        if text is None:
            missing.append(name)
            continue
        dest = env.config("heiss", "theme", name)
        if env.read(dest) != text:
            changed.append(name)
            if not dry:
                env.write(dest, text)
    if missing:
        return Result("colors", "failed", "theme files missing in %s: %s (package heiss-theme)" % (env.src_root, ", ".join(missing)))
    if not dry and get(env) != theme:
        env.write(current_path(env), theme + "\n")
    if changed:
        return Result("colors", "changed", ("would write " if dry else "wrote ") + ", ".join(changed))
    return Result("colors", "ok", "%s colour files already in place" % theme)


def target_wallpaper(env, theme, dry):
    link = env.config("heiss", "theme", "wallpaper")
    now = env.link_target(link)
    want = WALLPAPERS[theme]
    if now == want:
        return Result("wallpaper", "ok", "Heiss wallpaper of the %s theme in place" % theme)
    if now is not None and now not in WALLPAPERS.values():
        return Result("wallpaper", "skipped", "a wallpaper you chose (%s) is left alone" % now)
    if not env.exists(want):
        return Result("wallpaper", "skipped", "%s is not installed" % want)
    if not dry:
        env.set_link(link, want)
    return Result("wallpaper", "changed", ("would link " if dry else "linked ") + want)


def _ini_settings(theme):
    return "\n".join([MARK, "[Settings]",
                      "gtk-application-prefer-dark-theme=%d" % (1 if theme == "dark" else 0),
                      "gtk-icon-theme-name=%s" % ICONS, "gtk-cursor-theme-name=%s" % CURSOR,
                      "gtk-cursor-theme-size=%s" % CURSOR_SIZE, "gtk-font-name=%s" % FONT, ""])


def target_gtk(env, theme, dry):
    done, kept = [], []
    for ver in ("3.0", "4.0"):
        css = env.read(_src(env, theme, "gtk-%s.css" % ver))
        if css is None:
            return Result("gtk", "failed", "gtk-%s.css missing in %s (package heiss-theme)" % (ver, env.src_root))
        wanted = {env.config("gtk-%s" % ver, "settings.ini"): _ini_settings(theme),
                  env.config("gtk-%s" % ver, "gtk.css"): CSS_MARK + "\n" + css}
        for path, text in wanted.items():
            have = env.read(path)
            if have is not None and not have.startswith((MARK, CSS_MARK)):
                kept.append(os.path.relpath(path, env.config()))
                continue
            if have != text:
                done.append(os.path.relpath(path, env.config()))
                if not dry:
                    env.write(path, text)
    detail = ("would write " if dry else "wrote ") + ", ".join(done) if done else "GTK 3 and 4 files already in place"
    if kept:
        return Result("gtk", "warn", detail + "; left alone (not written by Heiss): " + ", ".join(kept))
    return Result("gtk", "changed" if done else "ok", detail)


def _qt6ct_conf(env):
    scheme = env.config("qt6ct", "colors", "heiss.conf")
    return "\n".join([MARK, "[Appearance]", "color_scheme_path=%s" % scheme, "custom_palette=true",
                      "standard_dialogs=default", "style=Fusion", "", "[Fonts]",
                      'fixed="JetBrains Mono,10,-1,5,50,0,0,0,0,0"', 'general="Inter,10,-1,5,50,0,0,0,0,0"', ""])


def target_qt(env, theme, dry):
    colors = env.read(_src(env, theme, "qt6ct-colors.conf"))
    if colors is None:
        return Result("qt", "failed", "qt6ct-colors.conf missing in %s (package heiss-theme)" % env.src_root)
    conf_path, colors_path = env.config("qt6ct", "qt6ct.conf"), env.config("qt6ct", "colors", "heiss.conf")
    have = env.read(conf_path)
    done, note = [], ""
    if have is not None and not have.startswith(MARK):
        note = "; qt6ct.conf is yours (not written by Heiss), only the colour file was updated"
    elif have != _qt6ct_conf(env):
        done.append("qt6ct.conf")
        if not dry:
            env.write(conf_path, _qt6ct_conf(env))
    if env.read(colors_path) != colors:
        done.append("colors/heiss.conf")
        if not dry:
            env.write(colors_path, colors)
    detail = (("would write " if dry else "wrote ") + ", ".join(done) if done else "qt6ct files already in place") + note
    detail += " (running Qt programs read it at their next start)" if done and not dry else ""
    return Result("qt", "warn" if note else ("changed" if done else "ok"), detail)


def target_color_scheme(env, theme, dry):
    want = COLOR_SCHEME[theme]
    rc, out = env.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
    if rc == 127:
        return Result("color-scheme", "skipped", "gsettings is not installed")
    if rc == 0 and out.strip("'") == want:
        return Result("color-scheme", "ok", "color-scheme is %s (kitty and GTK 4 follow it)" % want)
    if dry:
        return Result("color-scheme", "changed", "would set color-scheme to %s" % want)
    rc, out = env.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", want])
    if rc != 0:
        return Result("color-scheme", "failed", "gsettings set failed: %s" % out[:200])
    return Result("color-scheme", "changed", "color-scheme set to %s" % want)


def target_cursor(env, theme, dry, live):
    if not live:
        return Result("cursor", "skipped", "not in a running Hyprland session (the session sets %s)" % CURSOR)
    if dry:
        return Result("cursor", "ok", "would set %s %s" % (CURSOR, CURSOR_SIZE))
    rc, out = env.run(["hyprctl", "setcursor", CURSOR, CURSOR_SIZE])
    if rc != 0:
        return Result("cursor", "warn", "hyprctl setcursor failed: %s" % out[:200])
    return Result("cursor", "changed", "%s %s" % (CURSOR, CURSOR_SIZE))


def target_reload(env, dry, live):
    if not live:
        return Result("reload", "skipped", "not in a running Hyprland session; the programs read the files at their start")
    if dry:
        return Result("reload", "ok", "would reload Hyprland, Waybar, mako and the wallpaper")
    failed = []
    for argv in RELOAD_COMMANDS:
        rc, out = env.run(list(argv))
        if rc != 0:
            failed.append("%s (%s)" % (argv[0], out[:80] or "exit %d" % rc))
    env.run(["pkill", "-USR2", "-u", env.uid(), "-x", "waybar"])       # Waybar reloads style and config on SIGUSR2
    env.spawn(["heiss-wallpaper"])
    if failed:
        return Result("reload", "warn", "not reloaded: " + ", ".join(failed))
    return Result("reload", "changed", "Hyprland, Waybar, mako and the wallpaper reloaded")


# ---------- entry points ----------

def apply(env, theme, dry_run=False, live=None):
    """Run every target for `theme`. A crash in one target is reported and does not hide the others.
    Returns (results, exit_code); the exit code is 1 only when a target failed."""
    check_theme_name(theme)
    live = env.in_session() if live is None else live
    targets = (("colors", lambda: target_colors(env, theme, dry_run)),
               ("wallpaper", lambda: target_wallpaper(env, theme, dry_run)),
               ("gtk", lambda: target_gtk(env, theme, dry_run)),
               ("qt", lambda: target_qt(env, theme, dry_run)),
               ("color-scheme", lambda: target_color_scheme(env, theme, dry_run)),
               ("cursor", lambda: target_cursor(env, theme, dry_run, live)),
               ("reload", lambda: target_reload(env, dry_run, live)))
    results = []
    for name, fn in targets:
        try:
            results.append(fn())
        except Exception as e:  # noqa: BLE001 - one broken target must not hide the others
            results.append(Result(name, "failed", "%s: %s" % (type(e).__name__, e)))
    return results, (1 if any(r.status == "failed" for r in results) else 0)


def init(env):
    """First login: put the dark theme in place once (files and GSettings, no reload). Idempotent."""
    if get(env):
        return [Result("init", "ok", "theme already set (%s)" % get(env))], 0
    return apply(env, "dark", live=False)


def status(env):
    """Read-only: the current theme and what `set <current>` would change."""
    cur = get(env)
    if not cur:
        return [Result("theme", "warn", "no Heiss theme set yet (heiss theme set dark|light)")], 0
    results, rc = apply(env, cur, dry_run=True, live=False)
    out = [Result("theme", "ok", "current theme: %s" % cur)]
    for r in results:
        if r.target in ("cursor", "reload"):
            continue
        out.append(Result(r.target, "warn" if r.status == "changed" else r.status,
                          r.detail.replace("would write", "differs from the %s theme:" % cur) if r.status == "changed" else r.detail))
    return out, rc

