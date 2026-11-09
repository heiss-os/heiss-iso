"""Turn a Plan into an ordered list of helper calls and run them.

All privileged work goes through the helper (D-Bus + polkit). The order keeps
removals last, so a failure while installing never strips anything from the system.
User-level KDE settings are written locally as the user, never through the helper.
"""
import subprocess

from .errors import HeissError


class LocalRunner:
    """Runs user-level commands with fixed argument lists (no shell)."""

    def kwriteconfig(self, file, group, key, value):
        r = subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--", value],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise HeissError("kwriteconfig6 failed for %s/%s/%s: %s" % (file, group, key, r.stderr.strip()[:200]))


def build_calls(plan):
    """[(method, args, description)] in execution order."""
    calls = []
    if plan.adopt_packages:
        calls.append(("AdoptPackages", (plan.adopt_packages,), "claim %d installed package(s)" % len(plan.adopt_packages)))
    if plan.install_packages:
        calls.append(("InstallPackages", (plan.install_packages,), "install %d package(s)" % len(plan.install_packages)))
    if plan.enable_services:
        calls.append(("SetServices", (plan.enable_services, []), "enable %d service(s)" % len(plan.enable_services)))
    for d in plan.dropins:
        calls.append(("WriteDropin", (d["path"],), "write %s" % d["path"]))
    if plan.disable_services:
        calls.append(("SetServices", ([], plan.disable_services), "disable %d service(s)" % len(plan.disable_services)))
    if plan.remove_packages:
        calls.append(("RemovePackages", (plan.remove_packages,), "remove %d package(s)" % len(plan.remove_packages)))
    for action in plan.post_actions:
        calls.append(("RunPostAction", (action,), "post action %s" % action))
    return calls


def preflight(plan, system):
    """Raise HeissError when the plan cannot be applied right now. Changes nothing."""
    if plan.install_flatpaks or plan.remove_flatpaks:
        raise HeissError("Flatpak changes are not supported by the helper yet; nothing was changed")
    if plan.install_packages and not system.network_connected():
        raise HeissError("no network connection, cannot download %d package(s); nothing was changed" % len(plan.install_packages))


def apply_plan(plan, helper, system, on_output, local=None, on_step=None):
    """Run the plan. `helper.call(method, args, on_output)` raises HeissError on failure.

    Returns the number of helper calls made. Stops at the first failure and says which step failed.
    """
    preflight(plan, system)
    calls = build_calls(plan)
    done = 0
    for n, (method, args, desc) in enumerate(calls, 1):
        if on_step:
            on_step(n, len(calls), desc)
        try:
            helper.call(method, args, on_output)
        except HeissError as e:
            hint = "Steps before it were applied; run 'heiss profile diff' to see what is left." if n > 1 else "Nothing was applied."
            raise HeissError("step %d of %d failed (%s): %s. %s" % (n, len(calls), desc, e, hint))
        done += 1
    local = local or LocalRunner()
    for k in plan.kde_settings:
        local.kwriteconfig(k["file"], k["group"], k["key"], k["value"])
    return done
