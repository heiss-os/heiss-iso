#!/bin/sh
# Heiss OS: keep the themed parts of the desktop in line with the active Heiss theme.
# The logic lives in heiss-core (`heiss theme sync`): it sets the launcher icon and Konsole's
# default profile, and CHECKS the parts that Plasma, kde-gtk-config and the portal switch
# themselves, with one log line per target (journal and ~/.local/state/heiss/theme-sync.log).
# Triggered by ~/.config/kdeglobals changes (systemd user path unit) and once at login (autostart).
# Disable: HEISS_THEME_SYNC=0 in the environment, or remove the .path unit / autostart entry.
# Report only, without changing anything: heiss theme status
[ "${HEISS_THEME_SYNC:-1}" = 0 ] && exit 0
if ! command -v heiss >/dev/null 2>&1; then
  echo "theme-sync: all: failed: the heiss command (package heiss-core) is not installed" >&2
  exit 1
fi
exec heiss theme sync "$@"
