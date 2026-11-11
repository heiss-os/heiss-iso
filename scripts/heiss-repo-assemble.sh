#!/usr/bin/env bash
# Heiss OS: put freshly built packages into the checked-out gh-pages tree of heiss-repo,
# sign them and rebuild the signed database.
# Usage: heiss-repo-assemble.sh PKG_DIR SITE_DIR GPG_KEY_ID
#   PKG_DIR   directory with the built heiss-*.pkg.tar.zst
#   SITE_DIR  checkout of the gh-pages branch of heiss-repo (packages go to SITE_DIR/x86_64)
# The signing key must already be in the gpg keyring (GNUPGHOME), without a passphrase.
# Prints "changed=true|false" (also appended to $GITHUB_OUTPUT when set).
# Rules: a package file that is already published is kept byte for byte (makepkg output is not
# reproducible and a changed file would break the checksum of people who already have it);
# files of versions that are no longer built are removed; nothing is changed if nothing is new.
set -euo pipefail

PKG_DIR="${1:?PKG_DIR}"; SITE_DIR="${2:?SITE_DIR}"; KEY="${3:?GPG_KEY_ID}"
DEST="$SITE_DIR/x86_64"
mkdir -p "$DEST"

shopt -s nullglob
built=("$PKG_DIR"/heiss-*.pkg.tar.zst)
[[ ${#built[@]} -gt 0 ]] || { echo "No packages in $PKG_DIR" >&2; exit 1; }

changed=false
# 1. anything new, or anything published that is no longer built?
declare -A want=()
for p in "${built[@]}"; do
    want["$(basename "$p")"]=1
    [[ -f "$DEST/$(basename "$p")" ]] || changed=true
done
for old in "$DEST"/*.pkg.tar.zst; do
    [[ -n "${want[$(basename "$old")]:-}" ]] || changed=true
done

if [[ $changed == false ]]; then
    echo "Nothing new: every built package is already published."
else
    # 2. drop stale files, add new ones (existing ones stay untouched)
    for old in "$DEST"/*.pkg.tar.zst; do
        [[ -n "${want[$(basename "$old")]:-}" ]] || rm -vf -- "$old" "$old.sig"
    done
    for p in "${built[@]}"; do
        f="$DEST/$(basename "$p")"
        [[ -f "$f" ]] || cp -v -- "$p" "$f"
        [[ -f "$f.sig" ]] || gpg --batch --yes --pinentry-mode loopback -u "$KEY" --detach-sign --no-armor -o "$f.sig" "$f"
    done
    # 3. fresh signed database (real files, no symlinks: GitHub Pages serves plain files)
    rm -f -- "$DEST"/heiss.db* "$DEST"/heiss.files*
    (cd "$DEST" && repo-add --sign --key "$KEY" heiss.db.tar.zst ./heiss-*.pkg.tar.zst)
    for n in db files; do
        for ext in "" ".sig"; do
            cp --remove-destination -L -- "$DEST/heiss.$n.tar.zst$ext" "$DEST/heiss.$n$ext"
        done
    done
fi

# 4. plain index pages (GitHub Pages has no directory listing). Deterministic content, so an
#    unchanged repository stays unchanged; a changed page alone also counts as a change.
write_page() {  # write_page FILE  (content on stdin)
    local tmp; tmp="$(mktemp)"; cat > "$tmp"
    if [[ -f "$1" ]] && cmp -s "$tmp" "$1"; then rm -f "$tmp"; else mv "$tmp" "$1"; chmod 644 "$1"; changed=true; fi
}
write_page "$DEST/index.html" < <(
    echo '<!doctype html><meta charset="utf-8"><title>Heiss OS package repository: x86_64</title>'
    echo '<h1>Heiss OS package repository: x86_64</h1>'
    echo '<p>Pacman server line: <code>Server = https://heiss-os.github.io/heiss-repo/$arch</code>. Not an official Arch Linux repository.</p><ul>'
    (cd "$DEST" && LC_ALL=C ls -1 | grep -v '^index\.html$') | while read -r f; do
        # "./" keeps a name with ':' (epoch) from being read as a URL scheme
        href="$(printf '%s' "$f" | sed 's/%/%25/g; s/ /%20/g; s/"/%22/g; s/</%3C/g; s/>/%3E/g; s/#/%23/g; s/?/%3F/g; s/&/\&amp;/g')"
        text="$(printf '%s' "$f" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')"
        echo "<li><a href=\"./$href\">$text</a></li>"
    done
    echo '</ul>'
)
write_page "$SITE_DIR/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Heiss OS package repository</title><h1>Heiss OS package repository</h1><p>Pacman repository for Heiss OS: <code>$arch/heiss.db</code>. Not an official Arch Linux repository.</p><p><a href="x86_64/">x86_64 files</a></p>
HTML

echo "changed=$changed"
[[ -z "${GITHUB_OUTPUT:-}" ]] || echo "changed=$changed" >> "$GITHUB_OUTPUT"
