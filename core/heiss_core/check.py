"""`heiss check`: read-only health check of an INSTALLED Heiss system.

One line per item: OK, FAIL, or WARN where the situation cannot be judged (not a desktop
session, no root for /etc/shadow, tool missing). Nothing is changed on the system (the theme item takes the same short-lived lock file in the runtime directory as `heiss theme status`). Only fixed argument
lists are run, never a shell, and every command is recorded so `--report` can print it.
The environment is injected (CheckEnv) so tests run on fixtures without root.
"""
import os
import re
import subprocess

from . import manifest as mf
from . import state as st
from . import themesync
from .errors import HeissError

OK, WARN, FAIL = "OK", "WARN", "FAIL"

# The 37 packages removed from the ISO list in PR 49 (Cyber tools, rescue/imaging, legacy VPN/dial-up, storage tools).
REMOVED_PACKAGES = (
    "b43-fwcutter", "bcachefs-tools", "bind", "clonezilla", "ddrescue", "dnsmasq", "fsarchiver", "irssi",
    "jfsutils", "ldns", "lftp", "linux-atm", "lsscsi", "lynx", "mc", "mmc-utils", "ndisc6", "nilfs-utils",
    "nmap", "open-iscsi", "openconnect", "openpgp-card-tools", "openvpn", "partclone", "partimage",
    "pptpclient", "sdparm", "sequoia-sq", "sg3_utils", "testdisk", "tcpdump", "tpm2-tools", "usbmuxd",
    "vpnc", "wireless_tools", "wvdial", "xl2tpd",
)
# Hide stubs shipped in /usr/local/share/applications (docs/apps/LAUNCHER.md); calamares.desktop is removed after install.
HIDE_STUBS = ("org.kde.kwrite.desktop", "vim.desktop", "mpv.desktop", "assistant.desktop", "designer.desktop",
              "linguist.desktop", "qdbusviewer.desktop", "qv4l2.desktop", "qvidcap.desktop", "lstopo.desktop")
# desktop file -> key it must declare (docs/design/SHORTCUTS.md, rows marked "desktop")
SHORTCUT_FILES = {"org.kde.dolphin.desktop": "Meta+E", "org.kde.konsole.desktop": "Ctrl+Alt+T",
                  "systemsettings.desktop": "Meta+I", "org.kde.plasma-systemmonitor.desktop": "Meta+Esc"}
APP_DIRS = ("/usr/local/share/applications", "/usr/share/applications")
HELPER_FILES = ("/usr/share/polkit-1/actions/org.heiss.helper.policy",
                "/usr/share/dbus-1/system.d/org.heiss.Helper1.conf",
                "/usr/share/dbus-1/system-services/org.heiss.Helper1.service")
LIVE_PACKAGES = ("archiso", "mkinitcpio-archiso", "mkinitcpio-nfs-utils", "cloud-init", "livecd-sounds", "archinstall")
PROFILES_DIR = "/usr/share/heiss/profiles"
ETC_PROFILE = "/etc/heiss/profile.toml"
STATE_FILE = "/var/lib/heiss/state.json"


class CheckEnv:
    """Real system. `run` records every command in `self.commands`."""

    def __init__(self):
        self.commands = []

    def run(self, argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=30,
                               env={"LC_ALL": "C", "PATH": "/usr/bin:/bin",
                                    "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", "")})
            rc, out = r.returncode, r.stdout + r.stderr
        except (OSError, subprocess.TimeoutExpired):
            rc, out = 127, ""
        self.commands.append((list(argv), rc, out))
        return rc, out

    def read(self, path):
        """Text, or None when missing. PermissionError propagates."""
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, NotADirectoryError):
            return None

    def exists(self, path):
        return os.path.exists(path)

    def euid(self):
        return os.geteuid()

    def listdir(self, path):
        try:
            return sorted(os.listdir(path))
        except OSError:
            return []


