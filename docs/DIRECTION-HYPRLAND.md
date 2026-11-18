# Direction change: Hyprland desktop and a terminal installer

Status: plan and inventory (stage H0, docs only). Source: `~/share/heiss-task-31.md`. The KDE image `heiss-2026.11.17` stays as the "KDE preview"; nothing here changes it. Anything about Plasma, the Qt wizard look or Calamares in `heiss-task-30.md` that was not finished is obsolete.

## 1. What changes

| Area | Now | Target |
|---|---|---|
| Desktop | KDE Plasma 6 (KWin, plasmashell, Dolphin, Konsole) | Hyprland + Waybar, Heiss look, Heiss key bindings |
| Login | SDDM, Breeze theme with a Heiss override, Plasma session | SDDM stays, own Heiss theme without Plasma, Hyprland session |
| Live session | Plasma autologin, Calamares started from it | H1: same Hyprland session, Calamares started from it. H3: no graphical live session, console autologin, terminal installer `heiss-installer` |
| Installer | Calamares 3.4.2 (Qt6, AUR build) with QML branding | Terminal installer (Python). Calamares stays hidden until the owner confirms the new one in a VM, removed in H5 |
| First run | `heiss-welcome` Qt wizard (11 steps) | Welcome window with the key bindings (H2); the installer asks the questions (H3) |
| Settings | `heiss-control` (Qt, sidebar of pages) plus stock KDE System Settings | One light settings window (H2): Appearance, Display, Keyboard, Network and Bluetooth, Audio, Packages, Hardware, System |
| Theme switch | `heiss theme` = Plasma Look-and-Feel + theme sync | `heiss theme` for GTK, Qt, kitty, Waybar, wallpaper, cursor, from the design tokens |
| GRUB | Heiss theme, jagged font | Inter font from `grub-mkfont`, balanced layout (H4, Tier A) |

## 2. What is removed (completely, with code, helper actions, manifests, docs, tests)

- **Detail level** (old wizard step 4): `answers.level`, wizard step `level`, the viewmodel and QML for it, strings.
- **Privacy and protection** (old step 7): `core/heiss_core/privacy.py` (Wi-Fi MAC modes, screen-lock levels), `answers.privacy`, `--privacy` in `heiss profile apply|diff`, helper action `WritePrivacy` and its polkit action use, `check_privacy_level`, control-centre page `privacy_view.py`, KDE screen-locker keys.
- **Backups and snapshots** (old step 9): wizard step `backups`, helper action `CreateSnapshot`, the `_snapshot_step` before install, remove and update, `snapper` optdepends of `heiss-helper`, the snapshot description policy, the Updates-and-snapshots page of the control centre (the updates part moves to the settings window).
- **LTS kernel as an add-on** (`profiles/addon-lts-kernel.toml`). See section 6 for the NVIDIA rule.
- **Cyber extended / Developer extended as add-ons**: Cyber and Developer exist only as profiles. Their extra tools move into the package catalogue (H3) as ordinary entries.
- **Qt wizard steps 2 and 3 look**, the Plasma-bound parts of PR B of round 25 (not implemented).
- Removed in H1 (session): all Plasma and KDE packages and files of section 4. Removed in H5: Calamares and its branding, the Qt wizard code that no longer exists, leftovers and obsolete CI jobs.

Every removal lands in the PR of its stage, never half-way: a PR that removes a feature also removes its tests and docs, and statements about it in the docs are fixed in H5 at the latest.

## 3. What is kept

- Archiso base, GRUB with the safe-graphics entry (`heiss-safe-graphics`), signed `[heiss]` repository, `heiss-keyring`, root locked after install (the owner is still deciding this: not changed), no telemetry.
- Engine `heiss-core` (manifests, resolver, hardware detection, `heiss check`, state), helper `heiss-helper` with polkit and the allowlist, hardware profiles including the safe-graphics and driver-removal flow.
- Design tokens (`branding/tokens/heiss-tokens.json`, frozen palette), Heiss Dark and Heiss Light names, Inter and JetBrains Mono, sand accent, wallpapers `Heiss-Everyday` and `Heiss-Everyday-Light` (packages keep their names).
- Language, appearance (dark or light only), profile (Base, Custom, Cyber, Developer), additional packages, hardware, the other steps adapted to the terminal, summary.
- The Python stack, the tests, CI, the agents and the Tier A protection.

## 4. Inventory of everything Plasma-specific

