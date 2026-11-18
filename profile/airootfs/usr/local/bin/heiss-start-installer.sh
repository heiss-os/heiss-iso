#!/bin/sh
# Heiss OS: starts the installer in the live session as soon as the compositor is up (started by heiss-session).
# Ready = a Wayland socket exists in $XDG_RUNTIME_DIR (max wait 15 s). Calamares runs as root and connects to that
# socket (sudo -E keeps the environment). Output and the waited time go to ~/.cache/heiss-calamares-start.log.
[ -d /run/archiso/bootmnt ] || exit 0

LOG="$HOME/.cache/heiss-calamares-start.log"
mkdir -p "$HOME/.cache"

i=0
sock=""
while [ "$i" -lt 15 ]; do
  for s in "$XDG_RUNTIME_DIR"/wayland-*; do
    case "$s" in *.lock) continue ;; esac
    [ -S "$s" ] && sock="$(basename "$s")" && break
  done
  [ -n "$sock" ] && break
  sleep 1; i=$((i+1))
done
sleep 1

{ printf '%s start after %s s of waiting (socket: %s)\n' "$(date '+%F %T')" "$i" "${sock:-none}"; } >> "$LOG"
[ -n "$sock" ] || exit 1
export WAYLAND_DISPLAY="$sock" QT_QPA_PLATFORM=wayland
exec sudo -E calamares >> "$LOG" 2>&1
