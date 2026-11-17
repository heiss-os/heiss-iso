#!/usr/bin/env bash
# Heiss OS: repeatable, read-only inspection of a built ISO. Prints one line per check: OK, WARN or FAIL.
# Needs no root: the squashfs is unpacked in part with unsquashfs as a normal user (only /etc, /usr/share
# branding and the pacman database), the boot files are read from the ISO with bsdtar.
#
# Usage:  scripts/audit-image.sh path/to/heiss-*.iso
#         scripts/audit-image.sh --root DIR [--boot DIR]    (a tree that is already unpacked; used by the tests)
# Exit status: 0 no FAIL, 1 at least one FAIL, 2 wrong usage or a tool is missing.
#
# The work directory is a normal directory (default /var/tmp, never tmpfs: the squashfs alone is about 2 GB).
# Set AUDIT_TMP to use another parent directory. It is removed at the end only if it is a real directory
# of the form <parent>/heiss-audit.XXXXXX that this script created (see cleanup).
set -uo pipefail

PASS=0 WARN=0 FAIL=0
ok()   { printf 'OK    %s\n' "$*"; PASS=$((PASS + 1)); }
warn() { printf 'WARN  %s\n' "$*"; WARN=$((WARN + 1)); }
fail() { printf 'FAIL  %s\n' "$*"; FAIL=$((FAIL + 1)); }
info() { printf 'INFO  %s\n' "$*"; }
usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

ISO="" ROOT="" BOOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --root) ROOT="${2:-}"; shift 2 ;;
        --boot) BOOT="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        -*) echo "unknown option: $1" >&2; usage ;;
        *) [[ -z $ISO ]] || usage; ISO="$1"; shift ;;
    esac
done
[[ -n $ISO || -n $ROOT ]] || usage
[[ -z $ISO || -z $ROOT ]] || usage

