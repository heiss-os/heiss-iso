"""Action table: D-Bus method -> polkit action id -> validated list of steps.

build_*() validates (raising HelperError) and returns steps; nothing runs here.
"""
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

from heiss_core import state as st

from . import policy
from .errors import HelperError
from .runner import Runner

MIN_FREE_BYTES = 1 << 30   # 1 GiB free before install/update
PACMAN_LOCK = "/var/lib/pacman/db.lck"
SNAPPER_ROOT_CONFIG = "/etc/snapper/configs/root"


@dataclass
class Step:
    desc: str
    argv: Optional[list] = None
    func: Optional[Callable] = None   # func(ctx, emit)
    optional: bool = False            # failure is logged, job continues


class Context:
    """Everything environment-dependent, injectable for tests."""

    def __init__(self, profiles_dir="/usr/share/heiss/profiles", hardware_dir="/usr/share/heiss/hardware",
                 state_path="/var/lib/heiss/state.json", root="/", strict=True, runner=None):
        self.profiles_dir, self.hardware_dir = profiles_dir, hardware_dir
        self.state_path, self.root, self.strict = state_path, root, strict
        self.runner = runner or Runner()

    def _query(self, argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"})
        except (OSError, subprocess.TimeoutExpired):
            return set()
        return set(r.stdout.split()) if r.returncode == 0 else set()

    def installed_packages(self):
        return self._query(["pacman", "-Qq"])

    def explicit_packages(self):
        return self._query(["pacman", "-Qeq"])

    def enabled_services(self):
        out = set()
        for line in self._query_lines(["systemctl", "list-unit-files", "--state=enabled", "--no-legend", "--no-pager"]):
            if line.split():
                out.add(line.split()[0])
        return out

    def _query_lines(self, argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"})
        except (OSError, subprocess.TimeoutExpired):
            return []
        return r.stdout.splitlines() if r.returncode == 0 else []

    def update_state(self, fn):
        """Locked read-modify-write of the ownership state."""
        with st.lock(self.state_path):
            doc = st.load(self.state_path)
            fn(doc)
            st.save(self.state_path, doc)

    def trusted(self):
        return policy.load_trusted(self.profiles_dir, self.hardware_dir, self.strict)

    def lock_present(self):
        return os.path.exists(os.path.join(self.root, PACMAN_LOCK.lstrip("/")))

    def free_bytes(self):
        return shutil.disk_usage(self.root).free

    def snapshots_available(self):
        return shutil.which("snapper") is not None and os.path.exists(os.path.join(self.root, SNAPPER_ROOT_CONFIG.lstrip("/")))


# ---- step functions ----

def _check_pacman_free(ctx, emit):
    if ctx.lock_present():
        raise HelperError("Busy", "another package manager run is active (db.lck exists)")


def _check_space(ctx, emit):
    if ctx.free_bytes() < MIN_FREE_BYTES:
        raise HelperError("Failed", "less than 1 GiB free on the system partition")


def _snapshot_step(desc):
    def run(ctx, emit):
        if not ctx.snapshots_available():
            emit("snapshots are not available on this system, continuing without one")
            return
        rc = ctx.runner.run(["snapper", "-c", "root", "create", "--description", desc], emit, timeout=600)
        if rc != 0:
            raise HelperError("Failed", "snapshot failed (exit %d)" % rc)
    return Step("snapshot", func=run, optional=True)


def _dropin_step(path, content):
    def run(ctx, emit):
        policy.write_dropin(path, content, ctx.root)
        emit("wrote %s" % path)
    return Step("write drop-in", func=run)


# ---- builders ----

def build_install(ctx, names):
    names = policy.check_install(names, ctx.trusted())
    before = {}

    def remember(c, emit):
        before["pkgs"] = c.installed_packages()

    def record(c, emit):
        new = [n for n in names if n not in before["pkgs"]]
        c.update_state(lambda d: d["packages"].extend(new))     # only what Heiss really added is Heiss-owned
        emit("recorded %d new package(s) as installed by Heiss" % len(new))

    return [Step("check lock", func=_check_pacman_free), Step("check space", func=_check_space),
            _snapshot_step("Heiss: before installing packages"), Step("remember installed", func=remember),
            Step("install", argv=["pacman", "-S", "--needed", "--noconfirm", "--"] + names),
            Step("record ownership", func=record)]


def build_remove(ctx, names):
    names = policy.check_remove(names, ctx.trusted(), ctx.state_path)

    def record(c, emit):
        c.update_state(lambda d: d.__setitem__("packages", [p for p in d["packages"] if p not in names]))

    return [Step("check lock", func=_check_pacman_free),
            _snapshot_step("Heiss: before removing packages"),
            Step("remove", argv=["pacman", "-R", "--noconfirm", "--"] + names),   # no -s: never cascades
            Step("record ownership", func=record)]


def build_adopt(ctx, names):
    """Claim already installed, explicitly installed packages named in a manifest (e.g. the ISO content)."""
    names = policy.check_install(names, ctx.trusted())

    def adopt(c, emit):
        owned = set(st.load(c.state_path)["packages"])
        ok = [n for n in names if n in c.installed_packages() and n in c.explicit_packages() and n not in owned]
        c.update_state(lambda d: d["packages"].extend(ok))
        emit("adopted %d of %d package(s)" % (len(ok), len(names)))

    return [Step("adopt", func=adopt)]


def build_services(ctx, enable, disable):
    enable, disable = policy.check_services(enable, disable, ctx.trusted())
    before = {}
    steps = [Step("remember enabled", func=lambda c, e: before.update(svc=c.enabled_services()))]
    if enable:
        steps.append(Step("enable", argv=["systemctl", "enable", "--"] + enable))      # no --now
    if disable:
        steps.append(Step("disable", argv=["systemctl", "disable", "--"] + disable))

    def record(c, emit):
        newly = [u for u in enable if u not in before["svc"]]
        c.update_state(lambda d: d.__setitem__(
            "services", [u for u in d["services"] if u not in disable] + newly))

    steps.append(Step("record ownership", func=record))
    return steps


def build_dropin(ctx, path):
    path, content = policy.check_dropin(path, ctx.trusted())
    return [_dropin_step(path, content)]


def build_post_action(ctx, action_id):
    argv = policy.check_post_action(action_id)      # validates first: only known ids reach the description
    return [Step("post action " + action_id, argv=argv)]


def build_update(ctx):
    return [Step("check lock", func=_check_pacman_free), Step("check space", func=_check_space),
            _snapshot_step("Heiss: before system update"),
            Step("update", argv=["pacman", "-Syu", "--noconfirm"])]   # always a full upgrade


def build_snapshot(ctx, description):
    desc = policy.check_snapshot_description(description)
    s = _snapshot_step(desc)
    s.optional = False
    return [s]


@dataclass(frozen=True)
class Action:
    method: str
    polkit: str
    signature: str
    build: Callable


ACTIONS = {a.method: a for a in (
    Action("InstallPackages", "org.heiss.packages.install", "as", build_install),
    Action("RemovePackages", "org.heiss.packages.remove", "as", build_remove),
    Action("AdoptPackages", "org.heiss.packages.adopt", "as", build_adopt),
    Action("SetServices", "org.heiss.services.manage", "asas", build_services),
    Action("WriteDropin", "org.heiss.config.write", "s", build_dropin),
    Action("RunPostAction", "org.heiss.postaction.run", "s", build_post_action),
    Action("UpdateSystem", "org.heiss.system.update", "", build_update),
    Action("CreateSnapshot", "org.heiss.snapshot.create", "s", build_snapshot),
)}


def execute(steps, ctx, emit):
    """Run steps in order. Returns (ok, message). Stops at the first non-optional failure."""
    for s in steps:
        emit("== " + s.desc)
        try:
            if s.func:
                s.func(ctx, emit)
            else:
                rc = ctx.runner.run(s.argv, emit)
                if rc != 0:
                    raise HelperError("Failed", "%s failed (exit %d)" % (s.desc, rc))
        except HelperError as e:
            if s.optional and e.code == "Failed":
                emit("warning: %s" % e.message)
                continue
            return False, e.message
        except OSError as e:
            return False, "%s: %s" % (s.desc, e.strerror or e)
    return True, "done"