class Item:
    def __init__(self, name, status, detail, commands=()):
        self.name, self.status, self.detail, self.commands = name, status, detail, list(commands)

    def line(self):
        return "%-4s  %-18s %s" % (self.status, self.name, self.detail)

    def to_dict(self):
        return {"name": self.name, "status": self.status, "detail": self.detail,
                "commands": [" ".join(c) for c in self.commands]}


def _cmds(env, start):
    return [c[0] for c in env.commands[start:]]


def _desktop_keys(text):
    out, in_main = {}, False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_main = line == "[Desktop Entry]"
        elif in_main and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out.setdefault(k, v)
    return out


# ---------- checks ----------

def check_units(env):
    n = len(env.commands)
    bad, notes = [], []
    for scope, argv in (("system", ["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"]),
                        ("user", ["systemctl", "--user", "--failed", "--no-legend", "--plain", "--no-pager"])):
        if scope == "user" and env.euid() == 0:
            notes.append("user units not checked as root (run without sudo)")
            continue
        rc, out = env.run(argv)
        if rc != 0:
            notes.append("%s manager unreachable" % scope)
            continue
        bad += ["%s:%s" % (scope, l.split()[0]) for l in out.splitlines() if l.split()]
    if bad:
        return Item("failed-units", FAIL, "failed: " + ", ".join(bad), _cmds(env, n))
    if notes:
        return Item("failed-units", WARN, "; ".join(notes) + " (cannot judge); no failed units in the other", _cmds(env, n))
    return Item("failed-units", OK, "no failed system or user units", _cmds(env, n))


def _load_state(env):
    text = env.read(STATE_FILE)
    return None if text is None else st.parse(text)


def check_profile(env, manifests):
    n = len(env.commands)
    try:
        state = _load_state(env)
    except HeissError as e:
        return Item("profile-state", FAIL, "state file is invalid: %s" % e), None
    if state is None:
        return Item("profile-state", WARN, "no %s: no profile applied yet (normal right after install)" % STATE_FILE), None
    profile = (state.get("applied") or {}).get("profile")
    problems = []
    if profile is not None and profile not in manifests:
        problems.append("applied profile %r has no manifest" % profile)
    for a in (state.get("applied") or {}).get("addons", []):
        if a not in manifests:
            problems.append("applied add-on %r has no manifest" % a)
    answers = env.read(ETC_PROFILE)
    if answers is not None:
        m = re.search(r'^\s*profile\s*=\s*"([^"]*)"', answers, re.M)
        if m and profile is not None and m.group(1) != profile:
            problems.append("%s says %r, state says %r" % (ETC_PROFILE, m.group(1), profile))
    rc, out = env.run(["pacman", "-Qq"])
    if rc == 0:
        missing = sorted(set(state["packages"]) - set(out.split()))
        if missing:
            problems.append("state lists packages that are not installed: " + ", ".join(missing[:8]))
    if problems:
        return Item("profile-state", FAIL, "; ".join(problems), _cmds(env, n)), state
    return Item("profile-state", OK, "profile %s, %d packages recorded and installed" % (profile or "none", len(state["packages"])),
                _cmds(env, n)), state


def check_theme(theme_env):
    results, _ = themesync.sync(theme_env, wait=False, dry_run=True)
    # theme-sync runs its own read-only commands (kreadconfig6, gsettings, busctl --user); they are not captured here
    cmds = [["heiss", "theme", "status"]]
    if len(results) == 1 and results[0].target == "all" and results[0].status == "skipped":
        return Item("theme-sync", WARN, "cannot judge: " + results[0].detail, cmds)
    if len(results) == 1 and results[0].target == "all" and results[0].status == "failed":
        return Item("theme-sync", WARN, "cannot judge: " + results[0].detail, cmds)
    bad = [r for r in results if r.status == "failed"]
    warn = [r for r in results if r.status == "warn"]
    if bad:
        return Item("theme-sync", FAIL, "; ".join("%s: %s" % (r.target, r.detail) for r in bad), cmds)
    if warn:
        return Item("theme-sync", WARN, "; ".join("%s: %s" % (r.target, r.detail) for r in warn), cmds)
    if all(r.status == "skipped" for r in results):
        return Item("theme-sync", WARN, "not a Heiss color scheme: %s" % results[0].detail, cmds)
    return Item("theme-sync", OK, ", ".join("%s %s" % (r.target, r.status) for r in results), cmds)


