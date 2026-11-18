# What the owner still has to supply

The Hyprland session ships clean placeholders (`desktop/`). Everything below replaces a placeholder without a code change.

| What | Where it goes | Notes |
|---|---|---|
| Hyprland configuration | `desktop/hypr/hyprland.conf` (installed to `/usr/share/heiss/desktop/hypr/`, copied to `~/.config/hypr/` at the first login, never overwritten) | Keep the last line `source = ~/.config/hypr/heiss-user.conf` and the colour include `source = ~/.config/heiss/theme/hypr-colors.conf` (Heiss Dark and Light switch through it). Put a comment line with the description directly above every `bind` line: the welcome window (H2) lists them. |
| Waybar configuration and style | `desktop/waybar/config.jsonc`, `desktop/waybar/style.css` | Keep `@import "../heiss/theme/waybar-colors.css";` and use `@heiss_*` colours so Dark/Light keep working. |
| Key-binding descriptions | the comment lines above the binds | Russian and English texts for the welcome window: send them as a table (key, description en, description ru) if they differ from the placeholder comments. |
| The ß logo as SVG | `branding/logo/` (and `profile/airootfs/usr/share/heiss/`, Tier A) | Used by SDDM, GRUB and the installer. Today: `heiss-glyph-sand.svg`. |
| Wallpapers | `branding/wallpapers/` and the wallpaper packages under `profile/airootfs/usr/share/wallpapers/` (Tier A) | Dark and light, 3840x2160 plus 2560x1440 and 1920x1080. The package names `Heiss-Everyday` and `Heiss-Everyday-Light` stay; `heiss theme` points at them. |
| Hyprland on real hardware | a report | Whether the config works on your GPU; `hyprctl configerrors` output. |

Tier A files (logo, wallpapers, SDDM) need the label `design-approved` on the pull request.
