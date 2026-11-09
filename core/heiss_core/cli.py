"""heiss command line: profile list|show|diff|apply, answers validate.

`apply` without --dry-run needs the privileged helper (Phase 3) and refuses for now.
"""
import argparse
import json
import os
import sys

from . import answers as ans
from . import manifest as mf
from . import resolver, state as st
from .errors import HeissError
from .system import PacmanSystem

DEFAULT_PROFILES = "/usr/share/heiss/profiles"
DEFAULT_ETC = "/etc/heiss"
DEFAULT_STATE = "/var/lib/heiss/state.json"


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


def main(argv=None, system=None, out=sys.stdout):
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
    av = sub.add_parser("answers").add_subparsers(dest="sub", required=True)
    v = av.add_parser("validate")
    v.add_argument("file")
    args = p.parse_args(argv)
    try:
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
            raise HeissError("applying changes needs the privileged helper (not implemented yet); use --dry-run")
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
