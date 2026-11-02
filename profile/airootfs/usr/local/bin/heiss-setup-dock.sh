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
#   * the marker is written only after the read-back confirmed ONE panel (ours), the pinned
#     launchers, the launcher icon and the clock settings
#
# Plasma scripting: evaluateScript returns only what the script print()s (like the interactive
# console), NOT the value of the last expression. Earlier versions returned an empty string for
# every call, so "panels before: 0" was just an unparsable empty answer, never a real count.
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

# Returns the text print()ed by the script (the D-Bus reply is: s "text").
evaljs() {
  busctl --user call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$1" 2>>"$LOG" \
    | sed -e 's/^s "//' -e 's/"$//' -e 's/\\n/\n/g' -e 's/\\"/"/g'
}

# ---- wait for plasmashell and the scripting interface (a real answer, not just exit status) ----
ready=false
for i in $(seq 1 90); do
  if pgrep -x plasmashell >/dev/null && [ -n "$(evaljs 'print(panels().length)')" ]; then ready=true; break; fi
  sleep 1
done
$ready || { log "plasmashell/evaluateScript not ready after 90 s, giving up (no marker)"; exit 1; }

# ---- wait until the default layout is done: at least one panel, count unchanged for 4 s ----
last=-1; stable=0
for i in $(seq 1 40); do
  n=$(evaljs 'print(panels().length)' | grep -o '[0-9][0-9]*' | head -n 1)
  n=${n:-0}
  if [ "$n" -ge 1 ] && [ "$n" = "$last" ]; then stable=$((stable+1)); else stable=0; fi
  last=$n
  [ "$stable" -ge 4 ] && break
  sleep 1
done
log "panels before: $last (stable=$stable)"

# ---- shared JS: a panel is ours when its kickoff widget has our icon ----
FIND='function widgetOf(p, type) {
  var ids = p.widgetIds;
  for (var i = 0; i < ids.length; ++i) { var w = p.widgetById(ids[i]); if (w.type == type) return w; }
  return null;
}
function cfg(w, group, key) { if (!w) return "-"; w.currentConfigGroup = [group]; return String(w.readConfig(key)); }
function isHeiss(p) { return cfg(widgetOf(p, "org.kde.plasma.kickoff"), "General", "icon") == "heiss-launcher-sand"; }'

BUILD="var PINS = \"$DOCK_PINS\";
$FIND
$(cat << 'JSEOF'
var existing = panels();
for (var e = 0; e < existing.length; ++e) { if (isHeiss(existing[e])) { print("exists"); throw "exists"; } }
var old = existing.slice();
var panel = new Panel();
panel.location = "bottom";
panel.height = 52;
panel.lengthMode = "fill";
panel.floating = true;
// translucent panel background (Plasma blurs/fades it; uses the neutral color scheme)
panel.opacity = "translucent";
// Key names verified in the plasma-workspace/plasma-desktop plugins of the image:
//   kickoff:      [General] icon
//   icontasks:    [General] launchers
//   digitalclock: [Appearance] autoFontAndSize fontFamily fontSize fontWeight fontStyleName showDate
var k = panel.addWidget("org.kde.plasma.kickoff");
k.currentConfigGroup = ["General"];
k.writeConfig("icon", "heiss-launcher-sand");
k.reloadConfig();
var t = panel.addWidget("org.kde.plasma.icontasks");
t.currentConfigGroup = ["General"];
t.writeConfig("launchers", PINS);
t.reloadConfig();
panel.addWidget("org.kde.plasma.systemtray");
var c = panel.addWidget("org.kde.plasma.digitalclock");
// Time only, small and light: Inter Regular 11 pt, no date line
c.currentConfigGroup = ["Appearance"];
c.writeConfig("autoFontAndSize", false);
c.writeConfig("fontFamily", "Inter");
c.writeConfig("fontWeight", 400);
c.writeConfig("fontStyleName", "Regular");
c.writeConfig("fontSize", 11);
c.writeConfig("boldText", false);
c.writeConfig("showDate", false);
c.reloadConfig();
// remove only the panels that existed BEFORE ours (the default layout's panel)
for (var i = 0; i < old.length; ++i) { old[i].remove(); }
print("built");
JSEOF
)"

# Read-back, one line per panel: kind, kickoff icon, launchers, clock keys.
CHECK="$FIND
var ps = panels();
print('count=' + ps.length);
for (var i = 0; i < ps.length; ++i) {
  var p = ps[i];
  var ck = widgetOf(p, 'org.kde.plasma.digitalclock');
  print((isHeiss(p) ? 'heiss' : 'other') + ' loc=' + p.location + ' icon=' + cfg(widgetOf(p, 'org.kde.plasma.kickoff'), 'General', 'icon')
    + ' launchers=' + cfg(widgetOf(p, 'org.kde.plasma.icontasks'), 'General', 'launchers')
    + ' clock=[' + cfg(ck, 'Appearance', 'showDate') + ',' + cfg(ck, 'Appearance', 'fontFamily') + ',' + cfg(ck, 'Appearance', 'fontSize') + ',' + cfg(ck, 'Appearance', 'fontWeight') + ']');
}"

# Remove every panel that is not ours (a late default panel), keep ours.
PRUNE="$FIND
var ps = panels();
for (var i = ps.length - 1; i >= 0; --i) { if (!isHeiss(ps[i])) ps[i].remove(); }
print('panels after prune: ' + panels().length);"

res=$(evaljs "$BUILD"); log "build: $res"

# Plasma may create its default panel after we ran (slow start, late layout script). Keep
# reconciling for up to ~40 s: success needs two consecutive clean reads in a row.
ok=false; clean=0
for attempt in $(seq 1 10); do
  sleep 4
  state=$(evaljs "$CHECK"); log "check $attempt: $(printf '%s' "$state" | tr '\n' ' ')"
  if printf '%s' "$state" | grep -q '^other'; then
    log "extra panel found, pruning: $(evaljs "$PRUNE" | tr '\n' ' ')"; clean=0; continue
  fi
  if printf '%s' "$state" | grep -q '^count=1' \
     && printf '%s' "$state" | grep -q '^heiss .*icon=heiss-launcher-sand .*firefox.desktop.*org.kde.konsole.desktop.*clock=\[false,'; then
    clean=$((clean+1)); [ "$clean" -ge 2 ] && { ok=true; break; }
  else
    clean=0
  fi
done

if $ok; then
  touch "$MARK"; log "done, marker set"
else
  log "FAILED: dock not confirmed, marker NOT set (will retry at next login)"
  exit 1
fi
