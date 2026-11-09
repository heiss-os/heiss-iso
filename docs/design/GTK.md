# GTK applications: how they get the Heiss theme

Status: audit and plan, no GTK configuration is shipped by Heiss yet. Facts marked (db) come from the Arch package database, read in CI on 2026-11-10 (versions: Plasma 6.8.2, kde-gtk-config 6.8.2, xdg-desktop-portal 1.22.1). Everything about runtime behavior is NOT verified: nobody has run a GTK application in a Heiss session yet.

## What is already in the ISO (Essentials, so also Base and Custom)

`kde-gtk-config`, `breeze-gtk`, `xdg-desktop-portal-kde`, `xdg-desktop-portal-gtk`. A unit test keeps them in every profile.

## What kde-gtk-config provides (db)

- A kded module `gtkconfig` (`usr/lib/qt6/plugins/kf6/kded/gtkconfig.so`): Plasma's own place that writes GTK settings from the KDE settings.
- GTK3 modules `libcolorreload-gtk-module.so` (reloads colors when they change, no logout) and `libwindow-decorations-gtk-module.so` with `usr/share/themes/Breeze/window_decorations.css` (window buttons of GTK client-side decorations in the Breeze style).
- Dependencies: `xsettingsd` (live settings for X11 GTK apps) and `xdg-desktop-portal-gtk`; optional `gtk3`.
- kconf_update helpers (`gtk_theme`, removal of a deprecated GTK4 option).

`breeze-gtk` ships the GTK3 themes `Breeze` and `Breeze-Dark` (db, the CI listing shows `Breeze-Dark`).

## Consequence for Heiss

Plasma already owns the GTK configuration files and the Dark/Light reload. A second writer (for example a Heiss script editing `~/.config/gtk-4.0/gtk.css`, or an `/etc/xdg/gtk-*.0/settings.ini` that fights it) would race with `gtkconfig`. So this PR ships no GTK configuration. It ships a way to see what really happens:

- `heiss-gtk-audit <label>` (package `heiss-core`, `/usr/bin`): read-only, offline report: KDE color scheme and accent, package versions, the portal's `org.freedesktop.appearance` values (`color-scheme`, `accent-color`), GSettings, whether kded's `gtkconfig` module is loaded, system-wide and per-user GTK files (first 40 lines each), plus a short list of screenshots to take.

## What we expect (from background knowledge, to be confirmed by the audit)

1. GTK3 apps (Firefox, GTK dialogs) follow the KDE color scheme through `gtkconfig`, the Breeze theme and the color-reload module, so HeissDark/HeissLight colors reach them.
2. libadwaita (GTK4) apps ignore `gtk-theme-name`. They follow the portal `color-scheme` (Dark/Light) and the accent color. Named-color overrides work only through the user file `~/.config/gtk-4.0/gtk.css`. Widgets that libadwaita styles itself (rounded headerbars, switches, some popovers) will NOT match Breeze/Heiss exactly, and no GTK theme can change that.
3. Light/Dark reaches libadwaita apps through the portal setting that xdg-desktop-portal-kde provides.

## Decision rule after the audit

| Audit shows | Next step |
|---|---|
| GTK3 and GTK4 follow Dark/Light and colors look right | ship nothing more; document the limits |
| GTK3 right, libadwaita colors default blue | add a Heiss override layer for libadwaita named colors, generated from the tokens (`branding/tokens/generated/gtk-4.0/`, already staged), applied in a way that does not clash with `gtkconfig` (decided with the observed file contents) |
| `gtkconfig` not loaded or files missing | ship a small Plasma-side fix instead of overrides |
| Dark/Light does not reach GTK at all | investigate the portal configuration |

The AA text variants (`accent_text`, `success_color`, ...) in the generated CSS become relevant only in the second case.

## Please do in the VM

Installed or live session, logged into the desktop:

```bash
heiss-gtk-audit dark      # Heiss Dark session
# System Settings -> Appearance -> Global Theme -> Heiss Light, then:
heiss-gtk-audit light
```

Send `~/heiss-gtk-audit-dark.txt` and `~/heiss-gtk-audit-light.txt` and the screenshots listed at the end of the report (Firefox, a GTK file dialog, a GTK window's buttons next to Dolphin's, any libadwaita app), Dark and Light.
