# "Open terminal here" and the embedded terminal

## What Base does (checked in the packages)

Facts read from the real package contents on 2026-11-10 (dolphin 26.08.3, konsole 26.08.3, kio 6.31.0):

- Dolphin has the actions **Open Terminal Here** (`open_terminal_here`, context menu of a folder or the empty area), **Open Terminal** (`open_terminal`) and the **Terminal Panel** (`show_terminal_panel`, focus/defocus actions). Seen as strings in the `dolphin` binary.
- The terminal panel needs a KParts terminal: `konsole` ships `usr/lib/qt6/plugins/kf6/parts/konsolepart.so`. Konsole is in Essentials, so the panel works without anything else.
- "Open Terminal Here" starts a terminal through KIO's `KTerminalLauncherJob` (symbol present in the `dolphin` binary). `libKF6KIOGui` contains the settings keys `TerminalService` and `TerminalApplication` and the fallback value `konsole`. So with no setting at all, KDE opens **Konsole**, and installing another terminal does not change that.
- No Heiss file sets `TerminalService`/`TerminalApplication`; nothing is needed for Base. I did not edit `/etc/xdg/kdeglobals` (Tier B) to pin it.

Guarded by `core/tests/test_terminal.py`: Base contains Konsole and Dolphin and no second terminal or file manager; the kitty and Thunar add-ons are not part of any profile closure; `mimeapps.list` does not hand folders to another file manager.

## What the add-ons change (NOT verified)

- **kitty add-on:** installing kitty adds a menu entry and kitty's own settings (themed through `heiss-theme`). By the facts above, Dolphin's "Open Terminal Here" should stay on Konsole. To make kitty the choice, the user selects it in System Settings, Default Applications, Terminal Emulator. Not tested in a VM.
- **Thunar add-on:** Thunar's own "Open Terminal Here" is a Thunar custom action that uses the Xfce "preferred terminal" mechanism, not the KDE setting. I did not verify which terminal it starts when only Konsole and kitty are installed, nor where a system-wide default for it would live. Until verified, nothing is configured for it: if it picks the wrong terminal, the fix is a Heiss-owned custom action file, to be added after the VM test.
- `xdg-open` for folders uses `inode/directory` from `mimeapps.list` (Dolphin); the Thunar add-on does not change it.

## Please test in the VM (Base)

1. Right-click an empty area in a folder in Dolphin: "Open Terminal Here" is in the menu; click it: Konsole opens in that folder (`pwd`).
2. Press `F4` in Dolphin: the terminal panel appears below, and `cd` follows folder navigation.
3. Right-click a folder: the action opens Konsole in that folder, not in the parent.
4. After installing the kitty add-on repeat step 1: which terminal opens?
5. After installing the Thunar add-on: right-click in Thunar, "Open Terminal Here": which terminal opens?
