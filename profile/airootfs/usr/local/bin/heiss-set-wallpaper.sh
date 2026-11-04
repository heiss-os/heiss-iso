#!/bin/sh
# Heiss OS: FALLBACK only. The default wallpaper is set from the first frame by the
# look-and-feel defaults and layout script (package id Heiss-Everyday for Heiss Dark,
# Heiss-Everyday-Light for Heiss Light; two plain packages, no dynamic light/dark mechanism). This script applies it
# only if the desktop did not end up with it. It sets the package ID through the shell
# scripting API (plasma-apply-wallpaperimage takes a file path and would create a second
# "3840x2160" entry in the Wallpaper dialog). Disable with HEISS_WALLPAPER_FALLBACK=0.
[ "${HEISS_WALLPAPER_FALLBACK:-1}" = 0 ] && exit 0
MARK="$HOME/.config/heiss-wallpaper-set"
[ -f "$MARK" ] && exit 0
READ=$(command -v kreadconfig6 || command -v kreadconfig5)
ID=Heiss-Everyday; COLOR='#1E1F21'
if [ -n "$READ" ] && [ "$("$READ" --file kdeglobals --group General --key ColorScheme)" = HeissLight ]; then
  ID=Heiss-Everyday-Light; COLOR='#F7F5F1'
fi
[ -d "/usr/share/wallpapers/$ID" ] || exit 0
for i in $(seq 1 40); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 5
# defaults worked: nothing to do
if grep -qs "Image=$ID\$" "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc"; then
  mkdir -p "$HOME/.config"; touch "$MARK"; exit 0
fi
QDBUS=$(command -v qdbus6 || command -v qdbus)
[ -n "$QDBUS" ] || exit 0
if "$QDBUS" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
for (var d of desktops()) {
  d.wallpaperPlugin = "org.kde.image";
  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
  d.writeConfig("Image", "'"$ID"'");
  d.writeConfig("Color", "'"$COLOR"'");
}' >/dev/null; then
  mkdir -p "$HOME/.config"
  touch "$MARK"
fi
