"""Turn answers + manifests + current state into a plan. Pure: no side effects."""
from dataclasses import dataclass, field

from . import manifest as mf
from .errors import ValidationError


@dataclass
class Plan:
    profile: str
    addons: list
    manifests: list                      # ids in dependency order
    install_packages: list = field(default_factory=list)
    adopt_packages: list = field(default_factory=list)   # already installed, claimed as Heiss-owned
    remove_packages: list = field(default_factory=list)
    kept_packages: dict = field(default_factory=dict)    # owned but still needed: {pkg: [dependents]}
    forget_packages: list = field(default_factory=list)  # in state but no longer installed
    enable_services: list = field(default_factory=list)
    disable_services: list = field(default_factory=list)
    install_flatpaks: list = field(default_factory=list)
    remove_flatpaks: list = field(default_factory=list)
    dropins: list = field(default_factory=list)
    kde_settings: list = field(default_factory=list)
    post_actions: list = field(default_factory=list)
    next_state: dict = field(default_factory=dict)

    def is_empty(self):
        return not any([self.install_packages, self.adopt_packages, self.remove_packages,
                        self.enable_services, self.disable_services, self.install_flatpaks,
                        self.remove_flatpaks, self.dropins, self.kde_settings, self.post_actions])

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    def to_text(self):
        lines = ["profile: %s  add-ons: %s" % (self.profile, ", ".join(self.addons) or "none"),
                 "manifests: %s" % " -> ".join(self.manifests)]
        for title, items in (("install packages", self.install_packages), ("adopt packages", self.adopt_packages),
                             ("remove packages", self.remove_packages), ("enable services", self.enable_services),
                             ("disable services", self.disable_services), ("install flatpaks", self.install_flatpaks),
                             ("remove flatpaks", self.remove_flatpaks), ("forget (gone) packages", self.forget_packages),
                             ("post actions", self.post_actions)):
            if items:
                lines.append("%s (%d): %s" % (title, len(items), " ".join(items)))
        if self.dropins:
            lines.append("write drop-ins: %s" % " ".join(d["path"] for d in self.dropins))
        if self.kde_settings:
            lines.append("KDE settings: %d keys" % len(self.kde_settings))
        for pkg, deps in sorted(self.kept_packages.items()):
            lines.append("kept %s (needed by %s)" % (pkg, ", ".join(sorted(deps))))
        if self.is_empty() and not self.forget_packages:
            lines.append("nothing to do")
        return "\n".join(lines)


def _union(manifests, order, attr):
    seen, out = set(), []
    for mid in order:
        for x in getattr(manifests[mid], attr):
            if x not in seen:
                seen.add(x)
                out.append(x)
    return out


def resolve(answers, manifests, state, system, adopt=False):
    prof = manifests.get(answers["profile"])
    if prof is None or prof.kind != "profile":
        raise ValidationError("%r is not a profile" % answers["profile"])
    for a in answers["addons"]:
        if a not in manifests or manifests[a].kind != "addon":
            raise ValidationError("%r is not an add-on" % a)
    order = mf.closure(manifests, [answers["profile"]] + list(answers["addons"]))

    want_pkgs = _union(manifests, order, "packages")
    want_svc = _union(manifests, order, "services")
    want_fp = _union(manifests, order, "flatpaks")

    installed = system.installed_packages()
    owned = set(state["packages"])
    plan = Plan(profile=answers["profile"], addons=list(answers["addons"]), manifests=order)

    plan.install_packages = [p for p in want_pkgs if p not in installed]
    if adopt:
        explicit = system.explicit_packages()
        plan.adopt_packages = [p for p in want_pkgs if p in installed and p in explicit and p not in owned]

    # removal: only what Heiss owns, is no longer wanted, and nothing else needs
    gone = {p for p in owned if p not in want_pkgs}
    plan.forget_packages = sorted(p for p in gone if p not in installed)
    removal = {p for p in gone if p in installed}
    kept = {}
    changed = True
    while changed:
        changed = False
        for p in sorted(removal):
            outside = system.required_by(p) - removal
            if outside:
                removal.discard(p)
                kept[p] = sorted(outside)
                changed = True
    plan.remove_packages = sorted(removal)
    plan.kept_packages = kept

    enabled = system.enabled_services()
    plan.enable_services = [s for s in want_svc if s not in enabled]
    plan.disable_services = sorted(s for s in state["services"] if s not in want_svc and s in enabled)
    fp_inst = system.installed_flatpaks()
    plan.install_flatpaks = [f for f in want_fp if f not in fp_inst]
    plan.remove_flatpaks = sorted(f for f in state["flatpaks"] if f not in want_fp and f in fp_inst)

    # idempotent: only what differs from the system today
    plan.dropins = [d for mid in order for d in manifests[mid].dropins
                    if system.read_text(d["path"]) != d["content"]]
    plan.kde_settings = [k for mid in order for k in manifests[mid].kde_settings
                         if system.kde_value(k["file"], k["group"], k["key"]) != k["value"]]
    plan.post_actions = _union(manifests, order, "post_actions") if (plan.install_packages or plan.remove_packages) else []

    plan.next_state = {
        "schema_version": state["schema_version"],
        "applied": {"profile": answers["profile"], "addons": list(answers["addons"])},
        "packages": sorted((owned - set(plan.remove_packages) - set(plan.forget_packages))
                           | set(plan.install_packages) | set(plan.adopt_packages)),
        "services": sorted((set(state["services"]) - set(plan.disable_services)) | set(plan.enable_services)),
        "flatpaks": sorted((set(state["flatpaks"]) - set(plan.remove_flatpaks)) | set(plan.install_flatpaks)),
    }
    return plan
