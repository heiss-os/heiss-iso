"""Switches the desktop theme as the user (no privileges, no shell) through `heiss theme`.

`heiss theme get` prints `dark` or `light`, `heiss theme set dark|light` switches GTK, Qt, kitty, Waybar, the
wallpaper and the cursor (implemented in heiss-core). Failures are returned, never raised.
"""
import subprocess

THEMES = ("dark", "light")
MAX_OUTPUT = 4096   # characters kept of a tool's output; the rest is never used


def read_current(run=subprocess.run):
    """'dark', 'light' or '' (unknown, or `heiss` missing)."""
    try:
        r = run(["heiss", "theme", "get"], capture_output=True, text=True, errors="replace", timeout=10)
        out = r.stdout[:MAX_OUTPUT].strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001 - a missing tool must not stop the page
        return ""
    return out if out in THEMES else ""


def apply_theme(theme, run=subprocess.run):
    """Return (ok, message); message is empty on success."""
    if theme not in THEMES:
        return False, "unknown theme"
    try:
        r = run(["heiss", "theme", "set", theme], capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return False, "cannot switch the theme: %s" % e
    if r.returncode != 0:
        text = (r.stderr or r.stdout or "")[-MAX_OUTPUT:]
        return False, (text.strip().splitlines() or ["theme switch failed"])[-1]
    return True, ""
