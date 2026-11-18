# Heiss Settings (`heiss-control`)

Status 2026-11-18 (H2b): rewritten for the Hyprland session as one light settings window. The old Control Center (overview, profiles with saved actions, security center, updates and snapshots, network and privacy levels, backups, KDE System Settings link) is gone together with the privacy levels, backups and snapshots that were removed from the product (`DECISIONS.md`, direction change). Plan: `docs/DIRECTION-HYPRLAND.md`. Code that only the old window used (privacy levels, KDE settings, snapper) is removed from `heiss-core` and the helper in H2c.

## Pages

| Page | What it does | How |
|---|---|---|
| Appearance | Heiss Dark or Heiss Light | `heiss theme set dark\|light` on a worker thread |
| Display | lists the screens; scale 100, 125, 150 or 200 % for every screen | `hyprctl monitors -j` (read); the scale is written to a block of `~/.config/hypr/heiss-user.lua` and Hyprland is reloaded (`hyprctl reload`) |
| Keyboard | **main key Alt or Super**; keyboard layouts | the main key is `~/.config/heiss/modifier` (read by the shipped `hyprland.lua` and by the welcome window, `heiss_core.hyprcfg`); layouts are a block of `heiss-user.lua` (`kb_layout`, and `kb_options = "grp:ctrl_shift_toggle"` when there are several), checked against `/usr/share/X11/xkb/rules/base.lst`; then `hyprctl reload` |
| Network and Bluetooth | network state; opens `nm-connection-editor` and `blueman-manager` | `nmcli -t -f STATE,CONNECTIVITY general`; programs from a fixed table |
| Audio | opens `pavucontrol` | same table |
| Packages | read-only: chosen profile, add-ons, applied profile, how many packages and services Heiss installed | `/etc/heiss/profile.toml`, `/var/lib/heiss/state.json`; changing the profile is `heiss profile` in a terminal for now |
| Hardware | facts about the computer, driver proposals with their state, a report without personal data to copy | `heiss_core.hardware` (read-only) |
| System | system, build, kernel, links from os-release (https only), `heiss check` | read-only |

## Rules

- No privileges, no helper, no polkit: everything runs as the user. No shell: only fixed argument lists (`system_tools.py`), a program is chosen from a table, never from text. The only free text is the layout line, which must match `[a-z]{2,3}(,[a-z]{2,3}){0,3}` and be known to xkeyboard-config; the Lua written is built from the validated pieces.
- `heiss-user.lua` keeps what the window writes between two marker lines (`-- heiss:keyboard begin ...` / `end`, same for `display`); everything outside them is the user's and is never touched (`hyprcfg.set_block`, tested, including a run under Lua).
- A hand-written `hyprland.lua` that does not read the modifier file keeps its own main key: the window shows the choice disabled and says why.
- A page is a list of blocks (text, rows, choice, field, action, items, report, links, message) and `qml/Main.qml` draws any page from them; all logic is in `model.py` and tested without Qt (`control/tests/test_model.py`). Slow work runs on a worker thread; one job at a time.
- Colours: the Heiss tokens; Dark or Light follows the desktop colour scheme. Language: `LC_ALL`, `LC_MESSAGES` or `LANG` starting with `ru` gives Russian.
- Start: `Alt + I` (`heiss-control`), or the menu entry "Heiss Settings".
- Look at it without a VM: `python3 scripts/render-gui.py --only control` (offscreen, fixture data).

## Not verified

The window in a real session, `hyprctl reload` applying the main key, the layouts and the scale, whether a second `hl.monitor` call in `heiss-user.lua` overrides the default one, the layout switch with Ctrl + Shift, the program launchers (`nm-connection-editor`, `blueman-manager`, `pavucontrol`). See the H2b block of the FINAL VM TEST LIST in `docs/PLAN-STATE.md`.