WORK=""
cleanup() {
    # guarded delete: only a directory this script made with mktemp, never a link, never a short path
    if [[ -n $WORK && ! -L $WORK && -d $WORK && $WORK == */heiss-audit.* && ${#WORK} -gt 20 ]]; then
        chmod -R u+rwX -- "$WORK" 2>/dev/null     # the unpacked image has read-only directories (mode 555)
        rm -rf -- "$WORK"
    fi
}
trap cleanup EXIT

if [[ -n $ISO ]]; then
    for t in unsquashfs bsdtar; do command -v "$t" >/dev/null || { echo "$t is not installed" >&2; exit 2; }; done
    [[ -f $ISO ]] || { echo "no such file: $ISO" >&2; exit 2; }
    parent="${AUDIT_TMP:-/var/tmp}"
    [[ -d $parent && ! -L $parent ]] || { echo "temporary parent is not a directory: $parent" >&2; exit 2; }
    fstype="$(stat -f -c %T -- "$parent")"
    [[ $fstype != tmpfs && $fstype != ramfs ]] || { echo "$parent is $fstype (memory): set AUDIT_TMP to a directory on disk" >&2; exit 2; }
    WORK="$(mktemp -d -p "$parent" heiss-audit.XXXXXX)" || exit 2
    chmod 700 "$WORK"
    ROOT="$WORK/root" BOOT="$WORK/boot"
    mkdir -p "$ROOT" "$BOOT"
    info "image: $ISO ($(stat -c %s -- "$ISO" | awk '{printf "%.2f GiB", $1 / 1073741824}'))"
    if ! bsdtar -xf "$ISO" -C "$BOOT" --include 'loader/*' --include 'boot/grub/*' --include 'boot/syslinux/*' --include 'EFI/*' 2>/dev/null; then
        warn "boot files could not be read from the ISO"
    fi
    sfs="$WORK/airootfs.sfs"
    bsdtar -xf "$ISO" -C "$WORK" --include 'arch/x86_64/airootfs.sfs' 2>/dev/null
    mv -f "$WORK/arch/x86_64/airootfs.sfs" "$sfs" 2>/dev/null || { fail "arch/x86_64/airootfs.sfs not found in the ISO"; exit 1; }
    info "airootfs.sfs: $(stat -c %s -- "$sfs" | awk '{printf "%.0f MiB", $1 / 1048576}')"
    # only what the checks read; -no-xattrs and -ig because a normal user cannot create device nodes or set owners
    unsquashfs -f -no-xattrs -ig -d "$ROOT" "$sfs" etc usr/lib/os-release usr/share/heiss usr/share/applications \
        usr/share/calamares usr/share/plasma/look-and-feel usr/share/pacman usr/share/libalpm \
        usr/lib/systemd/system usr/local/bin var/lib/pacman/local >/dev/null 2>&1 || true
    [[ -d $ROOT/etc ]] || { fail "could not unpack /etc from the squashfs"; exit 1; }
fi
[[ -d $ROOT ]] || { echo "no such directory: $ROOT" >&2; exit 2; }

r() { printf '%s/%s' "$ROOT" "$1"; }
mode() { stat -c %a -- "$1" 2>/dev/null; }

# ---- identity: nothing a user sees may say Arch Linux --------------------------------------------------------
section() { printf '\n== %s\n' "$*"; }
section "identity"
osr="$(r usr/lib/os-release)"; [[ -f $osr ]] || osr="$(r etc/os-release)"
if [[ -f $osr ]]; then
    name="$(grep -E '^(NAME|PRETTY_NAME)=' "$osr" || true)"
    if grep -qi 'arch' <<<"$name"; then fail "os-release NAME/PRETTY_NAME mentions Arch: $name"; else ok "os-release names Heiss OS ($(grep -E '^PRETTY_NAME=' "$osr" | head -1))"; fi
else
    fail "no os-release in the image"
fi
for f in etc/issue etc/motd; do
    if [[ -f $(r "$f") ]] && grep -qi 'arch linux' "$(r "$f")"; then fail "$f says Arch Linux"; else ok "$f has no Arch Linux text"; fi
done
if [[ -f $(r usr/share/heiss/lsb-release) ]]; then ok "usr/share/heiss/lsb-release is shipped (the pacman hook restores /etc/lsb-release from it)"; else warn "usr/share/heiss/lsb-release is missing"; fi
if [[ -f $(r etc/lsb-release) ]]; then info "/etc/lsb-release exists in the live image"; else info "/etc/lsb-release does not exist in the live image (the lsb-release package is not installed: fine)"; fi

# user-visible text: desktop entries, installer branding, Plasma look-and-feel, boot menus
hits=""
while IFS= read -r f; do
    if grep -HniE '^(Name|GenericName|Comment|Name\[[a-z_]+\]|Comment\[[a-z_]+\])=.*arch linux' "$f" >/dev/null 2>&1; then hits+="${f#"$ROOT"/} "; fi
done < <(find "$(r usr/share/applications)" -name '*.desktop' 2>/dev/null)
[[ -z $hits ]] && ok "desktop entries: no Arch Linux in names or comments" || warn "desktop entries mention Arch Linux: $hits"
user_hits="$(grep -rIli 'arch linux' "$(r usr/share/calamares)" "$(r usr/share/plasma/look-and-feel)" "$(r etc/calamares)" 2>/dev/null | sed "s|^$ROOT/||" | tr '\n' ' ')"
[[ -z $user_hits ]] && ok "installer branding and look-and-feel: no Arch Linux text" || warn "Arch Linux text in: $user_hits"
if [[ -d $BOOT ]] && [[ -n "$(find "$BOOT" -type f 2>/dev/null | head -1)" ]]; then
    # only the lines a person reads (title, MENU LABEL, menuentry), not internal label ids such as "LABEL arch"
    boot_hits="$(grep -rInE '^\s*(title|MENU LABEL|MENU TITLE)\b.*([Aa]rch Linux|\bArch\b)|^\s*menuentry\s+["'"'"'][^"'"'"']*([Aa]rch Linux|\bArch\b)' "$BOOT" 2>/dev/null | sed "s|^$BOOT/||" | head -5 | tr '\n' ' ')"
    [[ -z $boot_hits ]] && ok "boot menus (loader, GRUB, syslinux): no Arch in titles" || fail "boot menu title mentions Arch: $boot_hits"
    if find "$BOOT" -iname 'shell*.efi' | grep -q .; then warn "an EFI shell binary is in the boot files"; else ok "no EFI shell entry in the boot files"; fi
else
    warn "no boot files to check"
fi

# ---- telemetry and phone-home ------------------------------------------------------------------------------------
section "telemetry and units that call out"
enabled="$(find "$(r etc/systemd)" \( -path '*.wants/*' -o -path '*.requires/*' \) -printf '%f\n' 2>/dev/null | sort -u)"
bad="$(grep -iE 'telemetry|popcon|whoopsie|abrt|kuserfeedback|cloud-init|reflector|ping|phone|metrics|analytics' <<<"$enabled" | tr '\n' ' ')"
[[ -z $bad ]] && ok "no enabled unit looks like telemetry, reflector or cloud-init" || fail "enabled units that call out or phone home: $bad"
nm="$(r etc/NetworkManager/conf.d/20-connectivity.conf)"
if [[ -f $nm ]] && grep -qE '^enabled\s*=\s*false' "$nm"; then ok "NetworkManager connectivity check is off"; else fail "NetworkManager connectivity check is not switched off (20-connectivity.conf)"; fi
tr_conf="$(r etc/calamares/modules/tracking.conf)"
if [[ -f $tr_conf ]]; then
    if grep -qE '^\s+enabled:\s*true' "$tr_conf"; then fail "Calamares tracking is enabled"; else ok "Calamares tracking is off"; fi
fi
if grep -qE '(^|[^a-z])tracking($|[^a-z])' "$(r etc/calamares/settings.conf)" 2>/dev/null; then fail "Calamares settings.conf lists a tracking module"; else ok "no tracking module in the Calamares sequence"; fi

# ---- permissions ---------------------------------------------------------------------------------------------------
section "permissions"
for f in etc/shadow etc/gshadow; do
    m="$(mode "$(r "$f")")"
    if [[ -z $m ]]; then fail "$f is missing"; elif (( 8#$m & 8#077 )); then fail "$f is mode $m (expected 400 or 600)"; else ok "$f is mode $m"; fi
done
ww="$(find "$ROOT" -xdev -type f -perm -0002 2>/dev/null | sed "s|^$ROOT/||" | head -5 | tr '\n' ' ')"
[[ -z $ww ]] && ok "no world-writable files among the unpacked ones" || fail "world-writable files: $ww"
sw="$(find "$(r etc/sudoers.d)" -type f 2>/dev/null | while read -r f; do m="$(mode "$f")"; (( 8#$m & 8#033 )) && echo "${f##*/}:$m"; done | tr '\n' ' ')"
[[ -z $sw ]] && ok "sudoers.d files are not writable by group or others" || fail "sudoers.d permissions: $sw"
if [[ -f $(r etc/shadow) ]] && grep -qE '^root:[^!*]' "$(r etc/shadow)"; then info "root has a password hash in the live image (the live session; cleanup locks it after install)"; fi

# ---- packages and repository -------------------------------------------------------------------------------------
section "pacman, keys and package set"
if [[ -f $(r usr/share/pacman/keyrings/heiss.gpg) && -f $(r usr/share/pacman/keyrings/heiss-trusted) ]]; then
    if grep -q 'DDD292CCC8613FD3324D3833FEA84CEF8AEDF132' "$(r usr/share/pacman/keyrings/heiss-trusted)"; then ok "heiss keyring is present with the pinned fingerprint"; else fail "heiss-trusted does not hold the pinned fingerprint"; fi
else
    fail "heiss keyring files are missing (heiss-keyring package)"
fi
# heiss-cleanup.sh appends the section with printf '\n[heiss]\n...' after the install; a plain pacman.conf has it on a line
if grep -qsE '(^|\\n)\[heiss\]' "$(r usr/local/bin/heiss-cleanup.sh)" "$(r etc/pacman.conf)" 2>/dev/null; then ok "the [heiss] repository section is set up (pacman.conf or the install cleanup)"; else fail "no [heiss] section in pacman.conf or heiss-cleanup.sh"; fi
if grep -qs 'SigLevel = Required DatabaseRequired' "$(r usr/local/bin/heiss-cleanup.sh)" "$(r etc/pacman.conf)"; then ok "[heiss] requires signatures"; else fail "no 'SigLevel = Required DatabaseRequired' for [heiss]"; fi
db="$(r var/lib/pacman/local)"
if [[ -d $db ]]; then
    n="$(find "$db" -mindepth 1 -maxdepth 1 -type d | wc -l)"
    size="$(find "$db" -name desc -print0 | xargs -0 -r awk '/^%SIZE%/ {getline; s += $1} END {printf "%.0f", s / 1048576}')"
    info "packages in the image: $n, installed size about ${size} MiB"
    for p in heiss-core heiss-helper heiss-theme heiss-keyring heiss-welcome heiss-control heiss-safe-graphics heiss-profile-base; do
        if compgen -G "$db/$p-[0-9]*" >/dev/null; then ok "package $p is in the image"; else fail "package $p is missing"; fi
    done
    for p in refind arch-install-scripts; do
        if compgen -G "$db/$p-[0-9]*" >/dev/null; then warn "$p is in the live image (removed from the installed system by the cleanup)"; fi
    done
else
    warn "no pacman database unpacked"
fi
sg="$(r etc/grub.d/41_heiss_safe)"
if [[ -f $sg ]]; then
    m="$(mode "$sg")"
    if (( 8#$m & 8#100 )) && grep -q 'nomodeset' "$sg"; then ok "safe-graphics grub script is executable and adds nomodeset"; else fail "41_heiss_safe is not executable (mode $m) or has no nomodeset"; fi
else
    fail "etc/grub.d/41_heiss_safe is missing (heiss-safe-graphics)"
fi

printf '\n%d OK, %d WARN, %d FAIL\n' "$PASS" "$WARN" "$FAIL"
[[ $FAIL -eq 0 ]]