def check_launcher(env):
    problems, entries = [], {}
    for fname in HIDE_STUBS:
        text = env.read("/usr/local/share/applications/" + fname)
        if text is None:
            problems.append("hide stub %s is missing (entry visible again)" % fname)
            continue
        keys = _desktop_keys(text)
        if keys.get("Hidden") != "true" or keys.get("NoDisplay") != "true" or "Exec" in keys:
            problems.append("hide stub %s is malformed (needs Hidden=true, NoDisplay=true, no Exec)" % fname)
    for d in APP_DIRS:                                  # first directory wins per desktop id
        for fname in env.listdir(d):
            if fname.endswith(".desktop") and fname not in entries:
                text = env.read(os.path.join(d, fname))
                if text is not None:
                    entries[fname] = _desktop_keys(text)
    by_name = {}
    for fname, k in entries.items():
        if k.get("Type") != "Application" or k.get("NoDisplay") == "true" or k.get("Hidden") == "true":
            continue
        only, notin = k.get("OnlyShowIn"), k.get("NotShowIn")
        if (only and "KDE" not in only.split(";")) or (notin and "KDE" in notin.split(";")):
            continue
        if k.get("Name"):
            by_name.setdefault(k["Name"], []).append(fname)
    dups = {n: f for n, f in by_name.items() if len(f) > 1}
    if problems:
        return Item("launcher-menu", FAIL, "; ".join(problems))
    if dups:
        return Item("launcher-menu", WARN, "duplicate visible names: " + "; ".join("%s (%s)" % (n, ", ".join(sorted(f))) for n, f in sorted(dups.items())))
    return Item("launcher-menu", OK, "%d stubs hide their entries, no duplicate visible names (%d entries read)" % (len(HIDE_STUBS), len(entries)))


def check_removed(env, state, profile):
    n = len(env.commands)
    rc, out = env.run(["pacman", "-Qq"])
    if rc != 0:
        return Item("removed-packages", WARN, "pacman unavailable, cannot judge", _cmds(env, n))
    installed = set(out.split())
    owned = set(state["packages"]) if state else set()
    present = sorted(p for p in REMOVED_PACKAGES if p in installed)
    stray = [p for p in present if p not in owned]
    if not stray:
        extra = " (%d installed by a Heiss profile, expected)" % len(present) if present else ""
        return Item("removed-packages", OK, "none of the %d removed packages is present%s" % (len(REMOVED_PACKAGES), extra), _cmds(env, n))
    detail = "present: " + ", ".join(stray)
    # on a non-Base profile or with extra software the user may have installed them on purpose
    return Item("removed-packages", FAIL if profile in (None, "base") else WARN, detail, _cmds(env, n))


def check_shortcuts(env):
    problems = []
    for fname, key in SHORTCUT_FILES.items():
        text = env.read("/usr/share/applications/" + fname)
        if text is None:
            problems.append("%s missing" % fname)
        elif key not in _desktop_keys(text).get("X-KDE-Shortcuts", "").split(","):
            problems.append("%s does not declare %s" % (fname, key))
    if not env.exists("/usr/lib/qt6/plugins/kf6/parts/konsolepart.so"):
        problems.append("konsolepart.so missing: Dolphin terminal panel (Open Terminal Here) will not work")
    kg = env.read("/etc/xdg/kdeglobals") or ""
    m = re.search(r"^TerminalApplication\s*=\s*(\S+)", kg, re.M)
    if m and m.group(1) != "konsole":
        return Item("shortcuts-terminal", WARN if not problems else FAIL,
                    "; ".join(problems + ["system TerminalApplication is %s, not konsole" % m.group(1)]))
    if problems:
        return Item("shortcuts-terminal", FAIL, "; ".join(problems))
    return Item("shortcuts-terminal", OK, "%d shortcuts declared; Konsole terminal part present for Open Terminal Here" % len(SHORTCUT_FILES))


