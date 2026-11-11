#!/usr/bin/env bash
# Heiss OS: убирает из установленной системы всё, что нужно только live-образу.
# Запускается установщиком Calamares внутри установленной системы (chroot).
set -u
log() { echo "[heiss-cleanup] $*"; }

log "live-пользователь и автовход"
userdel -rf liveuser 2>/dev/null || true
groupdel liveuser 2>/dev/null || true
rm -rf /home/liveuser
rm -f /etc/sddm.conf.d/autologin.conf
rm -f /etc/sudoers.d/g_wheel
rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf
rmdir /etc/systemd/system/getty@tty1.service.d 2>/dev/null || true
rm -f /root/.automated_script.sh /root/.zlogin /etc/motd

log "блокировка root и отключение live-доступа по SSH"
passwd -l root || true
rm -f /etc/ssh/sshd_config.d/10-archiso.conf
systemctl disable sshd.service 2>/dev/null || true

log "live-службы"
rm -f /etc/systemd/system/pacman-init.service
rm -f /etc/systemd/system/etc-pacman.d-gnupg.mount
rm -f /etc/systemd/system/choose-mirror.service
find /etc/systemd/system -xtype l -delete 2>/dev/null || true

log "установщик"
rm -f /usr/share/applications/heiss-installer.desktop
rm -f /etc/xdg/autostart/heiss-installer-autostart.desktop
rm -rf /etc/calamares /usr/share/calamares/branding/heiss
pacman -Rns --noconfirm calamares 2>/dev/null || true

log "live-only packages (releng leftovers)"
# Removed one by one: a package that other software needs just fails and is kept.
LIVE_PKGS=(mkinitcpio-archiso mkinitcpio-nfs-utils cloud-init livecd-sounds archinstall
           clonezilla darkhttpd nbd nfs-utils syslinux memtest86+ memtest86+-efi edk2-shell
           espeakup brltty gpm)
# Guest tools: keep only the ones that match the hypervisor we are installed on.
virt=$(systemd-detect-virt --vm 2>/dev/null || true)
log "virtualization: ${virt:-none}"
keep=""
case "$virt" in
  oracle)    keep=virtualbox-guest-utils-nox ;;
  vmware)    keep=open-vm-tools ;;
  kvm|qemu)  keep=qemu-guest-agent ;;
  microsoft) keep=hyperv ;;
esac
for g in virtualbox-guest-utils-nox open-vm-tools qemu-guest-agent hyperv; do
  [ "$g" = "$keep" ] || LIVE_PKGS+=("$g")
done
for pkg in "${LIVE_PKGS[@]}"; do
  if pacman -Q "$pkg" >/dev/null 2>&1; then
    pacman -Rns --noconfirm "$pkg" >/dev/null 2>&1 && log "removed $pkg" || log "kept $pkg (required by another package)"
  fi
done

log "live-only files and units"
rm -rf /etc/cloud /var/lib/cloud /etc/systemd/system/cloud-init.target.wants
rm -f /etc/systemd/system/livecd-*.service
rm -f /etc/systemd/resolved.conf.d/archiso.conf
rmdir /etc/systemd/resolved.conf.d 2>/dev/null || true
rm -rf /etc/systemd/system/systemd-networkd-wait-online.service.d
rm -f /usr/local/bin/choose-mirror /usr/local/bin/livecd-sound /usr/local/bin/heiss-open-link
rm -f /etc/xdg/autostart/heiss-open-link.desktop /usr/share/applications/calamares.desktop
find /etc/systemd/system -xtype l -delete 2>/dev/null || true   # units of removed packages

log "hostname"
if [ "$(cat /etc/hostname 2>/dev/null)" = "heiss-live" ]; then
  echo heiss > /etc/hostname   # fallback; the users step overrides it with the chosen name
  grep -q '127.0.1.1' /etc/hosts 2>/dev/null || echo "127.0.1.1 heiss" >> /etc/hosts
fi

log "pacman repositories and mirrors"
# the installed system must use real mirrors: no file:// local repo, at least one active Server
sed -i '/^\[heiss-local\]/,/^$/d' /etc/pacman.conf
if ! grep -q '^Server' /etc/pacman.d/mirrorlist 2>/dev/null; then
  echo 'Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch' >> /etc/pacman.d/mirrorlist
fi
if grep -qE '^Server *= *file://' /etc/pacman.conf; then log "WARNING: file:// still present in pacman.conf"; fi

log "ядро и initramfs"
rm -f /etc/mkinitcpio.conf.d/archiso.conf
install -Dm644 "$(ls /usr/lib/modules/*/vmlinuz | head -1)" /boot/vmlinuz-linux
cat > /etc/mkinitcpio.d/linux.preset << 'PRESET_EOF'
# mkinitcpio preset file for the 'linux' package
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"

PRESETS=('default' 'fallback')

default_image="/boot/initramfs-linux.img"

fallback_image="/boot/initramfs-linux-fallback.img"
fallback_options="-S autodetect"
PRESET_EOF
mkinitcpio -P || log "ВНИМАНИЕ: mkinitcpio завершился с ошибкой"

log "stock KDE wallpapers"
# squashfs may carry them if the build hook did not run; the libalpm hook keeps them away after updates
find /usr/share/wallpapers -mindepth 1 -maxdepth 1 ! -name 'Heiss-*' -exec rm -rf {} + 2>/dev/null || true

log "название системы в меню GRUB"
sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Heiss OS"/' /etc/default/grub || true

log "ключи pacman"
rm -rf /etc/pacman.d/gnupg
pacman-key --init && pacman-key --populate archlinux || log "ВНИМАНИЕ: не удалось инициализировать ключи pacman"
log "репозиторий Heiss и его ключ"
# Appended last (official repositories keep their priority). Only added when the Heiss key was
# really imported, otherwise `pacman -Sy` would fail on the installed system.
# Set HEISS_NO_REPO=1 to skip. Not tested on a real installation yet.
if [ "${HEISS_NO_REPO:-0}" = 1 ]; then
  log "пропущено (HEISS_NO_REPO=1)"
elif [ ! -f /usr/share/pacman/keyrings/heiss.gpg ]; then
  log "ВНИМАНИЕ: пакет heiss-keyring не установлен, репозиторий [heiss] не добавлен"
elif pacman-key --populate heiss; then
  if ! grep -q '^\[heiss\]' /etc/pacman.conf; then
    printf '\n[heiss]\nSigLevel = Required DatabaseRequired\nServer = https://heiss-os.github.io/heiss-repo/$arch\n' >> /etc/pacman.conf
  fi
else
  log "ВНИМАНИЕ: не удалось импортировать ключ Heiss, репозиторий [heiss] не добавлен"
fi
# do not leave gpg-agent running from the chroot (it would block unmounting the target)
gpgconf --homedir /etc/pacman.d/gnupg --kill all 2>/dev/null || true

rm -f /usr/local/bin/heiss-cleanup.sh
log "готово"
exit 0
