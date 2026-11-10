# Design and system audit (Phase 0)

Method: reading the repository at `main` (`e0eeb08`) and querying the package databases on the build VM (2026-11-09). No screenshot was available, so every visual statement is "to verify" until the owner sends captures (list in section 6). Nothing here was run in a VM by me.

## 1. Differences from the statements in the master plan, section 1

| # | Plan / CLAUDE.md says | Found | Consequence |
|---|---|---|---|
| 1 | A "heiss-theme-sync" service may be fuller than PR 30 | It exists: `heiss-theme-sync.sh` + user `.path` and `.service` + autostart. It ONLY switches the Kickoff launcher icon (`heiss-launcher-sand` / `-sand-light`) by reading `ColorScheme` from kdeglobals. Everything else relies on Plasma applying the LnF `defaults`. | Extension in Phase 4 starts from a small base. |
| 2 | CLAUDE.md: `[heiss-local]` uses an absolute path `/home/heiss-os/localrepo` | `profile/pacman.conf` uses `file://@LOCALREPO@`; `scripts/heiss-build.sh` renders it from `$LOCALREPO` (default `$HOME/localrepo`). | The "known problem" in CLAUDE.md is outdated. Fix the sentence in a later docs PR. |
| 3 | Versions of Plasma, KWin, Calamares | Repository database: plasma-desktop, kwin, plasma-workspace 6.8.2-1; KDE Gear 26.08.2. Calamares 3.4.2-2 in `~/localrepo` (AUR build with our layout patch). The ISO itself (`out/heiss-2026.11.04-x86_64.iso`, 2.55 GiB) was built Nov 4 and was not unpacked. | Versions inside the existing ISO are NOT verified. |
| 4 | Content of `packages.x86_64` | 155 lines. About 130 are archiso/releng leftovers (clonezilla, partimage, irssi, lynx, mc, ppp, wvdial, nilfs-utils, jfsutils, bcachefs-tools, many terminfo, `archinstall`...). Our desktop part is ~25 lines: plasma-desktop, sddm, xorg-server, mesa, konsole, dolphin, kate, noto-fonts, xdg-desktop-portal-kde, calamares, os-prober, plymouth, polkit-kde-agent, networkmanager, plasma-nm, firefox, ark, gwenview, okular, spectacle, kscreen, plasma-pa, pipewire-pulse, wireplumber, ttf-jetbrains-mono, python. | `heiss-cleanup.sh` removes a part of the leftovers after install; the rest ships to every installation. Candidate list in RESEARCH.md. |
| 5 | Installed filesystem | `partition.conf`: `defaultFileSystemType: "ext4"`. No snapper, no btrfs subvolume layout. | Snapshots are not available on installs today. Enabling Btrfs is a Tier A change (Calamares) needing an approved item. |
| 6 | Wallpapers: Heiss-Everyday, Heiss-Everyday-Light | Both exist under `usr/share/wallpapers`. `branding/wallpapers` holds four old PNGs (developer, everyday-dark, security, universal). | OK. Sources for Developer/Security/Universal exist but are not packaged. |
| 7 | Docs, CI, DECISIONS.md | None existed: no `docs/`, no `.github/`, no `DECISIONS.md`. | Created in this PR (docs) and Phase 1 (CI). |
| 8 | README profile names | README still says Everyday / Security / Developer / Universal. | Fixed in the profile-rename docs PR (README, CLAUDE.md). |
| 9 | Branch name | Owner asked for `docs/phase-0-aduit` (sic). | Kept as requested. |

## 2. Tier assignment of the main paths

| Tier | Paths |
|---|---|
| A (protected) | `profile/airootfs/usr/share/calamares/branding/heiss/**`; `profile/airootfs/etc/calamares/**` (sequence in `settings.conf`); `usr/local/bin/heiss-boot-branding.sh`, `usr/share/heiss/grub-theme/**`; `usr/share/plymouth/themes/heiss/**`; `etc/sddm.conf.d/**`; `usr/share/plasma/look-and-feel/org.heiss.*.desktop/**`; `usr/local/bin/heiss-setup-dock.sh`; `usr/share/wallpapers/Heiss-*`; `usr/share/color-schemes/Heiss*.colors`; `branding/logo/*`, `branding/fonts/*`, `heiss-*` icons; `usr/share/heiss/os-release`, `usr/share/libalpm/hooks/90-*`, `profile/hooks/*`; `usr/local/bin/heiss-cleanup.sh` (append only); `scripts/heiss-build.sh`, `scripts/heiss-calamares-build.sh` (extend only) |
| B (approval per item) | `etc/xdg/kdeglobals`, `kwinrc`, `kscreenlockerrc`, `ksplashrc`; dock/panel; plasma theme details; window decorations; KRunner/notification/OSD look |
| C (free) | GTK3/GTK4, terminals, Thunar/Dolphin extras, new packages, docs, CI, generators, tests |

Note: the theme-sync files (`heiss-theme-sync.sh`, user units, autostart entry) are not named in Tier A. I treat them as Tier C (extension planned in Phase 4). CONFIRM.

## 3. Inventory of surfaces and apps in the ISO

Toolkit and theming path are from reading configs, not from running the system.

