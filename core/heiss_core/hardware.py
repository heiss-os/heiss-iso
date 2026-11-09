"""Read-only hardware detection and declarative hardware profiles.

collect_live() gathers raw facts (lspci, /sys, /proc/cpuinfo, systemd-detect-virt).
detect() is a pure function: facts + hardware profiles -> proposals. Nothing here
installs or changes anything; proposals go through the resolver and the helper.
"""
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass, field

from .errors import ValidationError
from .manifest import PKG_RE, POST_ACTIONS, UNIT_RE, _dropins, _strs, _text

CLASSES = {"display": {"0300", "0302", "0380"}, "network": {"0280", "0200"}}
HEX4 = re.compile(r"^[0-9a-f]{4}$")
PARAM_RE = re.compile(r"^[a-z0-9_.-]+(=[A-Za-z0-9_.,:-]+)?$")
CHASSIS_LAPTOP = {8, 9, 10, 11, 14, 30, 31, 32}  # SMBIOS: portable, laptop, notebook, hand held, sub notebook, tablet, convertible, detachable
FORM_FACTORS = ("laptop", "desktop", "vm")
ALLOWED = {"schema_version", "id", "name", "description", "safe_by_default", "match", "packages",
           "services", "kernel_params", "dropins", "post_actions", "warnings"}
MATCH_KEYS = {"pci", "virt", "form_factor", "cpu_vendor"}
PCI_KEYS = {"vendor", "class", "devices", "device_min", "device_max"}


@dataclass(frozen=True)
class PciDevice:
    slot: str
    cls: str       # 4 hex digits, e.g. "0300"
    vendor: str    # 4 hex digits
    device: str


@dataclass
class Facts:
    pci: list = field(default_factory=list)
    cpu_vendor: str = ""
    virt: str = "none"            # systemd-detect-virt --vm: none, oracle, kvm, vmware, microsoft ...
    chassis_type: int = 0
    has_battery: bool = False
    has_bluetooth: bool = False
    sys_vendor: str = ""
    product_name: str = ""

    @property
    def form_factor(self):
        if self.virt != "none":
            return "vm"
        return "laptop" if (self.chassis_type in CHASSIS_LAPTOP or self.has_battery) else "desktop"


# ---------- collection ----------

_FIELD = re.compile(r'"([^"]*)"')
_ID = re.compile(r"\[([0-9a-fA-F]{4})\]\s*$")


def parse_lspci(text):
    """Parse `lspci -nn -mm` output."""
    devs = []
    for line in text.splitlines():
        if not line.strip():
            continue
        slot = line.split(" ", 1)[0]
        fields = _FIELD.findall(line)
        if len(fields) < 3:
            continue
        ids = []
        for f in fields[:3]:
            m = _ID.search(f)
            if not m:
                break
            ids.append(m.group(1).lower())
        if len(ids) == 3:
            devs.append(PciDevice(slot, ids[0], ids[1], ids[2]))
    return devs


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"})
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def collect_live(root="/"):
    j = lambda *p: os.path.join(root, *p)  # noqa: E731
    cpu = re.search(r"^vendor_id\s*:\s*(\S+)", _read(j("proc/cpuinfo")), re.M)
    virt = _run(["systemd-detect-virt", "--vm"]).strip() or "none"
    try:
        chassis = int(_read(j("sys/class/dmi/id/chassis_type"), "0"))
    except ValueError:
        chassis = 0
    ps = j("sys/class/power_supply")
    battery = os.path.isdir(ps) and any(_read(os.path.join(ps, d, "type")) == "Battery" for d in os.listdir(ps))
    return Facts(
        pci=parse_lspci(_run(["lspci", "-nn", "-mm"])), cpu_vendor=cpu.group(1) if cpu else "",
        virt=virt, chassis_type=chassis, has_battery=battery,
        has_bluetooth=os.path.isdir(j("sys/class/bluetooth")) and bool(os.listdir(j("sys/class/bluetooth"))),
        sys_vendor=_read(j("sys/class/dmi/id/sys_vendor")), product_name=_read(j("sys/class/dmi/id/product_name")),
    )


def load_fixture(path):
    with open(os.path.join(path, "lspci.txt"), encoding="utf-8") as f:
        pci = parse_lspci(f.read())
    with open(os.path.join(path, "facts.json"), encoding="utf-8") as f:
        d = json.load(f)
    return Facts(pci=pci, cpu_vendor=d["cpu_vendor"], virt=d["virt"], chassis_type=d["chassis_type"],
                 has_battery=d["has_battery"], has_bluetooth=d["has_bluetooth"],
                 sys_vendor=d.get("sys_vendor", ""), product_name=d.get("product_name", ""))


# ---------- hardware profiles ----------

@dataclass(frozen=True)
class HwProfile:
    id: str
    name: dict
    description: dict
    safe_by_default: bool
    match: dict
    packages: tuple = ()
    services: tuple = ()
    kernel_params: tuple = ()
    dropins: tuple = ()
    post_actions: tuple = ()
    warnings: dict = field(default_factory=dict)


def _hex(v, where):
    if not isinstance(v, str) or not HEX4.match(v):
        raise ValidationError("%s: %r must be 4 lowercase hex digits" % (where, v))
    return v


