"""heiss command line: profile list|show|diff|apply, hw detect|remove, theme sync|status, check, answers validate.

`apply` shows the plan, asks for confirmation and runs it through the privileged
helper (D-Bus + polkit). `--dry-run` only prints the plan.
"""
import argparse
import json
import os
import sys

from . import answers as ans
from . import check as checkmod
from . import apply as applymod
from . import hardware as hw
from . import hwremove
from . import privacy as pv
from . import manifest as mf
from . import resolver, state as st
from . import themesync
from .errors import HeissError
from .system import PacmanSystem

DEFAULT_PROFILES = "/usr/share/heiss/profiles"
DEFAULT_ETC = "/etc/heiss"
DEFAULT_STATE = "/var/lib/heiss/state.json"
DEFAULT_HARDWARE = "/usr/share/heiss/hardware"


def _paths(args):
    prof = args.profiles or os.environ.get("HEISS_PROFILES", DEFAULT_PROFILES)
    etc = os.environ.get("HEISS_ETC", DEFAULT_ETC)
    return prof, os.path.join(etc, "profile.toml"), os.environ.get("HEISS_STATE", DEFAULT_STATE)


def _kinds(manifests, kind):
    return {i for i, m in manifests.items() if m.kind == kind}


def _hardware_dir():
    return os.environ.get("HEISS_HARDWARE", DEFAULT_HARDWARE)


def _hardware_catalog():
    try:
        return hw.load_profiles(_hardware_dir())
    except FileNotFoundError:
        return {}


def _matching_hardware(catalog):
    """Ids of the hardware profiles that fit this machine; None when detection is impossible (no filter then).
    Detection runs without capabilities on purpose: this only filters what an earlier apply keeps (sticky_hardware),
    it never offers anything; the `requires` check of a new choice is in _chosen_hardware."""
    if not catalog:
        return None
    try:
        return {p.id for p in hw.detect(hw.collect_live(), catalog).proposals}
    except Exception:   # advisory only: never block an apply
        return None


def _chosen_hardware(args, catalog):
    ids = list(getattr(args, "hardware", None) or [])
    unknown = [i for i in ids if i not in catalog]
    if unknown:
        raise HeissError("unknown hardware profile(s): %s" % ", ".join(unknown))
    caps = hw.capabilities()
    for i in sorted(set(ids)):
        need = hw.unmet(catalog[i], caps)
        if need:
            raise HeissError("hardware profile %s needs %s, which is not installed on this system "
                             "(package heiss-safe-graphics); it is not applied" % (i, " and ".join(need)))
    confirmed = set(getattr(args, "confirm_hardware", None) or [])
    stray = sorted(confirmed - set(ids))
    if stray:
        raise HeissError("--confirm-hardware %s: not selected with --hardware" % ", ".join(stray))
    # only a real apply needs the confirmation; diff and --dry-run just show the plan
    if getattr(args, "sub", "") == "apply" and not getattr(args, "dry_run", False):
        for i in sorted(set(ids)):
            if hw.needs_confirmation(catalog[i]) and i not in confirmed:
                snap = ("A snapshot is set up (snapper), but check it before you continue."
                        if hw.snapshot_available() else
                        "No snapshot is set up, so going back means removing the packages.")
                raise HeissError("hardware profile %s needs your explicit confirmation: it installs a graphics driver "
                                 "and a wrong choice can leave a black screen. %s If the screen stays black, restart "
                                 "and choose \"Heiss OS, safe graphics\" in the boot menu. Pass --confirm-hardware %s "
                                 "to go on." % (i, snap, i))
    return [catalog[i] for i in sorted(set(ids))]


def _build(args, system=None):
    prof_dir, answers_path, state_path = _paths(args)
    manifests = mf.load_dir(prof_dir)
    if args.profile:
        doc = ans.validate({"profile": args.profile, "addons": args.addon or []},
                           _kinds(manifests, "profile"), _kinds(manifests, "addon"))
    else:
        doc = ans.load(answers_path, known_profiles=_kinds(manifests, "profile"),
                       known_addons=_kinds(manifests, "addon"))
    state, catalog = st.load(state_path), _hardware_catalog()
    return resolver.resolve(doc, manifests, state, system or PacmanSystem(), adopt=getattr(args, "adopt", False),
                            hardware=_chosen_hardware(args, catalog), catalog=catalog,
                            matching=_matching_hardware(catalog), privacy=getattr(args, "privacy", None))


def _ask(prompt):
    if not sys.stdin.isatty():
        raise HeissError("not a terminal: pass --yes to apply without asking")
    return input(prompt).strip().lower() in ("y", "yes")


def _real_helper():
    try:
        from heiss_helper.client import GioHelperClient
    except (ImportError, ValueError) as e:  # python-gobject or the helper package missing
        raise HeissError("the helper client is not available (needs python-gobject and heiss-helper): %s" % e)
    return GioHelperClient()