### 4.1 By package (ISO list `profile/packages.x86_64` and manifests)

| Where | Plasma or KDE package | Replacement |
|---|---|---|
| ISO list | `plasma-desktop`, `konsole`, `dolphin`, `kate`, `xdg-desktop-portal-kde`, `polkit-kde-agent`, `plasma-nm`, `ark`, `gwenview`, `okular`, `spectacle`, `kscreen`, `plasma-pa` | Hyprland stack (section 5); Base apps below |
| `essentials` | `plasma-nm`, `plasma-pa`, `bluedevil`, `plasma-desktop`, `plasma-workspace`, `kwin`, `kscreen`, `powerdevil`, `kinfocenter`, `polkit-kde-agent`, `xdg-desktop-portal-kde`, `kde-gtk-config`, `breeze-gtk`, `konsole`, `dolphin`, `plasma-firewall` | `network-manager-applet`, `pavucontrol`, `blueman`, `hyprland`, `waybar`, `brightnessctl`, `hyprpolkitagent`, `xdg-desktop-portal-hyprland`, `kitty`, `thunar`; firewall stays as `firewalld` (no GUI front end in the session; the settings window shows its state) |
| `base` | `kate`, `ark`, `gwenview`, `okular`, `spectacle`, `kcalc`, `plasma-systemmonitor`, `haruna`, `kio-extras`, `ffmpegthumbs`, `kdegraphics-thumbnailers`, `filelight`, `partitionmanager`, `plasma-disks`, `discover`, `print-manager` | `mousepad`, `file-roller`, `loupe`, `papers`, `grim`+`slurp`, `galculator`, `mate-system-monitor`, `mpv`+`celluloid`, `tumbler`+`ffmpegthumbnailer`, `baobab`, `gnome-disk-utility`, `system-config-printer`; `keepassxc`, `cups`, `cups-filters`, `sane-airscan` stay |
| `cyber`, `developer` | `wireshark-qt` (Qt, not KDE: stays) | none needed |
| add-ons | `addon-kitty`, `addon-thunar` | become part of `essentials` (default apps), add-on files removed in H1 |
| `heiss-control` optdepends | `kconfig`, `plasma-workspace`, `systemsettings` | removed |
| `heiss-theme` optdepends | `konsole` | removed |
| Calamares build (AUR, `~/localrepo`) | `kcoreaddons`, `kpmcore` (KDE Frameworks libraries, not Plasma; from `pacman -Qip ~/localrepo/calamares-3.4.2-2-x86_64.pkg.tar.zst`, Depends On: kcoreaddons kpmcore libpwquality qt6-declarative qt6-svg yaml-cpp) | stay for the hidden fallback until H5 |

All replacement names exist in the official repositories (`pacman -Si`, checked 2026-11-18 against the local sync database): hyprland 0.57.0-1, waybar 0.15.0-3, hyprlock 0.9.6-3, hypridle 0.1.8-2, swaybg 1.2.2-1, fuzzel 1.15.0-2, mako 1.11.0-1, hyprpolkitagent 0.2.0-1, xdg-desktop-portal-hyprland 1.4.1-2, xdg-desktop-portal-gtk 1.15.3-2, grim, slurp, wl-clipboard, network-manager-applet, blueman, pavucontrol, brightnessctl, kitty 0.49.2-1, thunar 4.20.10-1, qt6-wayland 6.12.0-1, qt6ct 0.11-9, adwaita-cursors 51.0-1, adwaita-icon-theme 51.0-1, ttf-nerd-fonts-symbols-mono 3.5.1-1, inter-font 4.1-1. Not in the repositories (so not used): `rofi-wayland`, `bibata-cursor-theme`, `ttf-font-awesome`.

### 4.2 By file

