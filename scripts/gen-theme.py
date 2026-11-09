#!/usr/bin/env python3
"""Generate theme files from branding/tokens/heiss-tokens.json (stdlib only).

  gen-theme.py           write outputs into branding/tokens/generated/
  gen-theme.py --check   exit 1 if the committed outputs differ from regeneration

Outputs never overwrite files that ship in the image; they are staged for the
heiss-theme package (Phase 10).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heiss_tokens as h  # noqa: E402

OUT = os.path.join(h.ROOT, "branding", "tokens", "generated")


def outputs(tokens):
    files = {}
    for th in h.THEMES:
        sid = tokens["themes"][th]["scheme_id"]
        files["kde/%s.colors" % sid] = h.render_kde_scheme(tokens, th)
        files["gtk-3.0/heiss-%s.css" % th] = h.render_gtk(tokens, th, gtk4=False)
        files["gtk-4.0/heiss-%s.css" % th] = h.render_gtk(tokens, th, gtk4=True)
        files["kitty/heiss-%s.conf" % th] = h.render_kitty(tokens, th)
        files["konsole/%s.colorscheme" % sid] = h.render_konsole(tokens, th)
        files["konsole/Heiss-%s.profile" % th.capitalize()] = h.render_konsole_profile(tokens, th)
        files["kitty/%s-theme.auto.conf" % th] = h.render_kitty(tokens, th)
    files["konsole/konsolerc"] = h.render_konsolerc()
    files["kitty/kitty.conf"] = h.render_kitty_conf(tokens)
    files["kitty/no-preference-theme.auto.conf"] = h.render_kitty(tokens, "dark")   # no preference: dark is the default look
    return files


def main(argv):
    check = "--check" in argv
    files = outputs(h.load())
    bad = []
    for rel, text in sorted(files.items()):
        path = os.path.join(OUT, rel)
        if check:
            try:
                with open(path, encoding="utf-8") as f:
                    if f.read() != text:
                        bad.append(rel)
            except FileNotFoundError:
                bad.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print("wrote", os.path.relpath(path, h.ROOT))
    if check:
        # stale files that the generator no longer produces
        for dp, _, fns in os.walk(OUT):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), OUT)
                if rel not in files:
                    bad.append(rel + " (stale)")
        if bad:
            print("generated files out of date, run scripts/gen-theme.py:", *bad, sep="\n  ")
            return 1
        print("generated files up to date (%d)" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
