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

log "название системы в меню GRUB"
sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Heiss OS"/' /etc/default/grub || true

log "ключи pacman"
rm -rf /etc/pacman.d/gnupg
pacman-key --init && pacman-key --populate archlinux || log "ВНИМАНИЕ: не удалось инициализировать ключи pacman"

rm -f /usr/local/bin/heiss-cleanup.sh
log "готово"
exit 0
