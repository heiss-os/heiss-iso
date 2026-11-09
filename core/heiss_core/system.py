"""Read-only view of the running system (pacman, systemd, flatpak).

Only fixed argument lists are executed, never a shell. Tests use FakeSystem.
"""
import re
import subprocess


def _run(args):
    """(returncode, stdout). A missing command (for example flatpak or nmcli on a minimal system)
    is reported as returncode 127 instead of raising."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120,
                           env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"})
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return r.returncode, r.stdout


class PacmanSystem:
    def installed_packages(self):
        rc, out = _run(["pacman", "-Qq"])
        return set(out.split()) if rc == 0 else set()

    def explicit_packages(self):
        rc, out = _run(["pacman", "-Qeq"])
        return set(out.split()) if rc == 0 else set()

    def required_by(self, pkg):
        rc, out = _run(["pacman", "-Qi", pkg])
        if rc != 0:
            return set()
        m = re.search(r"^Required By\s*:\s*(.*)$", out, re.M)
        if not m or m.group(1).strip() == "None":
            return set()
        return {re.split(r"[<>=]", x)[0] for x in m.group(1).split()}

    def enabled_services(self):
        rc, out = _run(["systemctl", "list-unit-files", "--state=enabled", "--no-legend", "--no-pager"])
        return {l.split()[0] for l in out.splitlines() if l.split()} if rc == 0 else set()

    def installed_flatpaks(self):
        rc, out = _run(["flatpak", "list", "--app", "--columns=application"])
        return set(out.split()) if rc == 0 else set()

    def read_text(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def kde_value(self, file, group, key):
        rc, out = _run(["kreadconfig6", "--file", file, "--group", group, "--key", key])
        return out.rstrip("\n") if rc == 0 else None

    def network_connected(self):
        """True when NetworkManager reports full connectivity. Unknown (no nmcli) counts as connected:
        pacman will report a real failure. Does not probe the network itself."""
        rc, out = _run(["nmcli", "-t", "-f", "STATE", "general"])
        if rc != 0:
            return True
        return out.strip() == "connected"
