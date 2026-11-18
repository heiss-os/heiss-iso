"""What the welcome window shows. No Qt here: the QML only draws this.

The list of key bindings is read from the active Hyprland configuration by heiss_core.hyprcfg, never written here.
"""
import os

from heiss_core import hyprcfg

from .strings import S, t

_CANON = {"ALT": "Alt", "SUPER": "Super", "SHIFT": "Shift", "CTRL": "Ctrl", "CONTROL": "Ctrl", "RETURN": "Enter",
          "ENTER": "Enter", "PRINT": "Print", "SPACE": "Space", "TAB": "Tab", "ESCAPE": "Escape", "ESC": "Escape",
          "LEFT": "left", "RIGHT": "right", "UP": "up", "DOWN": "down"}


def key_label(lang, key):
    """One key of a combination as a person reads it: 'ALT' -> 'Alt', 'mouse:272' -> 'left mouse button'."""
    name = _CANON.get(key.upper(), key)
    if "key." + name in S["en"]:
        return t(lang, "key." + name)
    return name.upper() if len(name) == 1 else name


def combo_label(lang, keys):
    return " + ".join(key_label(lang, k) for k in keys)


def should_show(first_run, force, cfg_dir, live_marker="/run/archiso"):
    """--force always shows; --first-run only on an installed system and only once per user; plain start shows."""
    if force or not first_run:
        return True
    return not (os.path.exists(live_marker) or os.path.exists(os.path.join(cfg_dir, "heiss", "welcome-done")))


def mark_done(cfg_dir):
    d = os.path.join(cfg_dir, "heiss")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "welcome-done"), "a", encoding="utf-8"):
        pass


def screen(lang, cfg_dir, query=""):
    """The dict the window draws: texts, the main key line and one row per binding (filtered by `query`)."""
    cfg = hyprcfg.load(cfg_dir)
    mod = key_label(lang, cfg.main_mod)
    rows = []
    for b in cfg.bindings:
        keys = combo_label(lang, b.keys) if b.resolved else b.keys_text
        desc = b.description or t(lang, "undescribed" if b.resolved else "unresolved")
        rows.append({"keys": keys, "description": desc})
    q = query.strip().lower()
    shown = [r for r in rows if not q or q in r["keys"].lower() or q in r["description"].lower()]
    if cfg.error:
        empty = t(lang, "unreadable") % cfg.error
    elif not rows:
        empty = t(lang, "none")
    else:
        empty = t(lang, "nomatch") if not shown else ""
    return {
        "title": t(lang, "title"), "intro": t(lang, "intro"), "search": t(lang, "search"), "close": t(lang, "close"),
        "mainKey": t(lang, "mainkey") % mod,
        "mainKeyNote": t(lang, "mainkey_managed" if cfg.managed else "mainkey_own"),
        "rows": shown, "empty": empty,
    }
