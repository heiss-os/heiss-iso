"""Applies the theme chosen in the wizard to the running desktop, as the user (no privileges, no shell).

`dark` and `light` switch the Heiss Global Theme with plasma-apply-lookandfeel (plasma-workspace); Plasma then
applies colors, icons and style, and the theme-sync path unit takes care of the rest. `auto` leaves the desktop as
it is: Plasma's own automatic switching is not configured here. Failures are reported, never raised: a missing
tool must not stop the wizard.
"""
import subprocess
import threading

LNF = {"dark": "org.heiss.dark.desktop", "light": "org.heiss.light.desktop"}
_LOCK = threading.Lock()   # clicks in quick succession must not run two switches at once


def apply_theme(theme, run=subprocess.run):
    """Return (ok, message). message is empty on success and for 'auto' (nothing to do)."""
    if theme not in LNF:
        return True, ""
    with _LOCK:
        try:
            r = run(["plasma-apply-lookandfeel", "--apply", LNF[theme]], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, "cannot switch the theme: %s" % e
    if r.returncode != 0:
        return False, ((r.stderr or r.stdout or "").strip().splitlines() or ["theme switch failed"])[-1]
    return True, ""