def check_helper(env):
    n = len(env.commands)
    missing = [p for p in HELPER_FILES if not env.exists(p)]
    if missing:
        return Item("helper", FAIL, "files not installed: " + ", ".join(missing), _cmds(env, n))
    rc, out = env.run(["busctl", "--system", "call", "org.heiss.Helper1", "/org/heiss/Helper1", "org.heiss.Helper1", "Ping"])
    if rc == 127:
        return Item("helper", WARN, "busctl missing, policy files are installed; D-Bus name not tested", _cmds(env, n))
    if rc != 0:
        return Item("helper", FAIL, "org.heiss.Helper1 not reachable: %s" % out.strip()[:120], _cmds(env, n))
    return Item("helper", OK, "org.heiss.Helper1 answers Ping (%s); polkit and D-Bus files installed" % out.strip(), _cmds(env, n))


def check_live(env):
    n = len(env.commands)
    if env.exists("/run/archiso"):
        return Item("live-leftovers", WARN, "this is the live session itself: check the installed system instead")
    problems = []
    passwd = env.read("/etc/passwd") or ""
    if any(l.split(":")[0] == "liveuser" for l in passwd.splitlines()):
        problems.append("user liveuser exists")
    rc, out = env.run(["pacman", "-Qq"])
    if rc == 0:
        left = [p for p in LIVE_PACKAGES if p in set(out.split())]
        if left:
            problems.append("live packages installed: " + ", ".join(left))
    note = ""
    try:
        shadow = env.read("/etc/shadow")
    except PermissionError:
        shadow = None
        note = "root lock not judged (run as root to read /etc/shadow)"
    if shadow is not None:
        root = [l.split(":") for l in shadow.splitlines() if l.startswith("root:")]
        if not root or not root[0][1].startswith(("!", "*")):
            problems.append("root password is not locked")
    elif not note:
        note = "root lock not judged (/etc/shadow not found)"
    if problems:
        return Item("live-leftovers", FAIL, "; ".join(problems), _cmds(env, n))
    if note:
        return Item("live-leftovers", WARN, "no liveuser, no live packages; " + note, _cmds(env, n))
    return Item("live-leftovers", OK, "no liveuser, no live packages, root locked", _cmds(env, n))


def run_checks(env, theme_env, profiles_dir=PROFILES_DIR):
    try:
        manifests = mf.load_dir(profiles_dir)
    except (OSError, HeissError):
        manifests = {}
    items = [check_units(env)]
    prof_item, state = check_profile(env, manifests)
    if not manifests:
        prof_item = Item(prof_item.name, FAIL,
                         "no manifests in %s (heiss-core installed?); " % profiles_dir + prof_item.detail, prof_item.commands)
    items.append(prof_item)
    if env.euid() == 0:
        items.append(Item("theme-sync", WARN, "not checked as root: it would read root's settings, run without sudo"))
    else:
        items.append(check_theme(theme_env))
    items.append(check_launcher(env))
    items.append(check_removed(env, state, (state.get("applied") or {}).get("profile") if state else None))
    items.append(check_shortcuts(env))
    items.append(check_helper(env))
    items.append(check_live(env))
    return items


def render(items):
    return "\n".join(i.line() for i in items) + "\n"


def render_report(items, env, header=""):
    out = ["heiss check report", header, "", render(items).rstrip("\n"), "", "Commands used per item (exact argument lists):"]
    for i in items:
        out.append("[%s] %s" % (i.status, i.name))
        out += ["  $ " + " ".join(c) for c in i.commands] or ["  (reads files only)"]
    out += ["", "Not captured below: the read-only commands run by the theme item (kreadconfig6, gsettings, busctl --user); see `heiss theme status`.",
            "", "Raw output of every command:"]
    for argv, rc, text in env.commands:
        out += ["$ " + " ".join(argv) + "    (exit %d)" % rc, text.rstrip("\n") or "(no output)", ""]
    return "\n".join(out) + "\n"


def exit_code(items):
    return 1 if any(i.status == FAIL for i in items) else 0
