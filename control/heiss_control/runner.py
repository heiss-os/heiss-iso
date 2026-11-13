"""Runs one saved "apply profile" action by starting `heiss profile apply --yes` in a child process.

The command does the real work through the privileged helper (D-Bus and polkit: the system asks for the
password); this window only starts it and shows the step lines. The queue item was validated when it was saved
and again when it was read; the ids are checked once more here and passed in the `--option=value` form, so an id
can never be read as an option. No shell. The child runs isolated (`-I`), in `/`, without interpreter, loader, GIO and HEISS_* override variables. The same command as the wizard's apply (`heiss_welcome.applier`),
duplicated on purpose so the Control Center does not depend on the wizard package.
"""
import os
import re
import subprocess
import sys

from heiss_core import manifest as mf
from heiss_core.errors import HeissError

STEP_RE = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")   # printed by `heiss profile apply` before every helper call


# interpreter, loader, locale, GIO module and test-override variables: none of them is needed to reach the bus and
# the polkit agent, and HEISS_* would let the client-side plan read other manifests than the installed ones
DROP_PREFIXES = ("PYTHON", "LD_", "GCONV", "LOCPATH", "NLSPATH", "GIO_", "GI_", "G_", "GSETTINGS_", "HEISS_")
# the child imports gi (helper client): GI_TYPELIB_PATH names libraries to load; the system bus address must stay the real one
DROP_NAMES = ("DBUS_SYSTEM_BUS_ADDRESS",)


def clean_env(environ):
    """The environment of the child: the user's session (it needs the bus and the display for the polkit agent)
    without anything that changes which code Python or the loader runs."""
    return {k: v for k, v in environ.items() if not k.startswith(DROP_PREFIXES) and k not in DROP_NAMES}


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
