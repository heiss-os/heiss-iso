#!/usr/bin/env bash
# Heiss OS: run shellcheck on every shell script of the repository (files with a sh/bash shebang).
# Warnings and errors fail the run; the style notes are switched off in .shellcheckrc with reasons.
# Usage: scripts/check-shell.sh   (needs shellcheck; run from anywhere inside the repository)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Tier A files (docs/design/protected-paths.txt) with a finding that is justified, not hidden. Changing them
# needs the design-approved label; take them off this list in the same change that fixes them.
#   heiss-setup-dock.sh       SC2034: the loop counter "i" of a bounded wait loop is not used
#   heiss-calamares-build.sh  SC2155: "export MAKEFLAGS=-j$(nproc)" masks the exit status of nproc, harmless
SKIP=(
    profile/airootfs/usr/local/bin/heiss-setup-dock.sh
    scripts/heiss-calamares-build.sh
)

command -v shellcheck >/dev/null || { echo "shellcheck is not installed" >&2; exit 2; }

files=()
while IFS= read -r -d '' f; do
    [[ -f $f && ! -L $f ]] || continue
    first=""
    IFS= read -r first < "$f" 2>/dev/null || true       # binary files hold no shebang and are skipped below
    first="${first//$'\r'/}"
    [[ $first =~ ^#!\ *(/usr/bin/env\ +)?(/bin/|/usr/bin/)?(ba)?sh([[:space:]]|$) ]] || continue
    skip=false
    for s in "${SKIP[@]}"; do [[ $f == "$s" ]] && skip=true; done
    $skip || files+=("$f")
done < <(git ls-files -z)

echo "shellcheck: ${#files[@]} scripts, ${#SKIP[@]} skipped (see the list in this script)"
shellcheck --severity=warning "${files[@]}"
echo "shellcheck: ok"
