# GTK applications: how they get the Heiss theme

Status 2026-11-18: the KDE-era audit (kde-gtk-config, Breeze GTK, the KDE portal) no longer applies and was removed. In the Hyprland session `heiss theme` writes the GTK files, GSettings and the Qt palette: see `docs/design/THEME.md`. Portals: `xdg-desktop-portal-hyprland` and `xdg-desktop-portal-gtk` (the `hyprland` package ships `hyprland-portals.conf`). Report script for the VM: `heiss-gtk-audit <label>` (read-only).
