#!/usr/bin/env bash
# Heiss OS: build every package under packages/ (heiss-core, heiss-helper, heiss-profile-*)
# and add them to the local repository that the ISO build uses.
# Usage: heiss-packages-build.sh   (normal user, in the build VM; makepkg refuses root)
# The sources of heiss-core and heiss-helper are taken from git HEAD: uncommitted changes
# are NOT included, so the ISO only ever contains reviewed, committed code.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCALREPO="${LOCALREPO:-$HOME/localrepo}"
[[ $EUID -ne 0 ]] || { echo "Run as a normal user, makepkg refuses root" >&2; exit 1; }

echo "==> Checking generated package files are up to date"
python3 "$REPO_DIR/scripts/gen-profile-packages.py" --check

if ! git -C "$REPO_DIR" diff --quiet HEAD -- core helper welcome profiles hardware packages branding/tokens; then
    echo "WARNING: uncommitted changes in core/ helper/ welcome/ profiles/ hardware/ packages/ branding/tokens/ are NOT part of the build (git HEAD is used)" >&2
fi
echo "==> Building from commit $(git -C "$REPO_DIR" rev-parse --short HEAD)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$LOCALREPO" "$WORK/out"
git -C "$REPO_DIR" archive --format=tar.gz --prefix=heiss-src/ -o "$WORK/heiss-src.tar.gz" HEAD core helper profiles hardware branding/tokens welcome docs/infra/heiss-public.asc

for dir in "$REPO_DIR"/packages/heiss-*/; do
    name="$(basename "$dir")"
    echo "==> Building $name"
    cp -r "$dir" "$WORK/$name"
    cp "$WORK/heiss-src.tar.gz" "$WORK/$name/"
    # -d: dependencies are ordinary repository packages, not needed to build an 'any' package
    (cd "$WORK/$name" && PKGDEST="$WORK/out" makepkg -d -f -C --noconfirm)
done

echo "==> Adding to $LOCALREPO"
cp -v "$WORK"/out/*.pkg.tar.zst "$LOCALREPO"/
(cd "$LOCALREPO" && repo-add heiss-local.db.tar.zst ./heiss-*.pkg.tar.zst)
echo "Done. Now build the ISO."
