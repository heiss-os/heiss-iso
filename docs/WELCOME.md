# Heiss Welcome: the key-binding window

Status 2026-11-18 (H2a): rewritten for the Hyprland session. The old eleven-step wizard (profile, privacy, backups, applying through the helper) is gone; its history is in `DECISIONS.md` and `git log`. The questions it asked move to the terminal installer (H3), the rest to the settings window (H2b). Plan: `docs/DIRECTION-HYPRLAND.md`.

## What it does

One window: the key bindings of the desktop, with a search box. The list is not typed in anywhere: `heiss_core.hyprcfg` reads `~/.config/hypr/hyprland.lua` (and `heiss-user.lua`, loaded last by it), so it is always the active configuration. If the owner replaces the file with a hand-written one, the list follows it.

- Start: `heiss-welcome --first-run` from `hyprland.start` in the shipped config (once per user, marker `~/.config/heiss/welcome-done`, never in the live session); `heiss-welcome --force` always (key `Alt + F1`, menu entry "Heiss Key Bindings"); plain `heiss-welcome` shows it too.
- Language: `LC_ALL`, `LC_MESSAGES` or `LANG` starting with `ru` gives Russian, anything else English. Key names are localised; the descriptions are the comments in the config as written.
- Colours: the Heiss tokens; Dark or Light follows the desktop colour scheme (`Qt.styleHints.colorScheme`).

## What it reads (format of the configuration)

```lua
local mainMod = "ALT"                      -- read, with ~/.config/heiss/modifier on top (see below)
-- Open the terminal                       -- the description of the next bind
hl.bind(mainMod .. " + Return", hl.dsp.exec_cmd(terminal))
for i = 1, 5 do                            -- expanded once per value of i
    hl.bind(mainMod .. " + " .. i, hl.dsp.focus({ workspace = i }), { description = "Go to workspace " .. i })
end
```

Description order: the `description` option, else the comment lines directly above (joined), else a comment after the call on the same line, else "(no description in the configuration)". A key written in a way the reader cannot evaluate (a function call, say) is listed as written with a note. A bind inside `function ... end` is skipped. Nothing is executed. Tests: `core/tests/test_hyprcfg.py`, including a run of the real `hyprland.lua` under Lua with a stub `hl` table to compare.

## Main modifier

`~/.config/heiss/modifier` holds `ALT` (default, because the owner's host uses Super) or `SUPER`. The shipped `hyprland.lua` reads it at the top; any other content is ignored. `hyprcfg.write_modifier` writes it atomically and refuses anything else. A configuration that does not mention `heiss/modifier` is "own": the window says the settings do not change its main key. The switch is on the Keyboard page of the settings window (`docs/CONTROL-CENTER.md`).

## Not verified

Real session start, the first-run marker, `Alt + F1`, `hyprctl reload` after a change, startup time of PySide6 in the VM. See the H2a block of the FINAL VM TEST LIST in `docs/PLAN-STATE.md`.
