#!/usr/bin/env bash
# Test of heiss-repo-assemble.sh with a throwaway key: new, unchanged and stale-removal cases.
# Usage: test-repo-assemble.sh PKG_DIR   (needs a GNUPGHOME with a signing key in $KEY, see workflow)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PK="${1:?PKG_DIR}"; : "${KEY:?KEY}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
run() { bash "$HERE/heiss-repo-assemble.sh" "$@" | tail -1; }

[[ "$(run "$PK" "$T/s" "$KEY")" == changed=true ]] || fail "first run must change"
[[ -s $T/s/x86_64/heiss.db && -s $T/s/x86_64/heiss.db.sig ]] || fail "signed db missing"
[[ ! -L $T/s/x86_64/heiss.db ]] || fail "heiss.db must not be a symlink"
sum="$(sha256sum "$T"/s/x86_64/*.pkg.tar.zst | sort)"
[[ "$(run "$PK" "$T/s" "$KEY")" == changed=false ]] || fail "second run must not change"
[[ "$(sha256sum "$T"/s/x86_64/*.pkg.tar.zst | sort)" == "$sum" ]] || fail "published files changed"

# stale: one package no longer built -> its files go away, the rest stays byte for byte
mkdir "$T/pk2"; cp "$PK"/heiss-*.pkg.tar.zst "$T/pk2/"
gone="$(ls "$T"/pk2/ | head -1)"; rm "$T/pk2/$gone"
[[ "$(run "$T/pk2" "$T/s" "$KEY")" == changed=true ]] || fail "stale run must change"
[[ ! -e $T/s/x86_64/$gone && ! -e $T/s/x86_64/$gone.sig ]] || fail "stale package kept"
echo "OK: assemble logic (new, unchanged, stale)"
