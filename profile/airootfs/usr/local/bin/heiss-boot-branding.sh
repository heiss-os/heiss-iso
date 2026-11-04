#!/usr/bin/env bash
# Heiss OS: boot chain branding for the INSTALLED system (Plymouth splash + GRUB theme).
# Runs inside the target chroot from Calamares (shellprocess@boot), after unpackfs and BEFORE
# shellprocess@cleanup (which runs mkinitcpio -P) and BEFORE the bootloader module
# (which runs grub-install + grub-mkconfig). Disable: set HEISS_BOOT_BRANDING=0 or remove
# "shellprocess@boot" from the exec sequence in settings.conf. Not used on the live ISO.
set -u
# ---- switches (environment overrides) ----------------------------------------------------
HEISS_GRUB_THEME="${HEISS_GRUB_THEME:-1}"            # 0: leave GRUB on its default text menu
HEISS_GRUB_GFXMODE="${HEISS_GRUB_GFXMODE:-1920x1080,1280x800,1024x768,auto}"
HEISS_GRUB_SELECT_BAR="${HEISS_GRUB_SELECT_BAR:-1}"  # 0: no selection bar, only text color
HEISS_GRUB_OVERRIDE_NAME="${HEISS_GRUB_OVERRIDE_NAME:-0}"  # see the note near the end
LOGFILE=/var/log/heiss-boot-branding.log
log() { echo "[heiss-boot-branding] $*"; echo "[heiss-boot-branding] $*" >> "$LOGFILE" 2>/dev/null; }
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
  if [ "$HEISS_GRUB_THEME" != 0 ] && [ -d /usr/share/heiss/grub-theme ]; then
    install -d /boot/grub/themes/heiss
    cp -a /usr/share/heiss/grub-theme/. /boot/grub/themes/heiss/
    T=/boot/grub/themes/heiss/theme.txt
    if [ "$HEISS_GRUB_SELECT_BAR" = 0 ]; then
      sed -i '/selected_item_pixmap_style/d' "$T"
      rm -f /boot/grub/themes/heiss/select_*.png
    fi
    setvar GRUB_THEME "\"$T\""
    # grub-mkconfig only loads the theme when gfxterm is in GRUB_TERMINAL_OUTPUT. Leave
    # GRUB_TERMINAL_INPUT / GRUB_TERMINAL unset: GRUB keeps its native input terminal.
    setvar GRUB_TERMINAL_OUTPUT gfxterm
    sed -i -E '/^#?GRUB_TERMINAL=/d' "$G"
    setvar GRUB_GFXMODE "\"$HEISS_GRUB_GFXMODE\""
    setvar GRUB_GFXPAYLOAD_LINUX keep
  fi
  # Menu entries read "Heiss OS Linux" because 10_linux builds the name as
  # "${GRUB_DISTRIBUTOR} Linux". Showing just "Heiss OS" would need a sed on
  # /etc/grub.d/10_linux (overwritten by every grub package update), so it is OFF by default.
  if [ "$HEISS_GRUB_OVERRIDE_NAME" = 1 ] && [ -f /etc/grub.d/10_linux ]; then
    sed -i 's/OS="${GRUB_DISTRIBUTOR} Linux"/OS="${GRUB_DISTRIBUTOR}"/' /etc/grub.d/10_linux
  fi
  log "wrote /etc/default/grub:"
  grep -E '^(GRUB_(DISTRIBUTOR|TIMEOUT|TIMEOUT_STYLE|THEME|TERMINAL|TERMINAL_INPUT|TERMINAL_OUTPUT|GFXMODE|GFXPAYLOAD_LINUX|CMDLINE_LINUX_DEFAULT))=' "$G" | while read -r l; do log "  $l"; done
  [ -d /boot/grub/themes/heiss ] && { log "theme dir:"; ls /boot/grub/themes/heiss | while read -r l; do log "  $l"; done; }
fi

rm -f /usr/local/bin/heiss-boot-branding.sh
log "done"
exit 0
