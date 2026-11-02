#!/bin/sh
# Heiss OS dock FALLBACK. The real panel comes from the look-and-feel layout script
# (org.heiss.*.desktop/contents/layouts/org.kde.plasma.desktop-layout.js), created by
# plasmashell from the first frame. This script only:
#   * does nothing when the panel is already ours (kickoff icon heiss-launcher-sand);
#     it never removes or rebuilds a panel that is ours
#   * builds our panel only if the layout script did not (e.g. an old home directory that
#     already has a stock panel), removing the other panels in that case
#   * reads the result back, logs it to ~/.cache/heiss-dock.log and sets the marker
#
# evaluateScript returns only what the script print()s, so every answer is ONE line with
# "|" between records; nothing depends on newlines (an earlier version parsed
# "count=1heiss" and never confirmed).
#
# Switches: HEISS_DOCK=0 in the environment disables the script; DOCK_PINS is the pin list.
[ "${HEISS_DOCK:-1}" = 0 ] && exit 0

MARK="$HOME/.config/heiss-dock-set"
LOG="$HOME/.cache/heiss-dock.log"
[ -f "$MARK" ] && exit 0
mkdir -p "$HOME/.cache" "$HOME/.config"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

# ---- single instance ----
LOCK="${XDG_RUNTIME_DIR:-/tmp}/heiss-dock.lock"
exec 9>"$LOCK"
if ! flock -n 9; then log "another instance is running, exit"; exit 0; fi

LIVE=false
[ -d /run/archiso/bootmnt ] && LIVE=true
DOCK_PINS="applications:org.kde.dolphin.desktop,applications:org.kde.konsole.desktop,applications:systemsettings.desktop,applications:firefox.desktop"
log "start: live=$LIVE"

# Returns the text print()ed by the script (the D-Bus reply is: s "text").
evaljs() {
  busctl --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$1" 2>>"$LOG" \
    | sed -e 's/^s "//' -e 's/"$//' -e 's/\\n/\n/g' -e 's/\\"/"/g'
}

ready=false
for i in $(seq 1 60); do
  if pgrep -x plasmashell >/dev/null && [ -n "$(evaljs 'print(panels().length)')" ]; then ready=true; break; fi
  sleep 1
done
$ready || { log "plasmashell/evaluateScript not ready after 60 s, giving up (no marker)"; exit 1; }

FIND='function widgetOf(p, type) {
  var ids = p.widgetIds;
  for (var i = 0; i < ids.length; ++i) { var w = p.widgetById(ids[i]); if (w.type == type) return w; }
  return null;
}
function cfg(w, group, key) { if (!w) return "-"; w.currentConfigGroup = [group]; return String(w.readConfig(key)); }
function isHeiss(p) { return cfg(widgetOf(p, "org.kde.plasma.kickoff"), "General", "icon") == "heiss-launcher-sand"; }'

# One line: count=N|heiss loc=.. icon=.. launchers=.. clock=[..]|other ...
CHECK="$FIND
var ps = panels(); var out = ['count=' + ps.length];
for (var i = 0; i < ps.length; ++i) {
  var p = ps[i]; var ck = widgetOf(p, 'org.kde.plasma.digitalclock');
  out.push((isHeiss(p) ? 'heiss' : 'other') + ' loc=' + p.location + ' icon=' + cfg(widgetOf(p, 'org.kde.plasma.kickoff'), 'General', 'icon')
    + ' launchers=' + cfg(widgetOf(p, 'org.kde.plasma.icontasks'), 'General', 'launchers')
    + ' clock=[' + cfg(ck, 'Appearance', 'showDate') + ',' + cfg(ck, 'Appearance', 'fontFamily') + ',' + cfg(ck, 'Appearance', 'fontSize') + ',' + cfg(ck, 'Appearance', 'fontWeight') + ']');
}
print(out.join('|'));"

BUILD="var PINS = \"$DOCK_PINS\".split(',');
$FIND
$(cat << 'JSEOF'
var old = panels().slice();
var panel = new Panel();
panel.location = "bottom";
panel.height = 52;
panel.lengthMode = "fill";
panel.floating = true;
panel.opacity = "translucent";
var k = panel.addWidget("org.kde.plasma.kickoff");
k.currentConfigGroup = ["General"];
k.writeConfig("icon", "heiss-launcher-sand");
k.reloadConfig();
var t = panel.addWidget("org.kde.plasma.icontasks");
t.currentConfigGroup = ["General"];
t.writeConfig("launchers", PINS);   // an array: a plain string would be ONE launcher entry
t.reloadConfig();
panel.addWidget("org.kde.plasma.systemtray");
var c = panel.addWidget("org.kde.plasma.digitalclock");
c.currentConfigGroup = ["Appearance"];
c.writeConfig("autoFontAndSize", false);
c.writeConfig("fontFamily", "Inter");
c.writeConfig("fontWeight", 400);
c.writeConfig("fontStyleName", "Regular");
c.writeConfig("fontSize", 11);
c.writeConfig("boldText", false);
c.writeConfig("showDate", false);
c.writeConfig("dateFormat", "shortDate");
c.reloadConfig();
for (var i = 0; i < old.length; ++i) { old[i].remove(); }
print("built");
JSEOF
)"

state=$(evaljs "$CHECK")
if ! printf '%s' "$state" | grep -q 'heiss loc='; then
  sleep 3; state=$(evaljs "$CHECK")      # give a late layout script one more chance
fi
log "initial: $state"
if printf '%s' "$state" | grep -q 'heiss loc='; then
  log "panel is already ours (layout script), nothing to build"
else
  log "no Heiss panel, building fallback: $(evaljs "$BUILD")"
fi

ok=false
for attempt in 1 2 3; do
  sleep 3
  state=$(evaljs "$CHECK"); log "check $attempt: $state"
  if printf '%s' "$state" | grep -q '^count=1|heiss .*icon=heiss-launcher-sand launchers=applications:org.kde.dolphin.desktop,applications:org.kde.konsole.desktop,applications:systemsettings.desktop,applications:firefox.desktop[^|]* clock=\[false,'; then
    ok=true; break
  fi
done

if $ok; then
  touch "$MARK"; log "done, marker set"
else
  log "FAILED: dock not confirmed, marker NOT set (will retry at next login)"
  exit 1
fi