| Surface / app | Toolkit | How it gets the theme | Status | Tier | Proposed fix | Risk |
|---|---|---|---|---|---|---|
| Boot menu (syslinux/GRUB) | n/a | custom GRUB theme, generator script | done | A | none | low |
| Plymouth | script | theme "heiss" | done | A | none | low |
| SDDM login | QML | Breeze theme + user conf | done | A | none | low |
| Plasma shell, panel/dock | QML | LnF `defaults`, layout JS | done, polish pending | B | propose indicator tuning with screenshots | medium |
| Kickoff launcher icon | QML | theme-sync script | done | C | fold into extended sync | low |
| Konsole | Qt6/KDE | color scheme + font from kdeglobals; default profile is stock | partial | C | Heiss profile + colorscheme from tokens | low |
| Dolphin | Qt6/KDE | color scheme, `breeze-dark` icons | pins and icon names checked statically (see section 4); look NOT verified | C | needs a screenshot from the new ISO | low |
| Kate, Ark, Gwenview, Okular, Spectacle | Qt6/KDE | color scheme | expected fine (to verify) | C | screenshot audit | low |
| Firefox | GTK | portal/GTK settings; no GTK theme configured by us | unknown | C | document limits; no userChrome | medium |
| Calamares installer | Qt6 | stylesheet + QML | done | A | none | low |
| Running installer in dock | n/a | StartupWMClass / desktop file | desktop files consistent (class `calamares`, shipped icon, one visible entry; guarded by `check-launchers.py`); look NOT verified | C | needs a screenshot of the running installer in the dock | low |
| System Settings (KCMs) | Qt6 | color scheme | expected fine | C | none | low |
| GTK3/GTK4 apps | GTK | none configured (no `settings.ini`, no `gtk.css`) | not themed by us | C | generate from tokens, portal color-scheme | medium |
| Tray icons | Qt | Breeze symbolic | weight/size may differ (to verify) | B | propose after screenshot | low |
| Notifications/OSD/KRunner | QML | Plasma style | stock look | B | propose | low |

## 4. Known visual issues from the plan: verification status

All four are NOT verified (no screenshot of the running system). Needed captures are in section 6.

1. Installer entry in the dock flat block / generic icon. Static findings (2026-11-10): the window class of Calamares 3.4.2 is `calamares` (strings of the binary); `heiss-installer.desktop` and the hidden override `calamares.desktop` both set `StartupWMClass=calamares` and `Icon=heiss-installer`, which exists only as 64 and 128 px PNG in hicolor (no SVG: icons under `hicolor/` are Tier A, so no icon was added). A flat block could still come from how that PNG is scaled; not reproducible without a screenshot.
2. Pinned file manager icon generic. Static findings: the pin `org.kde.dolphin.desktop` exists in the `dolphin` package (26.08.3), its `Icon=org.kde.dolphin` is shipped by the same package in `hicolor/scalable`; `org.kde.konsole.desktop` uses `utilities-terminal` and `systemsettings.desktop` exists in `systemsettings`; both icon themes (`breeze`, `breeze-dark`) contain `utilities-terminal` and `preferences-system`. The generic icons in the owner's early screenshots (`~/share/heiss-dock-*.png`) come from the older dock script and from the comma-joined pin string that the layout script no longer produces. Whether the current layout still shows a generic icon is NOT verified.
3. Tray icon weight/size inconsistency.
4. GTK client-side decoration button style versus KWin.

## 5. Observations from reading the repo (to fix later, not now)

- `packages.x86_64` ships tools that do not belong on a desktop install (clonezilla, partimage, mc, lynx, irssi, ppp stack, `archinstall`, `nmap` and `tcpdump` on every system). Cleanup removes some. Note that the plan puts nmap/tcpdump into Cyber, so Base should not contain them. This is an ISO-size and attack-surface item for Phase 2 and 10.
- No firewall package is in the list (`firewalld`, `ufw` absent): the "firewall on" requirement from the plan is not met today.
- No `flatpak`, `fwupd`, `power-profiles-daemon`, `bluez`/`bluedevil`, `cups`, `zram-generator` in the ISO. Bluetooth and printing do not work out of the box (to verify).
- `sshd.service` is enabled in the live image; cleanup disables it after install. Good.
- `heiss-cleanup.sh` lines `rm -rf /etc/pacman.d/gnupg` plus `pacman-key --init --populate archlinux` run at install time: a future `heiss-keyring` step must be appended after it.
- Live-only systemd symlinks (cloud-init, vmware, hyperv, vboxservice) live in `airootfs/etc/systemd/system`; cleanup deletes dangling ones only.
- Open issue from CLAUDE.md: `cloud-init` leftovers on the installed system (cleanup already lists `cloud-init` in `LIVE_PKGS`; to verify whether it still leaks).

## 6. Screenshots and checks I need from the owner (Dark and Light unless noted)

1. Desktop with the dock, full screen.
2. Dock with the running installer (live session, Dark).
3. Dock tooltip on Dolphin and on Konsole.
4. System tray, zoomed.
5. Dolphin, Konsole, Kate, Okular, System Settings, each open on a folder/document.
6. Firefox start page and a GTK file dialog (open any file from Firefox).
7. Output of `systemctl --user status heiss-theme-sync.path` and `plasmashell --version`, `kwin_wayland --version`, `calamares --version` in the live session.
8. After an installation: `findmnt /`, `systemctl --failed`, `pacman -Q | wc -l`.
