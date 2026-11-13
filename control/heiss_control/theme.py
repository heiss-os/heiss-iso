"""Switches the desktop theme as the user (no privileges, no shell) with plasma-apply-lookandfeel.

Only Dark and Light exist as Heiss Global Themes; Plasma then applies colours, icons and style and the
theme-sync path unit does the rest. Failures are returned, never raised.
"""
import subprocess

from heiss_core.themesync import LNF_PACKAGE, THEME_OF


def read_current(kde_value):
    """'dark', 'light' or '' (another colour scheme, or kreadconfig6 missing)."""
    try:
        return THEME_OF.get((kde_value("kdeglobals", "General", "ColorScheme") or "").strip(), "")
    except Exception:  # noqa: BLE001 - a missing tool must not stop the page
        return ""


MAX_OUTPUT = 4096   # characters kept of a tool's output; the rest is never used


def kreadconfig(file, group, key, run=subprocess.run):
    r = run(["kreadconfig6", "--file", file, "--group", group, "--key", key], capture_output=True, text=True,
            errors="replace", timeout=5)
    return r.stdout[:MAX_OUTPUT].strip() if r.returncode == 0 else ""


def apply_theme(theme, run=subprocess.run):
    """Return (ok, message); message is empty on success."""
    if theme not in LNF_PACKAGE:
        return False, "unknown theme"
    try:
        r = run(["plasma-apply-lookandfeel", "--apply", LNF_PACKAGE[theme]], capture_output=True, text=True,
                errors="replace", timeout=60)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return False, "cannot switch the theme: %s" % e
    if r.returncode != 0:
        text = (r.stderr or r.stdout or "")[-MAX_OUTPUT:]
        return False, (text.strip().splitlines() or ["theme switch failed"])[-1]
    return True, ""