def main(argv=None, system=None, out=sys.stdout, helper=None, confirm=None, theme_env=None, check_env=None):
    p = argparse.ArgumentParser(prog="heiss")
    p.add_argument("--profiles", help="directory with manifests")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    prof = sub.add_parser("profile").add_subparsers(dest="sub", required=True)
    prof.add_parser("list")
    show = prof.add_parser("show")
    show.add_argument("id")
    for name in ("diff", "apply"):
        sp = prof.add_parser(name)
        sp.add_argument("--profile")
        sp.add_argument("--addon", action="append")
        sp.add_argument("--adopt", action="store_true", help="claim already installed profile packages")
        sp.add_argument("--hardware", action="append", metavar="ID", help="also apply this hardware profile (see 'hw detect')")
        sp.add_argument("--confirm-hardware", action="append", metavar="ID",
                        help="confirm a hardware profile that is not safe by default (needed by apply, see 'hw detect')")
        sp.add_argument("--privacy", choices=pv.LEVELS, help="also apply this privacy level (network MAC, screen lock)")
        if name == "apply":
            sp.add_argument("--dry-run", action="store_true")
            sp.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    hwp = sub.add_parser("hw").add_subparsers(dest="sub", required=True)
    det = hwp.add_parser("detect", help="read-only hardware detection and proposals")
    det.add_argument("--hardware", help="directory with hardware profiles")
    det.add_argument("--fixture", help="use a recorded fixture directory instead of the live system")
    det.add_argument("--lang", choices=("en", "ru"), default="en")
    rm = hwp.add_parser("remove", help="remove a hardware profile (driver) that Heiss OS installed")
    rm.add_argument("id")
    rm.add_argument("--dry-run", action="store_true")
    rm.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    th = sub.add_parser("theme").add_subparsers(dest="sub", required=True)
    ts = th.add_parser("sync", help="bring launcher icon and Konsole in line with the active Heiss theme and check the rest")
    ts.add_argument("--no-wait", action="store_true", help="do not wait for plasmashell and the settings to settle")
    ts.add_argument("--dry-run", action="store_true")
    th.add_parser("status", help="like sync --dry-run --no-wait: report only")
    ck = sub.add_parser("check", help="read-only health check of the installed system (exit 1 on any FAIL)")
    ck.add_argument("--report", metavar="FILE", help="also save the full output and the exact commands to FILE")
    av = sub.add_parser("answers").add_subparsers(dest="sub", required=True)
    v = av.add_parser("validate")
    v.add_argument("file")
    args = p.parse_args(argv)
    if args.cmd == "theme":
        env = theme_env or themesync.RealEnv()
        dry = args.sub == "status" or args.dry_run
        log = (lambda line: None) if dry else env.append_log

        def say(line):
            out.write(line + "\n")
            log(line)
        _, rc = themesync.sync(env, wait=(args.sub == "sync" and not args.no_wait), dry_run=dry, say=say)
        return rc
    if args.cmd == "check":
        env = check_env or checkmod.CheckEnv()
        items = checkmod.run_checks(env, theme_env or themesync.RealEnv(), args.profiles or os.environ.get("HEISS_PROFILES", DEFAULT_PROFILES))
        out.write(json.dumps([i.to_dict() for i in items], indent=2) + "\n" if args.json else checkmod.render(items))
        if args.report:
            try:
                with open(os.path.expanduser(args.report), "w", encoding="utf-8") as f:
                    f.write(checkmod.render_report(items, env, "exit code %d" % checkmod.exit_code(items)))
            except OSError as e:
                sys.stderr.write("heiss: cannot write report: %s\n" % e)
                return 1
        return checkmod.exit_code(items)
    system = system or PacmanSystem()
    try:
        if args.cmd == "hw" and args.sub == "remove":
            catalog = hw.load_profiles(_hardware_dir())
            _, _, state_path = _paths(args)
            plan = hwremove.plan_removal(args.id, catalog, mf.load_dir(_paths(args)[0]), st.load(state_path),
                                         system.installed_packages())
            out.write(plan.to_text() + "\n")
            if args.dry_run:
                return 0
            if not args.yes and not (confirm or _ask)("Remove these packages? [y/N] "):
                out.write("cancelled, nothing was changed\n")
                return 1
            (helper or _real_helper()).call("RemoveHardware", (args.id,), lambda line: out.write("  " + line + "\n"))
            out.write("done\n")
            return 0
        if args.cmd == "hw":
            profiles = hw.load_profiles(args.hardware or os.environ.get("HEISS_HARDWARE", DEFAULT_HARDWARE))
            facts = hw.load_fixture(args.fixture) if args.fixture else hw.collect_live()
            report = hw.detect(facts, profiles, hw.capabilities())
            out.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n" if args.json
                      else hw.render_text(report, args.lang))
            return 0
        if args.cmd == "answers":
            doc = ans.load(args.file)
            out.write(json.dumps(doc, indent=2) if args.json else ans.dumps(doc))
            return 0
        if args.sub == "list":
            for m in mf.load_dir(_paths(args)[0]).values():
                out.write("%-22s %-8s %s\n" % (m.id, m.kind, m.name["en"]))
        elif args.sub == "show":
            m = mf.load_dir(_paths(args)[0]).get(args.id)
            if m is None:
                raise HeissError("unknown manifest %r" % args.id)
            out.write(json.dumps(m.__dict__, indent=2, ensure_ascii=False) + "\n")
        elif args.sub == "apply" and not args.dry_run:
            plan = _build(args, system)
            out.write(plan.to_text() + "\n")
            if plan.is_empty():
                out.write("nothing to apply\n")
                return 0
            if not args.yes and not (confirm or _ask)("Apply these changes? [y/N] "):
                out.write("cancelled, nothing was changed\n")
                return 1
            applymod.apply_plan(plan, helper or _real_helper(), system, lambda line: out.write("  " + line + "\n"),
                                on_step=lambda n, total, desc: out.write("[%d/%d] %s\n" % (n, total, desc)))
            out.write("done\n")
        else:
            plan = _build(args, system)
            out.write((json.dumps(plan.to_dict(), indent=2) + "\n") if args.json else plan.to_text() + "\n")
        return 0
    except HeissError as e:
        sys.stderr.write("heiss: %s\n" % e)
        return 1
    except (FileNotFoundError, PermissionError) as e:   # an unreadable state or answers file: say so, no traceback
        sys.stderr.write("heiss: %s\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
