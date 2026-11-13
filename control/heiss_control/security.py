"""Read-only security facts for the Security Center page. No privileges, no helper, nothing is changed.

Every command is a literal argument list run with a fixed PATH (no shell, no value from a file reaches a command
line, except the device name `findmnt` prints, which is passed to `lsblk` as one argument after a `--`). The result
is data only: `{"id", "status", "code", "data"}` with status ok, warn or info; the model turns it into text.
"""
import os
import re
import subprocess

SECURE_BOOT_VAR = "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
MAX_PORTS = 20


class RealSystem:
    def run(self, argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=10, env=ENV)
            return r.returncode, (r.stdout or "")[:65536]
        except (OSError, subprocess.TimeoutExpired):
            return 127, ""

    def read_bytes(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(16)
        except OSError:
            return None

    def exists(self, path):
        return os.path.exists(path)


def _item(item_id, status, code, data=""):
    return {"id": item_id, "status": status, "code": code, "data": data}


def firewall(sh):
    rc, out = sh.run(["systemctl", "is-active", "firewalld"])
    if rc == 127:
        return _item("firewall", "info", "unknown")
    if out.strip() != "active":
        return _item("firewall", "warn", "inactive")
    rc, out = sh.run(["systemctl", "is-enabled", "firewalld"])
    return _item("firewall", "ok", "active_enabled") if out.strip() == "enabled" else _item("firewall", "warn", "active_not_enabled")


def ssh(sh):
    rc, out = sh.run(["systemctl", "is-active", "sshd"])
    if rc == 127:
        return _item("ssh", "info", "unknown")
    return _item("ssh", "warn", "on") if out.strip() == "active" else _item("ssh", "ok", "off")


def disk_encryption(sh):
    rc, out = sh.run(["findmnt", "-n", "-o", "SOURCE", "/"])
    source = re.sub(r"\[.*\]$", "", out.strip().splitlines()[0]) if rc == 0 and out.strip() else ""
    if not source.startswith("/dev/"):
        return _item("disk", "info", "unknown")
    rc, out = sh.run(["lsblk", "-s", "-r", "-n", "-o", "TYPE", "--", source])
    if rc != 0:
        return _item("disk", "info", "unknown")
    return _item("disk", "ok", "encrypted") if "crypt" in out.split() else _item("disk", "warn", "plain")


def secure_boot(sh):
    if not sh.exists("/sys/firmware/efi"):
        return _item("secure_boot", "info", "bios")
    raw = sh.read_bytes(SECURE_BOOT_VAR)
    if not raw or len(raw) < 5:
        return _item("secure_boot", "info", "unknown")
    return _item("secure_boot", "ok", "enabled") if raw[4] == 1 else _item("secure_boot", "info", "disabled")


def listening(sh):
    rc, out = sh.run(["ss", "-H", "-l", "-t", "-n"])
    if rc != 0:
        return _item("listening", "info", "unknown")
    ports = set()
    for line in out.splitlines():
        cols = line.split()
        if len(cols) < 4:
            continue
        addr, _, port = cols[3].rpartition(":")
        if addr.startswith("127.") or addr == "[::1]" or not port.isdigit():
            continue
        ports.add(int(port))
    if not ports:
        return _item("listening", "ok", "none")
    shown = sorted(ports)[:MAX_PORTS]
    return _item("listening", "warn", "some", ", ".join(map(str, shown)) + (" ..." if len(ports) > MAX_PORTS else ""))


CHECKS = (("firewall", firewall), ("disk", disk_encryption), ("secure_boot", secure_boot), ("ssh", ssh),
          ("listening", listening))


def collect(sh=None):
    sh = sh or RealSystem()
    out = []
    for item_id, fn in CHECKS:
        try:
            out.append(fn(sh))
        except Exception:  # noqa: BLE001 - one broken fact must not hide the others
            out.append(_item(item_id, "info", "unknown"))
    return out
