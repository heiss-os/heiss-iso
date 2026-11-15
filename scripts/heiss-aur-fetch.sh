#!/usr/bin/env bash
# Heiss OS: fetch an AUR recipe at ONE reviewed commit and check its PKGBUILD, or fail.
# usage: heiss-aur-fetch.sh URL DIR COMMIT PKGBUILD_SHA256
#   URL    git URL of the AUR repository
#   DIR    directory to create (removed first); never "/" or the home directory
#   COMMIT full 40-character commit that was reviewed
#   PKGBUILD_SHA256  sha256 of the PKGBUILD at that commit
# A later commit in the AUR repository is never used, so an account takeover or a push after the review
# cannot change what is built. To move to a new version: read `git diff OLD..NEW` of the AUR repository
# (PKGBUILD, sources, checksums, install scripts), then change both pins in the caller.
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "usage: $0 URL DIR COMMIT PKGBUILD_SHA256" >&2
    exit 2
fi
url=$1 dir=$2 commit=$3 want_sha=$4

[[ $commit =~ ^[0-9a-f]{40}$ ]] || { echo "COMMIT must be 40 lowercase hex digits" >&2; exit 2; }
[[ $want_sha =~ ^[0-9a-f]{64}$ ]] || { echo "PKGBUILD_SHA256 must be 64 lowercase hex digits" >&2; exit 2; }
case "$dir" in
    ""|"/"|"$HOME"|"$HOME/") echo "refusing to use '$dir' as the target directory" >&2; exit 2 ;;
esac

rm -rf -- "$dir"
git clone --quiet -- "$url" "$dir"
git -C "$dir" -c advice.detachedHead=false checkout --quiet --detach "$commit" ||
    { echo "commit $commit is not in $url (rewritten history?): do not build, review the repository again" >&2; exit 1; }

head=$(git -C "$dir" rev-parse HEAD)
[ "$head" = "$commit" ] || { echo "checked out $head, expected $commit" >&2; exit 1; }
[ -z "$(git -C "$dir" status --porcelain)" ] || { echo "the checkout is not clean" >&2; exit 1; }
[ -f "$dir/PKGBUILD" ] || { echo "no PKGBUILD in $dir" >&2; exit 1; }

got_sha=$(sha256sum -- "$dir/PKGBUILD" | cut -d' ' -f1)
if [ "$got_sha" != "$want_sha" ]; then
    echo "PKGBUILD sha256 is $got_sha, expected $want_sha" >&2
    exit 1
fi
echo "==> $url at $commit, PKGBUILD sha256 $got_sha: as reviewed"
