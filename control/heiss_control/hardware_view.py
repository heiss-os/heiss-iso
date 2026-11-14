"""Read-only data for the Hardware and drivers page and the driver doctor report.

Uses the detection of `heiss_core.hardware` (lspci, /sys, systemd-detect-virt: read-only) and `pacman -Qq` to see
which packages of each matching hardware profile are installed. Nothing is changed. Data only; the model turns
codes into text. The report is plain text without personal data: no hostname, user name, serial numbers, PCI slot
addresses, MAC addresses or DMI vendor and product strings; only PCI vendor:device ids, the form factor, the CPU
vendor, the virtualization type, the kernel release and the state of each driver proposal.
"""
import os
import re

from heiss_core import hardware as hw
from heiss_core.system import PacmanSystem

HARDWARE_DIR = os.environ.get("HEISS_HARDWARE", "/usr/share/heiss/hardware")
VENDORS = {"8086": "Intel", "1002": "AMD", "10de": "NVIDIA", "80ee": "VirtualBox", "15ad": "VMware",
           "1af4": "Virtio", "1234": "QEMU", "1414": "Microsoft"}
CPUS = {"GenuineIntel": "intel", "AuthenticAMD": "amd"}
CODES = {
    "form": ("laptop", "desktop", "vm"),
    "cpu": ("intel", "amd", "other"),
    "gpu": ("some", "none"),
    "hybrid": ("yes",),
    "bluetooth": ("yes", "no"),
}
_KERNEL = re.compile(r"^[0-9A-Za-z.+_-]{1,40}$")
DRIVER_STATES = ("installed", "missing", "nothing", "unknown")   # per proposal


def _item(item_id, status, code, data=""):
    return {"id": item_id, "status": status, "code": code, "data": data}


def vendor_name(vendor_id):
    return VENDORS.get(vendor_id, "vendor " + vendor_id)


def facts_of(report, has_bluetooth):
    out = [_item("form", "info", report.form_factor, report.virt if report.form_factor == "vm" else ""),
           _item("cpu", "info", CPUS.get(report.cpu_vendor, "other"))]
    if report.gpus:
        out.append(_item("gpu", "info", "some", ", ".join("%s (%s:%s)" % (vendor_name(g["vendor"]), g["vendor"], g["device"])
                                                          for g in report.gpus)))
    else:
        out.append(_item("gpu", "info", "none"))
    if report.hybrid_graphics:
        out.append(_item("hybrid", "info", "yes"))
    out.append(_item("bluetooth", "info", "yes" if has_bluetooth else "no"))
    return out


def driver_state(profile, installed):
    if not installed:                       # pacman could not be asked: do not claim anything
        return "unknown"
    if not profile.packages:
        return "nothing"
    return "installed" if all(p in installed for p in profile.packages) else "missing"


def drivers_of(report, installed):
    return [{"id": p.id, "name": dict(p.name), "description": dict(p.description), "warning": dict(p.warnings),
             "safe": p.safe_by_default, "state": driver_state(p, installed),
             "missing": [x for x in p.packages if installed and x not in installed]} for p in report.proposals]


def report_text(report, drivers, has_bluetooth, kernel):
    # a custom kernel's local version string or an odd CPU vendor string could carry a name: only known shapes go in
    kernel = kernel if _KERNEL.match(kernel or "") else "other"
    lines = ["Heiss OS hardware report (no personal data: no hostname, serial numbers, addresses or user names)",
             "kernel: %s" % kernel, "form factor: %s" % report.form_factor, "cpu vendor: %s" % (CPUS.get(report.cpu_vendor, "other")),
             "virtualization: %s" % report.virt, "bluetooth: %s" % ("yes" if has_bluetooth else "no")]
    for g in report.gpus:
        lines.append("gpu: %s:%s" % (g["vendor"], g["device"]))
    if report.hybrid_graphics:
        lines.append("hybrid graphics: yes")
    for d in drivers:
        line = "driver proposal %s: %s" % (d["id"], d["state"])
        if d["missing"]:
            line += " (missing: %s)" % " ".join(d["missing"])
        lines.append(line)
    if not drivers:
        lines.append("no hardware profile matches")
    return "\n".join(lines) + "\n"


def collect(hardware_dir=None, facts=None, installed=None, kernel=None):
    """Returns {"facts", "drivers", "report"}. Raises when detection fails (the model shows the error)."""
    profiles = hw.load_profiles(hardware_dir or HARDWARE_DIR)
    facts = facts or hw.collect_live()
    report = hw.detect(facts, profiles)
    if installed is None:
        installed = PacmanSystem().installed_packages()
    drivers = drivers_of(report, installed)
    return {"facts": facts_of(report, facts.has_bluetooth), "drivers": drivers,
            "report": report_text(report, drivers, facts.has_bluetooth, kernel if kernel is not None else os.uname().release)}
