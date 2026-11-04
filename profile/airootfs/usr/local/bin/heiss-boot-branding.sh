#!/usr/bin/env bash
# Heiss OS: boot chain branding for the INSTALLED system (Plymouth splash + GRUB theme).
# Runs inside the target chroot from Calamares (shellprocess@boot), after unpackfs and BEFORE
# shellprocess@cleanup (which runs mkinitcpio -P) and BEFORE the bootloader module
# (which runs grub-install + grub-mkconfig). Disable: set HEISS_BOOT_BRANDING=0 or remove
# "shellprocess@boot" from the exec sequence in settings.conf. Not used on the live ISO.
set -u
log() { echo "[heiss-boot-branding] $*"; }
[ "${HEISS_BOOT_BRANDING:-1}" = 0 ] && { log "disabled"; exit 0; }

# ---- Plymouth -------------------------------------------------------------------------
if [ -d /usr/share/plymouth/themes/heiss ] && command -v plymouth-set-default-theme >/dev/null; then
  log "plymouth theme heiss"
  plymouth-set-default-theme heiss || log "WARNING: plymouth-set-default-theme failed"
  # mkinitcpio hook: after udev (plymouth needs the DRM/KMS devices), before filesystems/encrypt.
  # The archiso drop-in (mkinitcpio.conf.d/archiso.conf) is removed by heiss-cleanup.sh, so the
  # HOOKS line of /etc/mkinitcpio.conf is what the installed initramfs uses.
  if ! grep -Eq '^HOOKS=.*\bplymouth\b' /etc/mkinitcpio.conf; then
    if grep -Eq '^HOOKS=.*\budev\b' /etc/mkinitcpio.conf; then
      sed -i -E '/^HOOKS=/ s/\budev\b/udev plymouth/' /etc/mkinitcpio.conf
    elif grep -Eq '^HOOKS=.*\bsystemd\b' /etc/mkinitcpio.conf; then
      sed -i -E '/^HOOKS=/ s/\bsystemd\b/systemd plymouth/' /etc/mkinitcpio.conf
    else
      log "WARNING: no udev/systemd in HOOKS, plymouth hook not added"
    fi
  fi
  grep -E '^HOOKS=' /etc/mkinitcpio.conf
fi

# ---- GRUB defaults + theme --------------------------------------------------------------
G=/etc/default/grub
setvar() { # setvar KEY VALUE  (VALUE already quoted if needed)
  if grep -Eq "^#?$1=" "$G"; then sed -i -E "s|^#?$1=.*|$1=$2|" "$G"; else echo "$1=$2" >> "$G"; fi
}
if [ -f "$G" ]; then
  log "grub defaults"
  setvar GRUB_DISTRIBUTOR '"Heiss OS"'
  setvar GRUB_CMDLINE_LINUX_DEFAULT '"loglevel=3 quiet splash"'
  setvar GRUB_TIMEOUT_STYLE menu
  # 3 s, unless other operating systems are found (then 5 s and os-prober on)
  if command -v os-prober >/dev/null && [ -n "$(os-prober 2>/dev/null)" ]; then
    setvar GRUB_TIMEOUT 5
    setvar GRUB_DISABLE_OS_PROBER false
  else
    setvar GRUB_TIMEOUT 3
  fi
  if [ -d /usr/share/heiss/grub-theme ]; then
    install -d /boot/grub/themes/heiss
    cp -a /usr/share/heiss/grub-theme/. /boot/grub/themes/heiss/
    setvar GRUB_THEME '"/boot/grub/themes/heiss/theme.txt"'
    setvar GRUB_TERMINAL_OUTPUT gfxterm
    setvar GRUB_GFXMODE auto
    setvar GRUB_GFXPAYLOAD_LINUX keep
  fi
fi

rm -f /usr/local/bin/heiss-boot-branding.sh
log "done"
exit 0
