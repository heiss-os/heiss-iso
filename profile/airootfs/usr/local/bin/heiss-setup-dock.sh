#!/bin/sh
# Heiss OS: при первом входе собирает панель-док (как на макете): внизу, плавающая,
# значок ß, закреплённые приложения, трей и часы справа.
MARK="$HOME/.config/heiss-dock-set"
[ -f "$MARK" ] && exit 0
for i in $(seq 1 60); do
  pgrep -x plasmashell >/dev/null && break
  sleep 1
done
sleep 6
JS=$(cat << 'JSEOF'
var old = panels();
var panel = new Panel();
panel.location = "bottom";
panel.height = 52;
panel.lengthMode = "fill";
panel.floating = true;
var k = panel.addWidget("org.kde.plasma.kickoff");
k.currentConfigGroup = ["General"];
k.writeConfig("icon", "heiss-launcher");
var t = panel.addWidget("org.kde.plasma.icontasks");
t.currentConfigGroup = ["General"];
t.writeConfig("launchers", "applications:org.kde.dolphin.desktop,applications:firefox.desktop,applications:org.kde.konsole.desktop,applications:systemsettings.desktop");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");
for (var i = 0; i < old.length; ++i) { old[i].remove(); }
JSEOF
)
if busctl --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$JS" >/dev/null 2>&1; then
  mkdir -p "$HOME/.config"
  touch "$MARK"
fi
