"""Read-only facts for the Updates and snapshots page. No privileges, no helper, no network, nothing is changed.

Four facts: updates waiting (`pacman -Qu`, which reads the local package database and does not go online, so it
reflects the last refresh), when the last full system upgrade ran (tail of the pacman log), whether the running
kernel is still installed on disk (a restart is needed if not) and whether snapshots are set up (root file system
and the snapper configuration; listing snapshots needs root, so they are not counted). Data only:
`{"id", "status", "code", "data"}`; the model turns it into text.
"""
import datetime
import os
import re

from . import security

PACMAN_LOG = "/var/log/pacman.log"
PACMAN_LOCK = "/var/lib/pacman/db.lck"
SNAPPER_ROOT = "/etc/snapper/configs/root"
MAX_LOG = 262144
OLD_DAYS = 30
CODES = {
    "pending": ("none", "some", "unknown"),
    "last": ("recent", "old", "never", "unknown"),
    "reboot": ("no", "yes", "unknown"),
    "snapshots": ("ready", "not_btrfs", "btrfs_no_snapper", "unknown"),
}
_UPGRADE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})T[^\]]*\] \[PACMAN\] starting full system upgrade", re.M)
_FSTYPE = re.compile(r"^[A-Za-z0-9._-]{1,20}$")


class RealSystem(security.RealSystem):
    def read_tail(self, path):
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                start = max(0, f.tell() - MAX_LOG)
                f.seek(start)
                return f.read().decode("utf-8", errors="replace"), start > 0   # (text, the start was cut off)
        except OSError:
            return None

    def today(self):
        return datetime.date.today()

    def kernel_release(self):
        return os.uname().release


def _item(item_id, status, code, data=""):
    return {"id": item_id, "status": status, "code": code, "data": data}


def pending(sh):
    rc, out = sh.run(["pacman", "-Qu"])
    if rc == 127:
        return _item("pending", "info", "unknown")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if rc == 0 and lines:
        return _item("pending", "warn", "some", str(len(lines)))
    if rc == 1 and sh.exists(PACMAN_LOCK):   # pacman also exits 1 on errors; a held lock is the common one
        return _item("pending", "info", "unknown")
    return _item("pending", "ok", "none") if rc in (0, 1) else _item("pending", "info", "unknown")


def last_upgrade(sh):
    tail = sh.read_tail(PACMAN_LOG)
    if tail is None:
        return _item("last", "info", "unknown")
    text, cut = tail
    dates = _UPGRADE.findall(text)
    if not dates:
        return _item("last", "info", "unknown" if cut else "never")   # a cut log may hide the line
    try:
        day = datetime.date.fromisoformat(dates[-1])
    except ValueError:
        return _item("last", "info", "unknown")
    age = (sh.today() - day).days
    if age < 0:   # clock skew or a forged line: do not call it recent
        return _item("last", "info", "unknown")
    return _item("last", "warn" if age > OLD_DAYS else "ok", "old" if age > OLD_DAYS else "recent", day.isoformat())


def reboot(sh):
    release = sh.kernel_release()
    if not release or "/" in release:
        return _item("reboot", "info", "unknown")
    return _item("reboot", "ok", "no") if sh.exists("/usr/lib/modules/" + release) else _item("reboot", "warn", "yes")


def snapshots(sh):
    rc, out = sh.run(["findmnt", "-n", "-o", "FSTYPE", "/"])
    fstype = out.strip().splitlines()[0].strip() if rc == 0 and out.strip() else ""
    if not _FSTYPE.fullmatch(fstype):
        return _item("snapshots", "info", "unknown")
    if fstype != "btrfs":
        return _item("snapshots", "info", "not_btrfs", fstype)
    return _item("snapshots", "ok", "ready") if sh.exists(SNAPPER_ROOT) else _item("snapshots", "info", "btrfs_no_snapper")


CHECKS = (("pending", pending), ("last", last_upgrade), ("reboot", reboot), ("snapshots", snapshots))


def collect(sh=None):
    sh = sh or RealSystem()
    out = []
    for item_id, fn in CHECKS:
        try:
            out.append(fn(sh))
        except Exception:  # noqa: BLE001 - one broken fact must not hide the others
            out.append(_item(item_id, "info", "unknown"))
    return out
