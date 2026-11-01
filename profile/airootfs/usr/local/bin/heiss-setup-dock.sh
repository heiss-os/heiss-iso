#!/bin/sh
# Heiss OS: builds the dock panel at first login (bottom, floating, Heiss launcher, pinned
# apps, tray and clock on the right).
#
# Robustness (see PR "dock and default wallpaper"):
#   * lock: only one instance runs at a time (flock), a second run exits at once
#   * waits until plasmashell owns its D-Bus name AND answers evaluateScript, and until the
#     panel set of the default layout is stable (Plasma creates its own default panel at
#     first start; building ours in the middle of that is a race)
#   * creates the panel once; an existing Heiss panel (kickoff icon heiss-launcher-sand) means done
#   * reads the final state back and logs it to ~/.cache/heiss-dock.log
#   * the marker is written only after the read-back confirmed the pinned launchers
#
# Switches: HEISS_DOCK=0 in the environment disables the script; DOCK_PINS below is the pin list.
# Desktop file ids are the real ones from the Arch packages (checked in the built image):
#   firefox.desktop, org.kde.dolphin.desktop, org.kde.konsole.desktop, systemsettings.desktop
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
DOCK_PINS="applications:firefox.desktop,applications:org.kde.dolphin.desktop,applications:org.kde.konsole.desktop,applications:systemsettings.desktop"
$LIVE && DOCK_PINS="$DOCK_PINS,applications:heiss-installer.desktop"   # installer shortcut: live session only
log "start: live=$LIVE pins=$DOCK_PINS"

evaljs() { busctl --user --json=short call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$1" 2>>"$LOG"; }

# ---- wait for plasmashell and the scripting interface ----
ready=false
for i in $(seq 1 90); do
  if pgrep -x plasmashell >/dev/null && evaljs "panels().length" >/dev/null; then ready=true; break; fi
  sleep 1
done
$ready || { log "plasmashell/evaluateScript not ready after 90 s, giving up (no marker)"; exit 1; }

# ---- wait until the default layout is done: at least one panel, count unchanged for 4 s ----
last=-1; stable=0
for i in $(seq 1 40); do
  n=$(evaljs "panels().length" | grep -o '[0-9][0-9]*' | head -n 1)
  n=${n:-0}
  if [ "$n" -ge 1 ] && [ "$n" = "$last" ]; then stable=$((stable+1)); else stable=0; fi
  last=$n
  [ "$stable" -ge 4 ] && break
  sleep 1
done
log "panels before: $last (stable=$stable)"

# ---- shared JS: a panel is ours when its kickoff widget has our icon ----
FIND='function isHeiss(p) {
  var ids = p.widgetIds;
  for (var i = 0; i < ids.length; ++i) {
    var w = p.widgetById(ids[i]);
    if (w.type == "org.kde.plasma.kickoff") {
      w.currentConfigGroup = ["General"];
      if (w.readConfig("icon") == "heiss-launcher-sand") return true;
    }
  }
  return false;
}
function pins(p) {
  var ids = p.widgetIds;
  for (var i = 0; i < ids.length; ++i) {
    var w = p.widgetById(ids[i]);
    if (w.type == "org.kde.plasma.icontasks") { w.currentConfigGroup = ["General"]; return String(w.readConfig("launchers")); }
  }
  return "";
}'

BUILD="var PINS = \"$DOCK_PINS\";
$FIND
$(cat << 'JSEOF'
var existing = panels();
for (var e = 0; e < existing.length; ++e) { if (isHeiss(existing[e])) { "exists"; throw "exists"; } }
var old = existing.slice();
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
t.writeConfig("launchers", PINS);
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
// remove only the panels that existed BEFORE ours (the default layout's panel)
for (var i = 0; i < old.length; ++i) { old[i].remove(); }
"built"
JSEOF
)"

CHECK="$FIND
var out = [];
var ps = panels();
for (var i = 0; i < ps.length; ++i) { out.push((isHeiss(ps[i]) ? 'heiss' : 'other') + ':' + pins(ps[i])); }
out.join('|')"

# Remove every panel that is not ours (a late default panel), keep ours.
PRUNE="$FIND
var ps = panels();
for (var i = 0; i < ps.length; ++i) { if (!isHeiss(ps[i])) ps[i].remove(); }
panels().length"

res=$(evaljs "$BUILD"); log "build: $res"

ok=false
for attempt in 1 2 3; do
  sleep 4
  state=$(evaljs "$CHECK"); log "check $attempt: $state"
  # exactly one panel, ours, with Firefox and Konsole pinned
  case "$state" in
    *other*) log "extra panel found, pruning"; log "prune: $(evaljs "$PRUNE")"; continue ;;
  esac
  case "$state" in
    *heiss:*firefox.desktop*org.kde.konsole.desktop*) ok=true; break ;;
  esac
done

if $ok; then
  touch "$MARK"; log "done, marker set"
else
  log "FAILED: dock not confirmed, marker NOT set (will retry at next login)"
  exit 1
fi
