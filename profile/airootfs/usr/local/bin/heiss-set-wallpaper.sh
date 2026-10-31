#!/bin/sh
# Heiss OS: один раз при первом входе ставит фирменные обои
MARK="$HOME/.config/heiss-wallpaper-set"
IMG="/usr/share/wallpapers/Heiss-Everyday/contents/images/3840x2160.png"
[ -f "$MARK" ] && exit 0
[ -f "$IMG" ] || exit 0
for i in $(seq 1 40); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 3
if plasma-apply-wallpaperimage "$IMG"; then
  kwriteconfig6 --file kscreenlockerrc --group Greeter --group Wallpaper --group org.kde.image --group General --key Image "file://$IMG" || true
  mkdir -p "$HOME/.config"
  touch "$MARK"
fi