| File or directory | Role now | Fate |
|---|---|---|
| `profile/airootfs/usr/share/plasma/look-and-feel/org.heiss.{dark,light}.desktop/` (defaults, layouts JS, previews, splash QML, metadata) | Global themes, dock and panel layout | Removed in H1 (Tier A) (done in H1a) |
| `profile/airootfs/usr/share/color-schemes/Heiss{Dark,Light}.colors` | KDE colour schemes | Removed in H1 (Tier A); tokens stay (done in H1a) |
| `profile/airootfs/etc/xdg/{kdeglobals,kwinrc,kscreenlockerrc,ksplashrc}` | KDE defaults | Removed in H1 (done in H1a) |
| `profile/airootfs/etc/sddm.conf.d/{autologin,heiss-theme}.conf`, `usr/share/sddm/themes/breeze/theme.conf.user` | Breeze theme override, live autologin into `plasma.desktop` | Rewritten in H1 (Tier A): own theme, `heiss.desktop` (done in H1a) |
| `profile/airootfs/usr/local/bin/heiss-setup-dock.sh` and `etc/xdg/autostart/heiss-setup-dock.desktop` | Dock fallback | Removed in H1 (Tier A) (done in H1a) |
| `usr/local/bin/heiss-set-wallpaper.sh`, `heiss-theme-sync.sh`, their autostart entries | Plasma wallpaper, theme sync | Replaced by `heiss theme` (H1) (done in H1a) |
| `usr/local/bin/heiss-start-installer.sh` | waits for `plasmashell`, then `sudo -E calamares` | Rewritten in H1 (waits for the Hyprland session) (done in H1a) |
| `usr/local/share/applications/org.kde.kwrite.desktop` and other hide stubs | menu stubs | Reviewed in H1; `check-menu.py` follows (done in H1a) |
| `etc/xdg/mimeapps.list` | associations point to KDE apps | Rewritten in H1 (done in H1a) |
| `branding/tokens/generated/{kde,konsole}/` and the KDE and Konsole renderers in `scripts/heiss_tokens.py`, `scripts/gen-theme.py` | Generated KDE colours and Konsole schemes | Removed in H1; new generators for Waybar, fuzzel, mako, hyprlock, qt6ct, GTK settings |
| `branding/tokens/generated/{gtk-3.0,gtk-4.0,kitty}/` | GTK and kitty themes | Kept, extended (done in H1a) |
| `packages/heiss-theme/PKGBUILD` | installs Konsole files, kitty files | Konsole removed, desktop configs added |
| `core/heiss_core/themesync.py` (458 lines), `check.py` KDE items, `cli.py` `theme sync` | Plasma theme sync | Removed in H1a (done); `heiss theme get|set|init|status` in H1b (done, `docs/design/THEME.md`) |
| `system.py:kde_value`, `apply.py:kwriteconfig`, `manifest.py` and `resolver.py` `kde_settings`, `privacy.py` KDE keys | KDE settings writes for the privacy levels | Removed in H2 together with the privacy code and the old wizard |
| `core/data/heiss-gtk-audit` | audit script for the KDE GTK path | Rewritten in H1b (done) |
| `control/heiss_control/{theme,tools,privacy_view}.py`, `welcome/heiss_welcome/theme.py` | `plasma-apply-lookandfeel`, `kreadconfig6`, `systemsettings` | Replaced in H1 by calls to `heiss theme`; the apps themselves are replaced in H2 |
| `scripts/check-menu.py`, `check-launchers.py`, `check-shortcuts.py`, `gen-lnf-previews.py`, `audit-image.sh` (Plasma paths) | Checks of Plasma layout files, `X-KDE-Shortcuts` | Replaced by checks of the Hyprland and Waybar configs (H1) (done in H1a) |
| `.github/workflows/core.yml` jobs "tool the wizard uses ... plasma-workspace", "... kconfig", "dock pins" | package-database checks for KDE tools | Removed in H1 (done in H1a) |
| Tests: `test_lnf_layout`, `test_themesync` (rewritten), `test_dock_lock`, `test_shortcuts`, `test_menu`, `test_terminal`, `test_launchers`, `test_check`, `test_gtk`, `tests/test_mimeapps.py`, `tests/test_installer_desktop.py`, `test_calamares_quiet` (kept until H5) | cover the above | Removed or rewritten together with the code |
| Docs: `docs/design/GTK.md`, `docs/apps/ASSOCIATIONS.md`, `docs/CONTROL-CENTER.md`, `docs/WELCOME.md`, `docs/PROFILES.md` (`docs/design/{THEME-SYNC,SHORTCUTS}.md` and `docs/apps/{LAUNCHER,TERMINAL-HERE}.md` deleted in H1a) | describe the Plasma behaviour | Rewritten in the stage that changes the behaviour; leftovers swept in H5 |
| Calamares: `profile/airootfs/etc/calamares/`, `usr/share/calamares/branding/heiss/`, `scripts/heiss-calamares-build.sh`, `scripts/patches/calamares-heiss-layout.patch`, `usr/local/share/applications/calamares.desktop` (under `profile/airootfs/`) | installer | Kept hidden through H3, removed in H5 (Tier A) |

