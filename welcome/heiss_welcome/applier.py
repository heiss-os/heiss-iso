"""Applies the chosen profile by running `heiss profile apply` in a child process.

The command does the real work through the privileged helper (D-Bus + polkit); the wizard only starts it
and shows its output. A child process keeps GLib and D-Bus out of the Qt process and the window responsive.
The child runs isolated (python -I, cwd "/", an allowlisted environment and a fixed PATH).
Qt-free, so it is tested with a fake command. There is no cancel: the helper job keeps running on the system
bus even if the client dies (a Phase 3 follow-up).
"""
import json
import os
import re
import subprocess
import sys

from heiss_core.errors import HeissError

# The child ends up calling the privileged helper, and polkit keeps the authorisation per calling process (see
# DECISIONS.md). So it gets an ALLOWLIST: only what a session program needs (home, locale, the session bus and the
# display for the polkit agent) and a fixed PATH; nothing that changes which code Python or the loader runs
# (PYTHON*, LD_*, GI_*, GIO_*, ...), nothing from HEISS_*, and no variable that will be invented later.
# The same list in heiss_control.runner, duplicated on purpose (tests keep the two equal).
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


STEP_RE = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")   # printed by `heiss profile apply` before every helper call
PLAN_TIMEOUT_S = 120


class CliApplier:
    def __init__(self, argv=None):
        # -I: no user site, no PYTHON* variables, no current directory on sys.path (heiss_core is installed)
        self.argv = list(argv or [sys.executable, "-I", "-m", "heiss_core"])

    @staticmethod
    def _selection(answers, hardware=()):
        args = ["--adopt", "--profile=%s" % answers["profile"]]   # "=" form: an id can never be read as an option
        args += ["--addon=%s" % a for a in answers["addons"]]
        args += ["--hardware=%s" % h for h in hardware]
        # the wizard passes only profiles the user ticked and, when they need it, confirmed on the hardware screen
        args += ["--confirm-hardware=%s" % h for h in hardware]
        level = answers.get("privacy", {}).get("level")   # a validated answer; complete answers always have it
        if level:
            args.append("--privacy=%s" % level)
        return args

    def plan(self, answers, hardware=()):
        """Read-only: the resolver plan as a dict (`profile apply --dry-run`). Raises HeissError."""
        argv = self.argv + ["--json", "profile", "apply", "--dry-run"] + self._selection(answers, hardware)
        try:
            r = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=PLAN_TIMEOUT_S,
                               cwd="/", env=clean_env(os.environ))
        except (OSError, subprocess.TimeoutExpired) as e:
            raise HeissError("cannot compute the plan: %s" % e)
        if r.returncode != 0:
            raise HeissError(_last_message(r.stderr))
        try:
            return json.loads(r.stdout)
        except ValueError:
            raise HeissError("the plan is not readable")

    def run(self, answers, on_line, on_step, hardware=()):
        """Apply. on_line(text) for helper output, on_step(n, total, description) for each helper call."""
        argv = self.argv + ["profile", "apply", "--yes"] + self._selection(answers, hardware)
        try:
            p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                                 bufsize=1, cwd="/", env=clean_env(os.environ))
        except OSError as e:
            raise HeissError("cannot start the apply command: %s" % e)
        tail = []
        with p:
            for raw in p.stdout:
                line = raw.rstrip("\n")
                m = STEP_RE.match(line)
                try:                      # a broken callback must not abandon the pipe and the running command
                    if m:
                        on_step(int(m.group(1)), int(m.group(2)), m.group(3))
                    else:
                        on_line(line)
                except Exception:
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
