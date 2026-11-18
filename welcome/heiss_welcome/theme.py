"""Applies the theme chosen in the wizard to the running desktop, as the user (no privileges, no shell).

`dark` and `light` run `heiss theme set <name>` (heiss-core). `auto` leaves the desktop as it is.
Failures are reported, never raised: a missing tool must not stop the wizard.
"""
import subprocess
import threading

THEMES = ("dark", "light")
_LOCK = threading.Lock()   # clicks in quick succession must not run two switches at once


def apply_theme(theme, run=subprocess.run):
    """Return (ok, message). message is empty on success and for 'auto' (nothing to do)."""
    if theme not in THEMES:
        return True, ""
    with _LOCK:
        try:
            r = run(["heiss", "theme", "set", theme], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, "cannot switch the theme: %s" % e
    if r.returncode != 0:
        return False, ((r.stderr or r.stdout or "").strip().splitlines() or ["theme switch failed"])[-1]
    return True, ""
