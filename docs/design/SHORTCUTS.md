# Keyboard shortcuts

Heiss OS adds **no custom shortcuts of its own**. Plasma and the Base applications already ship a consistent set; adding a second layer in `kglobalshortcutsrc` would be a Tier B change that I cannot test without a display, and a wrong entry silently overrides a default. This file documents the set, and `scripts/check-shortcuts.py` (CI) keeps the documented rows true and finds two applications fighting for one key.

## Shortcuts read from the packages (verified)

Source: `X-KDE-Shortcuts` in the desktop files of the package versions in the repositories on 2026-11-10 (dolphin 26.08.3, konsole 26.08.3, kcalc 26.08.3, plasma-systemmonitor 6.8.2, systemsettings 6.8.2, plasma-desktop 6.8.2). The `desktop` rows are checked by CI.

| Key | Action | Source | Desktop file |
|---|---|---|---|
| `Meta+E` | Open the file manager (Dolphin) | desktop | `org.kde.dolphin.desktop` |
| `Ctrl+Alt+T` | Open the terminal (Konsole) | desktop | `org.kde.konsole.desktop` |
| `Meta+I` | System Settings | desktop | `systemsettings.desktop` |
| `Meta+Esc` | System Monitor | desktop | `org.kde.plasma-systemmonitor.desktop` |
| `Meta+.` | Emoji selector | desktop | `org.kde.plasma.emojier.desktop` |
| `Calculator` | Calculator (KCalc), the dedicated keyboard key | desktop | `org.kde.kcalc.desktop` |

No two desktop files of the checked packages use the same key (collision check over all their entries).

## Plasma defaults that are not declared in desktop files (NOT verified)

Window management, KRunner, screen lock, screenshots and the launcher are registered by KWin, KRunner and Spectacle in code, not in files I can read on the build VM. I know them from KDE documentation, not from this system, so they are not listed as facts. After the next ISO build, open System Settings, Keyboard, Shortcuts in the VM (or send `~/.config/kglobalshortcutsrc` after a fresh login) and I will turn the real list into a table.

## Rules for adding a shortcut later

1. Prefer the application's own `X-KDE-Shortcuts`; add the row above (`desktop`) so CI guards it.
2. A system-wide file (`/etc/xdg/kglobalshortcutsrc`) only after the list from the VM exists and a conflict check against it passes.
3. Never reuse `Meta+<letter>` combinations of the table; never bind plain `Meta` (it opens the launcher).
