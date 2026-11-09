#!/usr/bin/env bash
# Heiss OS: build the heiss-profile-* metapackages and add them to the local repository.
# Usage: heiss-profile-build.sh   (run as a normal user in the build VM, not as root)
# Does not touch profile/packages.x86_64: the ISO only gets these packages when they are listed there.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCALREPO="${LOCALREPO:-$HOME/localrepo}"
[[ $EUID -ne 0 ]] || { echo "Run as a normal user, makepkg refuses root" >&2; exit 1; }

echo "==> Checking generated package files are up to date"
python3 "$REPO_DIR/scripts/gen-profile-packages.py" --check

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$LOCALREPO" "$WORK/out"

for dir in "$REPO_DIR"/packages/heiss-profile-*/; do
    name="$(basename "$dir")"
    echo "==> Building $name"
    cp -r "$dir" "$WORK/$name"
    # -d: the dependencies are ordinary repository packages, they are not needed to build an 'any' metapackage
    (cd "$WORK/$name" && PKGDEST="$WORK/out" makepkg -d -f -C --noconfirm)
done

echo "==> Adding to $LOCALREPO"
cp -v "$WORK"/out/*.pkg.tar.zst "$LOCALREPO"/
(cd "$LOCALREPO" && repo-add heiss-local.db.tar.zst ./heiss-profile-*.pkg.tar.zst)
echo "Done."
