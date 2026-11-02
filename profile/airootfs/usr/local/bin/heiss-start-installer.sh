#!/bin/sh
# Heiss OS: starts the installer in the live session once the desktop is ready.
# Ready = plasmashell is running AND the dock script has finished (marker set, or it logged a
# failure, or the dock is disabled), but never wait longer than 30 s.
# Calamares output goes to ~/.cache/heiss-calamares-start.log.
[ -d /run/archiso/bootmnt ] || exit 0

LOG="$HOME/.cache/heiss-calamares-start.log"
mkdir -p "$HOME/.cache"
DOCKLOG="$HOME/.cache/heiss-dock.log"
MARK="$HOME/.config/heiss-dock-set"

i=0
while [ "$i" -lt 30 ]; do
  if pgrep -x plasmashell >/dev/null; then
    if [ "${HEISS_DOCK:-1}" = 0 ] || [ -f "$MARK" ] || grep -q 'FAILED' "$DOCKLOG" 2>/dev/null; then break; fi
  fi
  sleep 1; i=$((i+1))
done

{ printf '%s start after %s s of waiting\n' "$(date '+%F %T')" "$i"; } >> "$LOG"
exec sudo -E calamares >> "$LOG" 2>&1
