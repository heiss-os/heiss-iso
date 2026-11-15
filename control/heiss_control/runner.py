"""Runs one saved "apply profile" action by starting `heiss profile apply --yes` in a child process.

The command does the real work through the privileged helper (D-Bus and polkit: the system asks for the
password); this window only starts it and shows the step lines. The queue item was validated when it was saved
and again when it was read; the ids are checked once more here and passed in the `--option=value` form, so an id
can never be read as an option. No shell. The child runs isolated (`-I`), in `/`, with an allowlisted environment and a fixed PATH. The same command as the wizard's apply (`heiss_welcome.applier`),
duplicated on purpose so the Control Center does not depend on the wizard package.
"""
import os
import re
import subprocess
import sys

from heiss_core import manifest as mf
from heiss_core.errors import HeissError

STEP_RE = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")   # printed by `heiss profile apply` before every helper call


# The child ends up calling the privileged helper, and polkit keeps the authorisation per calling process (see
# DECISIONS.md). So it gets an ALLOWLIST: only what a session program needs (home, locale, the session bus and the
# display for the polkit agent) and a fixed PATH; nothing that changes which code Python or the loader runs
# (PYTHON*, LD_*, GI_*, GIO_*, ...), nothing from HEISS_*, and no variable that will be invented later.
# The same list in heiss_welcome.applier, duplicated on purpose (tests keep the two equal).
ALLOW_NAMES = ("HOME", "USER", "LOGNAME", "LANG", "LANGUAGE", "TZ", "TERM",
               "XDG_RUNTIME_DIR", "XDG_SESSION_ID", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP",
               "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
               "DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY")
ALLOW_PREFIXES = ("LC_",)
FIXED_PATH = "/usr/bin:/bin"   # not the user's PATH: the child runs pacman, systemctl and flatpak by name


LOCALE_VALUE = re.compile(r"[A-Za-z0-9_.@:-]{1,100}")   # glibc reads a locale name containing "/" as a file path


def clean_env(environ):
    env = {}
    for k, v in environ.items():
        if k in ALLOW_NAMES or k.startswith(ALLOW_PREFIXES):
            if (k in ("LANG", "LANGUAGE") or k.startswith("LC_")) and not LOCALE_VALUE.fullmatch(v):
                continue
            env[k] = v
    env["PATH"] = FIXED_PATH
    return env


def argv_for(item, base=None):
    payload = item.get("payload", {}) if isinstance(item, dict) else {}
    ids = [payload.get("profile")] + list(payload.get("addons", []))
    if item.get("kind") != "apply-profile" or not all(isinstance(i, str) and mf.ID_RE.fullmatch(i) for i in ids):
        raise HeissError("this saved action is not valid")
    argv = list(base or [sys.executable, "-I", "-m", "heiss_core"]) + ["profile", "apply", "--yes", "--adopt",
                                                                  "--profile=%s" % payload["profile"]]
    return argv + ["--addon=%s" % a for a in payload["addons"]]


def run_item(item, on_step=None, base=None, popen=subprocess.Popen, environ=None):
    """Apply one saved action. on_step(n, total, description) for each helper call. Raises HeissError."""
    argv = argv_for(item, base)
    try:
        # -I: no user site, no PYTHON* variables, no current directory on sys.path; cwd "/": nothing of the user's
        # is next to the interpreter that then calls the helper (whose polkit authorisation is kept per process)
        p = popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1,
                  cwd="/", env=clean_env(os.environ if environ is None else environ))
    except OSError as e:
        raise HeissError("cannot start the apply command: %s" % e)
    tail = []
    with p:
        for raw in p.stdout:
            line = raw.rstrip("\n")
            m = STEP_RE.match(line)
            if m and on_step:
                try:                      # a broken callback must not abandon the pipe and the running command
                    on_step(int(m.group(1)), int(m.group(2)), m.group(3))
                except Exception:  # noqa: BLE001
                    pass
            tail.append(line)
            del tail[:-20]
    if p.returncode != 0:
        raise HeissError(_last_message("\n".join(tail)))


def _last_message(text):
    """The error of the command: its last 'heiss: ...' line, else the last non-empty line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in reversed(lines):
        if l.startswith("heiss: "):
            return l[len("heiss: "):]
    return lines[-1] if lines else "the apply command failed without a message"
