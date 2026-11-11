"""Privacy levels (Standard, Enhanced, Maximum) as fixed data: one root drop-in and a few user-level KDE keys.

Pure data and a tiny planner. The helper takes the drop-in content from here (never from a client), exactly as
it takes manifest drop-ins from the installed manifests, so a client can only pick a level name.

What a level does today (everything else on the wizard's privacy screen is still "coming soon"):
- NetworkManager: the default for the MAC address a connection presents (`wifi.cloned-mac-address`,
  `ethernet.cloned-mac-address`; NetworkManager's own default is "preserve") and random MAC while scanning
  (`wifi.scan-rand-mac-address`, default yes). "stable" means a different but fixed address per network,
  "random" a new address at every connection (may break captive portals and MAC-based allow lists).
  A connection that sets its own value keeps it. NetworkManager reads the file when it starts or is reloaded.
- KDE screen locker (user's ~/.config/kscreenlockerrc, group Daemon): Autolock, Timeout (minutes), LockGrace
  (seconds after locking during which the screen unlocks without a password).
"""
from .errors import ValidationError

LEVELS = ("standard", "enhanced", "maximum")
NM_DROPIN = "/etc/NetworkManager/conf.d/80-heiss-privacy.conf"

# level -> (wifi cloned MAC, ethernet cloned MAC, lock timeout in minutes, grace in seconds)
_TABLE = {
    "standard": ("preserve", "preserve", "5", "5"),
    "enhanced": ("stable", "preserve", "3", "5"),
    "maximum": ("random", "stable", "1", "0"),
}


def _check(level):
    if level not in LEVELS:
        raise ValidationError("unknown privacy level %r" % (level,))
    return _TABLE[level]


def dropins(level):
    """[{"path", "content"}] written as root by the helper."""
    wifi, eth, _, _ = _check(level)
    content = ("# Written by Heiss OS (privacy level: %s). Rewritten when the level changes.\n"
               "[device]\nwifi.scan-rand-mac-address=yes\n\n"
               "[connection]\nwifi.cloned-mac-address=%s\nethernet.cloned-mac-address=%s\n") % (level, wifi, eth)
    return [{"path": NM_DROPIN, "content": content}]


def kde_settings(level):
    """User-level keys, written with kwriteconfig6 as the user."""
    _, _, timeout, grace = _check(level)
    return [{"file": "kscreenlockerrc", "group": "Daemon", "key": k, "value": v}
            for k, v in (("Autolock", "true"), ("Timeout", timeout), ("LockGrace", grace))]
