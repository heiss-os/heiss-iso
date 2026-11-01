#!/bin/sh
# Heiss OS: при первом входе собирает панель-док (как на макете): внизу, плавающая,
# значок ß (sand accent), закреплённые приложения, трей и часы справа.
MARK="$HOME/.config/heiss-dock-set"
[ -f "$MARK" ] && exit 0
for i in $(seq 1 60); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 6
LIVE=false
[ -d /run/archiso/bootmnt ] && LIVE=true
JS="var LIVE = $LIVE;
$(cat << 'JSEOF'
var old = panels();
var panel = new Panel();
panel.location = "bottom";
panel.height = 52;
panel.lengthMode = "fill";
panel.floating = true;
// translucent panel background (Plasma blurs/fades it; uses the neutral color scheme)
panel.opacity = "translucent";
var k = panel.addWidget("org.kde.plasma.kickoff");
k.currentConfigGroup = ["General"];
k.writeConfig("icon", "heiss-launcher-sand");
var t = panel.addWidget("org.kde.plasma.icontasks");
t.currentConfigGroup = ["General"];
// Plasma 6 on Arch desktop file ids. An id that does not exist shows up as a generic
// "file" icon in the task manager, so keep these in sync with the installed packages.
var launchers = "applications:org.mozilla.firefox.desktop,applications:org.kde.dolphin.desktop,applications:systemsettings.desktop";
if (LIVE) { launchers += ",applications:heiss-installer.desktop"; }  // installer shortcut: live session only
t.writeConfig("launchers", launchers);
panel.addWidget("org.kde.plasma.systemtray");
var c = panel.addWidget("org.kde.plasma.digitalclock");
// Lighter clock: Inter Regular 11 pt, no date line (set showDate to true for a small date)
c.currentConfigGroup = ["Appearance"];
c.writeConfig("autoFontAndSize", "false");
c.writeConfig("fontFamily", "Inter");
c.writeConfig("fontWeight", "400");
c.writeConfig("fontStyleName", "Regular");
c.writeConfig("fontSize", "11");
c.writeConfig("showDate", "false");
c.writeConfig("dateFormat", "shortDate");
for (var i = 0; i < old.length; ++i) { old[i].remove(); }
JSEOF
)"
if busctl --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$JS" >/dev/null 2>&1; then
  mkdir -p "$HOME/.config"
  touch "$MARK"
fi
