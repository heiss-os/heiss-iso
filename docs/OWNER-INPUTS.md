# What the owner still has to supply

The Hyprland session ships clean placeholders (`desktop/`). Everything below replaces a placeholder without a code change.

| What | Where it goes | Notes |
|---|---|---|
| Hyprland configuration | `desktop/hypr/hyprland.lua` (Hyprland 0.57 reads **Lua**, not the old hyprlang `.conf`; installed to `/usr/share/heiss/desktop/hypr/`, copied to `~/.config/hypr/hyprland.lua` at the first login, never overwritten) | Check your file with `Hyprland --verify-config -c hyprland.lua` (exit 0 and `config ok`). Keep the last block (it loads `~/.config/hypr/heiss-user.lua` with `dofile`, where Heiss settings write) and the colours block at the top (it reads `~/.config/heiss/theme/hypr-colors.conf`, so Heiss Dark and Light switch; use `colors.accent`, `colors.border`, ...). Put a comment line `-- description` directly above every `hl.bind` (or a `description` option): the welcome window (H2) lists them. The session starts Hyprland through `start-hyprland -- -c ~/.config/hypr/hyprland.lua`. |
| Key bindings (temporary) | the `mainMod` line and the `hl.bind` lines in `desktop/hypr/hyprland.lua` | **Temporary defaults, replace with yours.** The main modifier is **ALT** (`local mainMod = "ALT"`, one place) because a host that also runs Hyprland on SUPER would catch the keys. ALT+Return terminal (kitty), ALT+Q close, ALT+E files (Thunar), ALT+D launcher (fuzzel), ALT+F fullscreen, ALT+V floating, ALT+L lock, ALT+SHIFT+E leave, ALT+arrows focus, ALT+1..5 workspaces (SHIFT moves the window), ALT+mouse drag and resize. H2 adds a settings switch between ALT and SUPER. |
| Waybar configuration and style | `desktop/waybar/config.jsonc`, `desktop/waybar/style.css` | Keep `@import "../heiss/theme/waybar-colors.css";` and use `@heiss_*` colours so Dark/Light keep working. |
| Key-binding descriptions | the comment lines above the binds | Russian and English texts for the welcome window: send them as a table (key, description en, description ru) if they differ from the placeholder comments. |
| The ß logo as SVG | `branding/logo/` (and `profile/airootfs/usr/share/heiss/`, Tier A) | Used by SDDM, GRUB and the installer. Today: `heiss-glyph-sand.svg`. |
| Wallpapers | `branding/wallpapers/` and the wallpaper packages under `profile/airootfs/usr/share/wallpapers/` (Tier A) | Dark and light, 3840x2160 plus 2560x1440 and 1920x1080. The package names `Heiss-Everyday` and `Heiss-Everyday-Light` stay; `heiss theme` points at them. |
| Hyprland on real hardware | a report | Whether the config works on your GPU; `hyprctl configerrors` output. |

Tier A files (logo, wallpapers, SDDM) need the label `design-approved` on the pull request.