Tier A paths touched by H1 (label `design-approved` needed, checksums updated in the same PR): `etc/sddm.conf.d/`, `usr/share/plasma/look-and-feel/`, `usr/share/color-schemes/`, `usr/local/bin/heiss-setup-dock.sh`, `usr/share/heiss/` (new desktop drop-in directory), `usr/share/libalpm/hooks/` if a hook is added.

## 5. Choices for the Hyprland session (small decisions, recorded in DECISIONS.md)

| Part | Choice | Why |
|---|---|---|
| Compositor, bar | `hyprland`, `waybar` | the task |
| Launcher | `fuzzel` | small, Wayland native, one ini file from the tokens; `wofi` is GTK3 and larger (my judgement, not measured), `rofi-wayland` is not in the repositories |
| Notifications | `mako` | tiny, one config file, themable; `swaync` is larger and brings a second UI |
| Polkit agent | `hyprpolkitagent` | needed by the helper prompts and Thunar mounts; small Qt6 agent from the same project as Hyprland (its Qt dependencies are already pulled by SDDM) |
| Portals | `xdg-desktop-portal-hyprland` (screencast, screenshot) + `xdg-desktop-portal-gtk` (file chooser, settings, dark/light) with a `hyprland-portals.conf` | the usual pair; the GTK portal answers `org.freedesktop.appearance color-scheme` |
| Wallpaper | `swaybg` | one process per image, restart to change: trivial to test and to switch live; `hyprpaper` and `awww` are larger and their IPC is not needed |
| Idle and lock | `hypridle` + `hyprlock` | same project, configs from tokens |
| Screenshots | `grim` + `slurp` + `wl-clipboard` (bind lines call them directly) | fewer layers than `hyprshot` |
| Audio | existing PipeWire, WirePlumber, `pavucontrol`; Waybar `pulseaudio` module | |
| Network and Bluetooth | Waybar `network` and `bluetooth` modules; `network-manager-applet` (tray, `nm-connection-editor`) and `blueman` (pairing agent, manager) | no Plasma applets |
| Brightness | `brightnessctl` | |
| Terminal, files | `kitty`, `thunar` (+ `thunar-volman`, `gvfs`, `tumbler`) | the task |
| Fonts, icons, cursor | `inter-font`, `ttf-jetbrains-mono`, `ttf-nerd-fonts-symbols-mono` (Waybar icons), `noto-fonts`, `noto-fonts-emoji`, `adwaita-icon-theme`, `adwaita-cursors` | all in `extra`; Papirus (111 MiB) is too large |
| GTK theming | generated `settings.ini`, `gtk.css` (the existing token CSS) and GSettings `color-scheme`, written by `heiss theme` | no `kde-gtk-config`; libadwaita follows the portal |
| Qt theming | `qt6-wayland`, `qt6ct` with a colour scheme generated from the tokens, `QT_QPA_PLATFORMTHEME=qt6ct`; Heiss's own Qt apps draw from the tokens themselves | Kvantum is not needed |
| Session start | SDDM starts `heiss.desktop` (shipped by `heiss-desktop`, runs `/usr/bin/heiss-session`, which starts Hyprland); environment and `uwsm` not used in H1 | fewer moving parts; revisit if systemd user integration is needed |
| SDDM greeter | X11 greeter (`xorg-server` stays in the image, SDDM depends on it), own QtQuick theme using only `QtQuick`, `QtQuick.Controls`, `QtQuick.Layouts` and `SddmComponents`-free code | the Breeze theme imports `org.kde.plasma.*` and `org.kde.kirigami`, so it cannot be used without Plasma. Wayland greeter would need `weston` or `cage` as an extra compositor; not chosen |
| Config drop-in place | `/usr/share/heiss/desktop/{hypr,waybar,...}/` copied to `~/.config` at first login (never over an existing file) | replacing the files needs no code change |
| Software rendering | `WLR_RENDERER_ALLOW_SOFTWARE=1` in the safe-graphics session environment | VirtualBox without 3D acceleration |

## 6. The LTS kernel and the NVIDIA rule

