"""Applies the chosen profile by running `heiss profile apply` in a child process.

The command does the real work through the privileged helper (D-Bus + polkit); the wizard only starts it
and shows its output. A child process keeps GLib and D-Bus out of the Qt process and the window responsive.
Qt-free, so it is tested with a fake command. There is no cancel: the helper job keeps running on the system
bus even if the client dies (a Phase 3 follow-up).
"""
import json
import re
import subprocess
import sys

from heiss_core.errors import HeissError

STEP_RE = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")   # printed by `heiss profile apply` before every helper call
PLAN_TIMEOUT_S = 120


class CliApplier:
    def __init__(self, argv=None):
        self.argv = list(argv or [sys.executable, "-m", "heiss_core"])

    @staticmethod
    def _selection(answers, hardware=()):
        args = ["--adopt", "--profile=%s" % answers["profile"]]   # "=" form: an id can never be read as an option
        args += ["--addon=%s" % a for a in answers["addons"]]
        args += ["--hardware=%s" % h for h in hardware]
        level = answers.get("privacy", {}).get("level")   # a validated answer; complete answers always have it
        if level:
            args.append("--privacy=%s" % level)
        return args

    def plan(self, answers, hardware=()):
        """Read-only: the resolver plan as a dict (`profile apply --dry-run`). Raises HeissError."""
        argv = self.argv + ["--json", "profile", "apply", "--dry-run"] + self._selection(answers, hardware)
        try:
            r = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=PLAN_TIMEOUT_S)
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
                                 bufsize=1)
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
