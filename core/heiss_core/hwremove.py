"""Plan for removing one hardware profile ("Remove this driver"). Pure: no side effects.

Used twice with the same rules: `heiss hw remove` shows the plan, and the helper recomputes it from its own
root-owned catalog (the client only names the profile). Only things Heiss itself installed (the state file) are
planned, nothing the profile or an add-on still wants is touched, and the packages a profile lists in
`keep_on_remove` stay (the LTS kernel is the way back, DECISIONS 2026-11-16).
"""
from dataclasses import dataclass, field

from . import manifest as mf
from . import resolver
from .errors import ValidationError


@dataclass
class Removal:
    profile: str
    packages: list = field(default_factory=list)      # installed by Heiss, to remove
    kept: dict = field(default_factory=dict)          # {package: why it stays}
    services: list = field(default_factory=list)      # enabled by Heiss, to disable
    dropins: list = field(default_factory=list)       # [{"path", "content"}] to delete if unchanged
    post_actions: list = field(default_factory=list)

    def to_text(self):
        lines = ["remove hardware profile: %s" % self.profile,
                 "remove packages (%d): %s" % (len(self.packages), " ".join(self.packages))]
        if self.services:
            lines.append("disable services (%d): %s" % (len(self.services), " ".join(self.services)))
        if self.dropins:
            lines.append("delete drop-ins: %s" % " ".join(d["path"] for d in self.dropins))
        if self.post_actions:
            lines.append("post actions: %s" % " ".join(self.post_actions))
        for pkg, why in sorted(self.kept.items()):
            lines.append("kept %s (%s)" % (pkg, why))
        return "\n".join(lines)


def _wanted_by_others(profile_id, catalog, manifests, state):
    """(packages, services, drop-in paths) that something else than `profile_id` still asks for: the applied
    profile and add-ons, and the other hardware profiles applied earlier."""
    applied = state.get("applied") or {}
    ids = [i for i in [applied.get("profile")] + list(applied.get("addons") or []) if i in manifests]
    order = mf.closure(manifests, ids) if ids else []
    pkgs = {p for m in order for p in manifests[m].packages}
    svcs = {s for m in order for s in manifests[m].services}
    paths = {d["path"] for m in order for d in manifests[m].dropins}
    # a sibling whose packages are all in this profile (the two hybrid-graphics profiles share nvidia-prime) goes
    # with it; any other applied profile keeps what it needs
    mine = set(catalog[profile_id].packages)
    others = {i: p for i, p in catalog.items() if i != profile_id and not set(p.packages) <= mine}
    for i in resolver.sticky_hardware(others, state, pkgs):
        pkgs.update(others[i].packages)
        svcs.update(others[i].services)
        paths.update(d["path"] for d in others[i].dropins)
    return pkgs, svcs, paths


def plan_removal(profile_id, catalog, manifests, state, installed):
    """Raises ValidationError when the profile is unknown or nothing of it was installed by Heiss."""
    prof = catalog.get(profile_id)
    if prof is None:
        raise ValidationError("unknown hardware profile %r" % profile_id)
    owned, installed = set(state["packages"]), set(installed)
    pkgs, svcs, paths = _wanted_by_others(profile_id, catalog, manifests, state)
    out = Removal(profile=profile_id)
    for p in prof.packages:
        if p not in owned or p not in installed:
            continue
        if p in prof.keep_on_remove:
            out.kept[p] = "kept on purpose, it is the way back"
        elif p in pkgs:
            out.kept[p] = "still wanted by your profile or another hardware profile"
        else:
            out.packages.append(p)
    if not out.packages:
        raise ValidationError("nothing of hardware profile %r was installed by Heiss OS, so there is nothing to remove"
                              % profile_id)
    out.services = [s for s in prof.services if s in state["services"] and s not in svcs]
    out.dropins = [dict(d) for d in prof.dropins if d["path"] not in paths]
    out.post_actions = list(prof.post_actions) if (out.packages or out.dropins) else []
    return out
