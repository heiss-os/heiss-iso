#!/usr/bin/env bash
# Developer tool: build the GRUB theme fonts from the shipped Inter files.
#
# GRUB fonts (.pf2) are 1-bit bitmaps: there is no anti-aliasing. Inter Regular has hairline strokes (about 1.5
# px at 20 px) that break into gaps and steps in 1-bit, which is the "jagged, holey" text seen in the first real
# install. Inter Medium keeps its strokes at least 2 px wide at these sizes and renders solid (checked by
# rendering the glyph bitmaps of the .pf2 files). H4 tried 18, 22 and 26 px in Regular, Medium and SemiBold: at 26 px
# Medium has 3 px stems (24 px had 2 px), which is the cleanest result in 1-bit, so 26 px is for the menu entries and
# 18 px (2 px stems) for the footer label and the terminal.
#
#   scripts/gen-grub-fonts.sh           write the two fonts (18 and 26) into the theme directory
#   scripts/gen-grub-fonts.sh --check   exit 1 when the committed fonts differ from a fresh build
#
# Needs grub-mkfont (package grub). It prints many "unsupported font feature" warnings for Inter; they are
# harmless and hidden here.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/branding/fonts/static/Inter-Medium.ttf"
dest="$root/profile/airootfs/usr/share/heiss/grub-theme"
command -v grub-mkfont >/dev/null || { echo "grub-mkfont not found (package grub)" >&2; exit 2; }
[ -f "$src" ] || { echo "missing $src" >&2; exit 2; }
work="$(mktemp -d "${TMPDIR:-/var/tmp}/heiss-grub-fonts.XXXXXX")"
trap '[ -n "${work:-}" ] && [ -d "$work" ] && rm -rf -- "$work"' EXIT
bad=0
for size in 18 26; do
  name="inter-medium-$size.pf2"
  grub-mkfont -s "$size" -n "Inter Medium" -o "$work/$name" "$src" 2>/dev/null
  if [ "${1:-}" = "--check" ]; then
    if cmp -s "$work/$name" "$dest/$name"; then echo "$name: ok"; else echo "$name: DIFFERENT"; bad=1; fi
  else
    install -m 0644 "$work/$name" "$dest/$name"; echo "wrote $dest/$name"
  fi
done
exit "$bad"
