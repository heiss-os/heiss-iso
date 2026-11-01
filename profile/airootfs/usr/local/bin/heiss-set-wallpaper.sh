#!/bin/sh
# Heiss OS: FALLBACK only. The default wallpaper is set from the first frame by the
# look-and-feel defaults ([Wallpaper] Image=Heiss-Everyday in org.heiss.*.desktop). This script
# applies the wallpaper only if the desktop did not end up with it (and then the stock one may
# flash for a moment). Disable with HEISS_WALLPAPER_FALLBACK=0.
[ "${HEISS_WALLPAPER_FALLBACK:-1}" = 0 ] && exit 0
MARK="$HOME/.config/heiss-wallpaper-set"
IMG="/usr/share/wallpapers/Heiss-Everyday/contents/images/3840x2160.png"
[ -f "$MARK" ] && exit 0
[ -f "$IMG" ] || exit 0
for i in $(seq 1 40); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 5
# defaults worked: nothing to do
if grep -qs 'Heiss-Everyday' "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc"; then
  mkdir -p "$HOME/.config"; touch "$MARK"; exit 0
fi
if plasma-apply-wallpaperimage "$IMG"; then
  mkdir -p "$HOME/.config"
  touch "$MARK"
fi
