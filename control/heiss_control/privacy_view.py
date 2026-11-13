"""Read-only facts for the Network and privacy page: what is in place now, compared with the chosen level.

Reads the NetworkManager drop-in the privacy level writes (`heiss_core.privacy.NM_DROPIN`, root-owned, world
readable), the user's screen-lock keys with `kreadconfig6` (fixed argument list, `--default` set to KDE's own
defaults so an unset key reads as the default) and the firewall state (`systemctl`, as the Security Center does).
Nothing is changed. Data only: `{"id", "status", "code", "data"}`; the model turns it into text.
"""
import re
import subprocess

from heiss_core import privacy as pv

from . import security

MAX_FILE = 65536
# codes per fact, for the completeness test of the strings
CODES = {
    "level": ("standard", "enhanced", "maximum", "unset"),
    "wifi_mac": ("preserve", "stable", "random", "other", "unknown"),
    "lock": ("on", "off", "unknown"),
    "firewall": ("active_enabled", "active_not_enabled", "inactive", "unknown"),
}
KDE_DEFAULTS = (("Autolock", "true"), ("Timeout", "5"), ("LockGrace", "5"))   # kscreenlocker's own defaults


class RealSystem(security.RealSystem):
    def read_text(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read(MAX_FILE)
        except OSError:
            return None

    def kde_value(self, key, default):
        rc, out = self.run(["kreadconfig6", "--file", "kscreenlockerrc", "--group", "Daemon", "--key", key,
                            "--default", default])
        return out.strip() if rc == 0 else None


def _item(item_id, status, code, data=""):
    return {"id": item_id, "status": status, "code": code, "data": data}


def level(chosen):
    return _item("level", "info", chosen if chosen in pv.LEVELS else "unset")


def wifi_mac(sh, chosen):
    text = sh.read_text(pv.NM_DROPIN)
    if text is None:
        value = "preserve"                     # no drop-in: NetworkManager's own default
    else:
        m = re.search(r"^\s*wifi\.cloned-mac-address\s*=\s*(\S+)\s*$", text, re.M)
        value = m.group(1) if m else "preserve"
    code = value if value in ("preserve", "stable", "random") else "other"
    if chosen not in pv.LEVELS:
        return _item("wifi_mac", "info", code, value if code == "other" else "")
    return _item("wifi_mac", "ok" if value == pv._TABLE[chosen][0] else "warn", code, value if code == "other" else "")


def lock(sh, chosen):
    vals = {k: sh.kde_value(k, d) for k, d in KDE_DEFAULTS}
    if any(v is None for v in vals.values()):
        return _item("lock", "info", "unknown")
    if vals["Autolock"] != "true":
        return _item("lock", "warn" if chosen in pv.LEVELS else "info", "off")
    minutes = vals["Timeout"] if vals["Timeout"].isdigit() else "?"
    status = "info"
    if chosen in pv.LEVELS:
        want = pv._TABLE[chosen]
        status = "ok" if (vals["Timeout"], vals["LockGrace"]) == (want[2], want[3]) else "warn"
    return _item("lock", status, "on", minutes)


def firewall(sh, chosen):
    f = security.firewall(sh)
    return _item("firewall", f["status"], f["code"])


CHECKS = (("level", lambda sh, c: level(c)), ("wifi_mac", wifi_mac), ("lock", lock), ("firewall", firewall))


def collect(chosen=None, sh=None):
    sh = sh or RealSystem()
    out = []
    for item_id, fn in CHECKS:
        try:
            out.append(fn(sh, chosen))
        except Exception:  # noqa: BLE001 - one broken fact must not hide the others
            out.append(_item(item_id, "info", "unknown"))
    return out
