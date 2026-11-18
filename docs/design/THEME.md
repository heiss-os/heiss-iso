# Theme: Heiss Dark and Heiss Light in the Hyprland session

One command switches the whole session, as the user, without privileges: `heiss theme set dark|light` (`core/heiss_core/theme.py`). The colours come from the design tokens (`branding/tokens/heiss-tokens.json`, frozen palette); `scripts/gen-theme.py` renders them into `branding/tokens/generated/`, the package `heiss-theme` installs them to `/usr/share/heiss/desktop/theme/<dark|light>/`, and `heiss theme` copies the chosen set into the user's configuration.

## Commands

| Command | Does |
|---|---|
| `heiss theme get` | prints `dark` or `light` (exit 1 when none was set) |
| `heiss theme set dark\|light [--dry-run]` | applies every target below; `--dry-run` only reports |
| `heiss theme init` | first login (called by `heiss-session`): puts dark in place once, no reload, never overrides a later choice |
| `heiss theme status` | read-only: current theme and what differs from it (also the `theme` item of `heiss check`) |

Output: one line per target, `theme: <target>: <ok|changed|skipped|warn|failed>: detail`. Exit code 1 only when a target failed; a crash in one target is reported and does not hide the others.

## Targets

| Target | What is written or run | Live? |
|---|---|---|
| colors | `~/.config/heiss/theme/{hypr-colors.conf,waybar-colors.css,fuzzel.ini,mako.conf}`, `current` (the chosen name) | yes, through reload |
| wallpaper | symlink `~/.config/heiss/theme/wallpaper` to `Heiss-Everyday` (dark) or `Heiss-Everyday-Light`; a link to anything else is left alone | yes (`heiss-wallpaper` restarts swaybg) |
| gtk | `~/.config/gtk-3.0` and `gtk-4.0`: `settings.ini` (prefer-dark, Adwaita icons and cursor, Inter) and `gtk.css` (named colours from the tokens, libadwaita reads them); only files that start with the Heiss header are overwritten | GTK 4: at the next start of an app |
| qt | `~/.config/qt6ct/qt6ct.conf` (Fusion style, custom palette) and `colors/heiss.conf` (22 palette roles); a `qt6ct.conf` of the user is left alone, only the colour file is updated | at the next start of an app |
| color-scheme | `gsettings set org.gnome.desktop.interface color-scheme prefer-dark\|prefer-light`: GTK 4 and libadwaita apps, the GTK portal, and kitty (its `*-theme.auto.conf` files of `heiss-theme` follow it) | yes |
| cursor | `hyprctl setcursor Adwaita 24` | yes |
| reload | `hyprctl reload`, `makoctl reload`, `pkill -USR2 -x waybar` (own processes only) | yes |

Outside a running Hyprland session (`HYPRLAND_INSTANCE_SIGNATURE` unset) cursor and reload are skipped; the programs read the files at their start. The Qt variable `QT_QPA_PLATFORMTHEME=qt6ct` is set by `heiss-session`. The Heiss Qt windows draw from the tokens themselves.

## Rules

- Only fixed argument lists are run, never a shell. Files are written atomically (temporary file, then rename).
- A file the user wrote (no Heiss header) is never overwritten; the result says `warn` and names it. To take a file over, remove the header line.
- No new literal colours anywhere: a test checks the desktop configs, and the generated files carry the generator header.

## Not verified

Everything at runtime (no session was started): the 22-role colour file against qt6ct 0.11, Waybar's `SIGUSR2` reload of the CSS import, `hyprctl reload` re-reading sourced colour files, `makoctl reload`, kitty following `color-scheme` through the portal, libadwaita taking the named colours of `gtk.css`. See the FINAL VM TEST LIST, "H1b".
