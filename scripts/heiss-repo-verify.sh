#!/usr/bin/env bash
# Heiss OS: check that real pacman accepts the assembled repository with SigLevel Required
# DatabaseRequired, trusting only the given public key. Needs root (pacman-key) and pacman.
# Usage: heiss-repo-verify.sh REPO_DIR PUBLIC_KEY_FILE
#   REPO_DIR  the x86_64 directory (heiss.db, heiss.db.sig, packages and their .sig)
# Uses a temporary pacman configuration, database and keyring; the host's pacman is not touched.
set -euo pipefail

REPO="$(cd "${1:?REPO_DIR}" && pwd)"; PUB="$(cd "$(dirname "${2:?PUBLIC_KEY_FILE}")" && pwd)/$(basename "$2")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/db" "$T/cache"

pacman-key --gpgdir "$T/gpg" --init  >/dev/null
pacman-key --gpgdir "$T/gpg" --add "$PUB"  >/dev/null
fpr="$(gpg --batch --show-keys --with-colons "$PUB" | awk -F: '/^fpr:/ {print $10; exit}')"
pacman-key --gpgdir "$T/gpg" --lsign-key "$fpr"  >/dev/null

cat > "$T/pacman.conf" <<CONF
[options]
Architecture = x86_64
DBPath = $T/db
CacheDir = $T/cache
GPGDir = $T/gpg
LogFile = $T/pacman.log
SigLevel = Required DatabaseRequired
[heiss]
Server = file://$REPO
CONF

pacman --config "$T/pacman.conf" -Sy
pacman --config "$T/pacman.conf" -Sl heiss
# -dd: dependencies are ordinary Arch packages that this temporary config does not know
mapfile -t names < <(pacman --config "$T/pacman.conf" -Sl heiss | awk '{print $2}')
pacman --config "$T/pacman.conf" -Sdd -w --noconfirm "${names[@]}"
echo "OK: pacman accepted the database and ${#names[@]} signed package(s) from $REPO"