def parse_profile(doc, where="hardware profile"):
    if set(doc) - ALLOWED:
        raise ValidationError("%s: unknown keys %s" % (where, sorted(set(doc) - ALLOWED)))
    if doc.get("schema_version") != 1:
        raise ValidationError("%s: schema_version must be 1" % where)
    pid = doc.get("id", "")
    if not re.match(r"^[a-z][a-z0-9-]{0,40}$", str(pid)):
        raise ValidationError("%s: invalid id %r" % (where, pid))
    match = doc.get("match")
    if not isinstance(match, dict) or not match or set(match) - MATCH_KEYS:
        raise ValidationError("%s: match needs at least one of %s" % (where, sorted(MATCH_KEYS)))
    if "form_factor" in match and match["form_factor"] not in FORM_FACTORS:
        raise ValidationError("%s: form_factor must be one of %s" % (where, FORM_FACTORS))
    if "virt" in match and not re.match(r"^[a-z0-9-]+$", str(match["virt"])):
        raise ValidationError("%s: bad virt" % where)
    for c in match.get("pci", []):
        if not isinstance(c, dict) or set(c) - PCI_KEYS:
            raise ValidationError("%s: pci condition keys must be in %s" % (where, sorted(PCI_KEYS)))
        for k in ("vendor", "device_min", "device_max"):
            if k in c:
                _hex(c[k], where)
        for d in c.get("devices", []):
            _hex(d, where)
        if "class" in c and c["class"] not in CLASSES:
            raise ValidationError("%s: pci class must be one of %s" % (where, sorted(CLASSES)))
    actions = doc.get("post_actions", [])
    if not isinstance(actions, list) or set(actions) - POST_ACTIONS:
        raise ValidationError("%s: post_actions must be a subset of %s" % (where, sorted(POST_ACTIONS)))
    params = doc.get("kernel_params", [])
    if not isinstance(params, list) or not all(isinstance(p, str) and PARAM_RE.match(p) for p in params):
        raise ValidationError("%s: invalid kernel_params" % where)
    warnings = doc.get("warnings", {})
    if warnings:
        _text({"w": warnings}, "w", where)
    return HwProfile(
        id=pid, name=_text(doc, "name", where), description=_text(doc, "description", where),
        safe_by_default=bool(doc.get("safe_by_default", False)), match=match,
        packages=_strs(doc, "packages", PKG_RE, where), services=_strs(doc, "services", UNIT_RE, where),
        kernel_params=tuple(params), dropins=_dropins(doc, where), post_actions=tuple(actions),
        warnings=dict(warnings))


def load_profiles(path):
    out = {}
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".toml"):
            continue
        with open(os.path.join(path, fn), "rb") as f:
            try:
                doc = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise ValidationError("%s: %s" % (fn, e))
        p = parse_profile(doc, fn)
        if fn != p.id + ".toml":
            raise ValidationError("%s: file name must match id %r" % (fn, p.id))
        out[p.id] = p
    return out


# ---------- matching ----------

def _pci_ok(cond, dev):
    if "vendor" in cond and dev.vendor != cond["vendor"]:
        return False
    if "class" in cond and dev.cls not in CLASSES[cond["class"]]:
        return False
    if "devices" in cond and dev.device not in cond["devices"]:
        return False
    d = int(dev.device, 16)
    if "device_min" in cond and d < int(cond["device_min"], 16):
        return False
    return not ("device_max" in cond and d > int(cond["device_max"], 16))


def matches(profile, facts):
    m = profile.match
    if "form_factor" in m and facts.form_factor != m["form_factor"]:
        return False
    if "cpu_vendor" in m and facts.cpu_vendor != m["cpu_vendor"]:
        return False
    if "virt" in m:
        if m["virt"] == "none" and facts.virt != "none":
            return False
        if m["virt"] != "none" and facts.virt != m["virt"]:
            return False
    # every pci condition must be met by some device
    return all(any(_pci_ok(c, d) for d in facts.pci) for c in m.get("pci", []))


@dataclass
class Report:
    form_factor: str
    cpu_vendor: str
    virt: str
    gpus: list
    proposals: list      # matching HwProfile objects, sorted by id
    hybrid_graphics: bool

    def to_dict(self):
        return {
            "form_factor": self.form_factor, "cpu_vendor": self.cpu_vendor, "virt": self.virt,
            "gpus": self.gpus, "hybrid_graphics": self.hybrid_graphics,
            "proposals": [{"id": p.id, "safe_by_default": p.safe_by_default, "packages": list(p.packages),
                           "services": list(p.services), "kernel_params": list(p.kernel_params),
                           "post_actions": list(p.post_actions), "warnings": p.warnings} for p in self.proposals],
        }


def detect(facts, profiles):
    gpus = [{"slot": d.slot, "vendor": d.vendor, "device": d.device}
            for d in facts.pci if d.cls in CLASSES["display"]]
    vendors = {g["vendor"] for g in gpus}
    hybrid = facts.virt == "none" and len(gpus) > 1 and len(vendors) > 1
    props = sorted((p for p in profiles.values() if matches(p, facts)), key=lambda p: p.id)
    return Report(facts.form_factor, facts.cpu_vendor, facts.virt, gpus, props, hybrid)


def render_text(report, lang="en"):
    lines = ["form factor: %s   cpu: %s   virtualization: %s" % (report.form_factor, report.cpu_vendor or "?", report.virt)]
    for g in report.gpus:
        lines.append("gpu: %s:%s at %s" % (g["vendor"], g["device"], g["slot"]))
    if report.hybrid_graphics:
        lines.append("hybrid graphics: yes")
    for p in report.proposals:
        tag = "safe by default" if p.safe_by_default else "needs confirmation"
        lines.append("")
        lines.append("[%s] %s (%s)" % (p.id, p.name[lang], tag))
        lines.append("  " + p.description[lang])
        if p.packages:
            lines.append("  packages: " + " ".join(p.packages))
        if p.services:
            lines.append("  services: " + " ".join(p.services))
        if p.kernel_params:
            lines.append("  kernel parameters: " + " ".join(p.kernel_params))
        if p.warnings:
            lines.append("  WARNING: " + p.warnings[lang])
    if not report.proposals:
        lines.append("no hardware profile matches")
    return "\n".join(lines) + "\n"
