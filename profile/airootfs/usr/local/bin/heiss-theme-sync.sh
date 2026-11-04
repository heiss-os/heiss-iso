#!/bin/sh
# Heiss OS: keep the pieces of the desktop that a Global Theme switch does NOT re-apply in
# line with the active Heiss theme. Plasma applies the LnF `defaults` (color scheme, accent,
# icons, plasmarc, kwin, wallpaper id) on a switch, but it never re-runs the layout script, so
# the launcher icon stays as it was. This script sets the launcher icon variant:
#   HeissDark  -> heiss-launcher-sand        (#C9B28A)
#   HeissLight -> heiss-launcher-sand-light  (#8C7448)
# Triggered by ~/.config/kdeglobals changes (systemd user path unit) and once at login
# (autostart). Idempotent; never touches kdeglobals itself (no feedback loop). A custom color
# scheme (anything but HeissDark/HeissLight) is left alone.
# Disable: HEISS_THEME_SYNC=0 in the environment, or remove the .path unit / autostart entry.
[ "${HEISS_THEME_SYNC:-1}" = 0 ] && exit 0

exec 9>"${XDG_RUNTIME_DIR:-/tmp}/heiss-theme-sync.lock"
flock -n 9 || exit 0

for i in $(seq 1 60); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 2   # a theme switch writes kdeglobals several times; read the final state

READ=$(command -v kreadconfig6 || command -v kreadconfig5) || exit 0
SCHEME=$("$READ" --file kdeglobals --group General --key ColorScheme)
case "$SCHEME" in
  HeissDark)  ICON=heiss-launcher-sand ;;
  HeissLight) ICON=heiss-launcher-sand-light ;;
  *) exit 0 ;;
esac

busctl --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "
var icon = '$ICON';
for (var p of panels()) {
  for (var w of p.widgets()) {
    if (w.type != 'org.kde.plasma.kickoff') continue;
    w.currentConfigGroup = ['General'];
    var cur = String(w.readConfig('icon'));
    if (cur.indexOf('heiss-launcher-sand') == 0 && cur != icon) w.writeConfig('icon', icon);
  }
}" >/dev/null 2>&1
exit 0
