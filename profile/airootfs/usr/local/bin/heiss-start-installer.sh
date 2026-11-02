#!/bin/sh
# Heiss OS: starts the installer in the live session as soon as the desktop is up.
# Ready = plasmashell is running (max wait 8 s). It does NOT wait for the dock script.
# Calamares output and the waited time go to ~/.cache/heiss-calamares-start.log.
[ -d /run/archiso/bootmnt ] || exit 0

LOG="$HOME/.cache/heiss-calamares-start.log"
mkdir -p "$HOME/.cache"

i=0
while [ "$i" -lt 8 ]; do
  pgrep -x plasmashell >/dev/null && break
  sleep 1; i=$((i+1))
done

{ printf '%s start after %s s of waiting\n' "$(date '+%F %T')" "$i"; } >> "$LOG"
exec sudo -E calamares >> "$LOG" 2>&1