`heiss-safe-graphics` (`/etc/grub.d/41_heiss_safe`) loops over `linux` and `linux-lts` and writes an entry only for a kernel that exists. It works with `linux` alone: the entry boots with `nomodeset` and the NVIDIA modules blacklisted. It does not need the LTS add-on. The NVIDIA hardware profiles (only `hardware/gpu-nvidia-open.toml` lists them; the legacy and hybrid NVIDIA profiles do not mention an LTS kernel) install `linux-lts` and `nvidia-open-lts` themselves (`packages`, `keep_on_remove = ["linux-lts"]`) as a second kernel to start from. So removing the add-on (`addon-lts-kernel`) changes nothing for that rule; the hardware step keeps working unchanged and only the add-on entry and its two test lines go away. Not verified: a real boot of the safe-graphics entry (listed in the FINAL VM TEST LIST).

## 7. Dependency check: Heiss packages

| Package | Depends today | On Plasma or KDE libraries? | What replaces it |
|---|---|---|---|
| `heiss-core` | `python` | No at install time. The code calls `kreadconfig6`, `kwriteconfig6`, `plasma-apply-lookandfeel`, `busctl org.kde.*` (themesync, check, apply) | Calls removed in H1; `heiss theme` writes GTK, Qt, kitty, Waybar and wallpaper itself |
| `heiss-helper` | `heiss-core python python-gobject polkit dbus`, optdepends `snapper` | No | Snapshot and privacy actions removed (H2); the rest unchanged |
| `heiss-welcome` | `python pyside6 heiss-core` | No (QtQuick Controls only), but applies the theme with `plasma-apply-lookandfeel` | Replaced in H2 by the welcome window (key bindings) |
| `heiss-control` | `python pyside6 heiss-core`, optdepends `kconfig`, `plasma-workspace`, `systemsettings` | Optional only | Replaced in H2 by the settings window |
| `heiss-theme` | optdepends `konsole`, `kitty` | Konsole files | Desktop theme files for the Hyprland stack |
| `heiss-profile-essentials`, `-base` | generated from the manifests | Yes: they pull Plasma | Regenerated from the new manifests (H1) |
| `heiss-safe-graphics` | `grub` | No | unchanged |
| `heiss-keyring` | none | No | unchanged |

## 8. Qt or something lighter for the welcome and settings apps

Recommendation: **keep Qt (PySide6 with QtQuick Controls) on Wayland with `qt6-wayland`** for the welcome and settings windows (H2), do not rewrite to GTK now.

Reasons:
1. SDDM already depends on `qt6-base` and `qt6-declarative`, so the Qt runtime is in the image either way; `pyside6` (52 MiB) is the only extra.
2. All logic is in toolkit-free Python (viewmodels, models, `heiss-core`, about 2600 lines of `core/heiss_core` plus the viewmodels, with their tests). Only the QML skin changes. A GTK rewrite would redo the part that is already tested for no user-visible gain.
3. `scripts/render-gui.py` renders the QML windows offscreen to PNGs, so the owner and I can look at a result without a VM. There is nothing equivalent for GTK here.
4. Our windows draw from the design tokens themselves, so they do not need Plasma's colour mechanism.

Cost, said openly: GTK3 via `python-gobject` would start a little faster and use less memory, and GTK is already present for Thunar, Waybar and the applets. If H2 measures the Qt windows as too slow on the target VM, the viewmodel layer allows a later switch. Not measured yet.

## 9. Order and size

H0 (this document), H1 session (large: split in two PRs if it passes about 600 lines of hand-written change: H1a packages, manifests, SDDM, session configs, first login; H1b `heiss theme` rebuild and `heiss check`), H2 welcome and settings windows, H3 terminal installer, H4 boot look, H5 cleanup. Every stage updates `DECISIONS.md`, `docs/PLAN-STATE.md` and the FINAL VM TEST LIST.

## 10. Questions that block

None for H0 and H1. Decisions that would need the owner later: removing the Calamares branding (Tier A, H5), the root account policy (the owner is deciding; unchanged), manual partitioning (out of scope for H3, recorded).

## 11. Not verified in this plan

- Functional fit of the replacements: `plasma-firewall` by `firewalld` alone, `kio-extras` and `kdegraphics-thumbnailers` by `tumbler` + `ffmpegthumbnailer`.
- That the X11 greeter with an own QtQuick SDDM theme starts, that Hyprland starts in VirtualBox (needs 3D acceleration or `WLR_RENDERER_ALLOW_SOFTWARE=1`), Qt versus GTK startup time, and a real safe-graphics boot with `linux` only.
- Package sizes and versions are from the local sync database of 2026-11-18.
