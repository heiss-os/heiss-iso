"""heiss command line: profile list|show|diff|apply, hw detect, answers validate.

`apply` shows the plan, asks for confirmation and runs it through the privileged
helper (D-Bus + polkit). `--dry-run` only prints the plan.
"""
import argparse
import json
import os
import sys

from . import answers as ans
from . import apply as applymod
from . import hardware as hw
from . import manifest as mf
from . import resolver, state as st
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


def _build(args, system=None):
    prof_dir, answers_path, state_path = _paths(args)
    manifests = mf.load_dir(prof_dir)
    if args.profile:
        doc = ans.validate({"profile": args.profile, "addons": args.addon or []},
                           _kinds(manifests, "profile"), _kinds(manifests, "addon"))
    else:
        doc = ans.load(answers_path, known_profiles=_kinds(manifests, "profile"),
                       known_addons=_kinds(manifests, "addon"))
    plan = resolver.resolve(doc, manifests, st.load(state_path), system or PacmanSystem(),
                            adopt=getattr(args, "adopt", False))
    return plan


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


def main(argv=None, system=None, out=sys.stdout, helper=None, confirm=None):
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
        if name == "apply":
            sp.add_argument("--dry-run", action="store_true")
            sp.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    hwp = sub.add_parser("hw").add_subparsers(dest="sub", required=True)
    det = hwp.add_parser("detect", help="read-only hardware detection and proposals")
    det.add_argument("--hardware", help="directory with hardware profiles")
    det.add_argument("--fixture", help="use a recorded fixture directory instead of the live system")
    det.add_argument("--lang", choices=("en", "ru"), default="en")
    av = sub.add_parser("answers").add_subparsers(dest="sub", required=True)
    v = av.add_parser("validate")
    v.add_argument("file")
    args = p.parse_args(argv)
    system = system or PacmanSystem()
    try:
        if args.cmd == "hw":
            profiles = hw.load_profiles(args.hardware or os.environ.get("HEISS_HARDWARE", DEFAULT_HARDWARE))
            facts = hw.load_fixture(args.fixture) if args.fixture else hw.collect_live()
            report = hw.detect(facts, profiles)
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
    except FileNotFoundError as e:
        sys.stderr.write("heiss: %s\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
