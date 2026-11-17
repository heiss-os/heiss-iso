# Theme sync

One Dark/Light switch (Global Theme, or Plasma's automatic light/dark switching, both change `~/.config/kdeglobals`) must leave no half-switched desktop. The user path unit `heiss-theme-sync.path` watches `kdeglobals` and runs `heiss theme sync` (via `/usr/local/bin/heiss-theme-sync.sh`), and the autostart entry runs it once at login. Disable with `HEISS_THEME_SYNC=0`.

## What happens, in order

Plasma first applies the Look-and-Feel defaults (color scheme, accent, icons, widget style, Plasma style, splash). Then `heiss theme sync` waits for plasmashell and 2 s for the settings to settle, reads the color scheme, and runs these targets once, one log line each:

| Target | Does | Result values |
|---|---|---|
| launcher-icon | asks plasmashell to switch the Kickoff icon (`heiss-launcher-sand` or `-sand-light`); a custom icon is left alone | ok / failed |
| wallpaper | sets the wallpaper package of the theme (`Heiss-Everyday` dark, `Heiss-Everyday-Light` light, fill mode crop) on the desktop and the lock screen; a wallpaper the user chose is left alone | changed / ok / skipped / failed |
| konsole | sets `DefaultProfile` (Heiss-Dark or Heiss-Light) in `konsolerc` and switches running Konsole sessions through D-Bus | changed / ok / warn / skipped |
| plasma-consistency | compares color scheme, icon theme, widget style, Plasma style and splash with the Look-and-Feel defaults of the active theme (accent excluded) and REPORTS differences | ok / warn |
| gtk | checks the kde-gtk-config module `gtkconfig` is loaded and GSettings `color-scheme` agrees | ok / warn / failed |
| portal | checks the portal `org.freedesktop.appearance color-scheme` (1 dark, 2 light) | ok / warn |
| kitty | nothing to switch: kitty follows the portal through the `*-theme.auto.conf` files of package heiss-theme | ok / warn / skipped |

A color scheme that is not HeissDark/HeissLight (the user picked another) leaves everything alone. If the scheme cannot be read, that is a visible failure, not silence. A crash in one target is reported and does not hide the others. Exit code 1 only when a target failed; warnings do not fail the unit.

Log: stdout (journal: `journalctl --user -u heiss-theme-sync`) and `~/.local/state/heiss/theme-sync.log` (rotated at 200 KiB). Report only: `heiss theme status` (also `heiss theme sync --dry-run --no-wait`).

## Package heiss-theme (new, in the ISO)

Generated from the tokens: Konsole color schemes and profiles (JetBrains Mono 11, `Parent=FALLBACK/`, opacity 1) in `/usr/share/konsole`, `/etc/xdg/konsolerc` (default profile Heiss Dark), kitty `/etc/xdg/kitty/kitty.conf` plus `dark-theme.auto.conf`, `light-theme.auto.conf`, `no-preference-theme.auto.conf`, and the plain theme files in `/usr/share/heiss/kitty`. Konsole and kitty stay optional; kitty is an add-on.

## First login

Once per user (mark `~/.local/state/heiss/theme-first-login`): if the desktop started on a color scheme that is not a Heiss one (Plasma's own default is Breeze), `heiss theme sync` applies Heiss Dark with `plasma-apply-lookandfeel` and logs a `first-login` line. The mark is written either way, so a theme the user picks later is never overridden. If applying fails, there is no mark and the next login tries again. System defaults in `/etc/xdg/kdeglobals` (`LookAndFeelPackage`, `DefaultDarkLookAndFeel`, `DefaultLightLookAndFeel`, `AutomaticLookAndFeel=false`) are the primary mechanism; this is the safety net.

## What the sync does NOT do

It does not write the color scheme, icons, widget style, Plasma style or splash (kdeglobals, plasmarc, ksplashrc, kwinrc): differences are reported only. The only Plasma-owned values it writes are the wallpaper (through plasmashell) and the lock screen wallpaper (`kscreenlockerrc`), and only while they are Heiss wallpapers. GTK and libadwaita are handled by kde-gtk-config and the portal (see `GTK.md`). The wallpaper is applied through plasmashell (no read-back); whether it is ours is read from `plasma-org.kde.plasma.desktop-appletsrc`.

## Not verified

Everything runtime: that the path unit fires on a switch, that `busctl` can reach plasmashell, kded and the portal as written, the D-Bus names used for running Konsole sessions (`org.kde.konsole-<pid>`, `/Sessions/<n>`, `Session.setProfile`), that the profile name is the one `setProfile` expects, that kitty finds the `*.auto.conf` files in `/etc/xdg/kitty` and applies them, and Plasma's automatic light/dark switching. The logic is unit tested against a scripted desktop only.

Test in the VM: switch Heiss Dark -> Heiss Light in System Settings, then `journalctl --user -u heiss-theme-sync --no-pager | tail -20` and `cat ~/.local/state/heiss/theme-sync.log`; open a new Konsole window and one that was already open (the colors must match the theme); repeat Light -> Dark. Send the log and screenshots.
