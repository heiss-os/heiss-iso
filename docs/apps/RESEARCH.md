# Research: profiles, apps, drivers, motion, plugins (Phase 0)

Data source: `pacman -Si` on the build VM, 2026-11-09 (repositories core + extra). "inst" = installed size. Versions move; re-check before shipping. Anything marked NOT VERIFIED could not be tested here. All numbers are for the package alone, without dependencies unless stated.

## 1. Essentials (proposal, CONFIRM)

Built from the real `packages.x86_64`, keeping only what a usable, secure, themed system needs.

| Group | Packages | Note |
|---|---|---|
| Base system | base, linux, linux-firmware (split: intel 138 MiB, amdgpu 28, nvidia 104, realtek 7.7, broadcom 13 ...), sof-firmware 55 MiB, intel-ucode 31 MiB, amd-ucode 0.6 MiB, grub, os-prober, efibootmgr, sudo, nano | `linux-firmware` is now a meta-package (0 KiB) depending on 12 split packages; installing only needed ones saves space |
| Graphics | mesa 54 MiB, xorg-server (XWayland needs), vulkan-radeon 18, vulkan-intel 44 | NVIDIA only by hardware profile |
| Network | networkmanager, plasma-nm 14 MiB, wireless-regdb, iwd or wpa_supplicant (NM backend), openssh disabled | |
| Audio | pipewire-pulse, wireplumber, plasma-pa 2.4 MiB, alsa-utils | |
| Bluetooth | bluez 1.7 MiB, bluez-utils 3.7, bluedevil 2.7 | missing in ISO today |
| Desktop | plasma-desktop 42, plasma-workspace 58, kwin 32, sddm, kscreen, polkit-kde-agent, xdg-desktop-portal-kde, kde-gtk-config 0.3, breeze-gtk 1.2, xdg-desktop-portal-gtk 0.4 | Plasma 6.8.2 |
| Core apps | konsole 10, dolphin 16, firefox 302 MiB | one terminal, one file manager, one browser |
| Fonts | ttf-jetbrains-mono, Inter (from `branding/fonts`), noto-fonts | Inter is not a package line today |
| Tooling | pacman, flatpak 8 MiB (optional), reflector, zram-generator 0.7, fwupd 19 MiB | |
| Security | firewalld 2.1 MiB + plasma-firewall 1.4 MiB (default to confirm) | missing today |
| Heiss | heiss-branding, heiss-keyring, heiss-core, heiss-helper, heiss-welcome, heiss-control, heiss-theme | not yet written |
| Plymouth | plymouth | |

Not included in Essentials: nmap, tcpdump, clonezilla, partimage, mc, lynx, irssi, ppp stack, archinstall, bcachefs/jfs/nilfs tools, rescue tools (move to a "Rescue" add-on or drop).

## 2. Base set (candidate tables, one default per job)

Criteria in order: official repo, maintained, Qt/KDE-native, small, themeable, no duplicates.

| Job | Default (recommended) | Alternatives checked | Why |
|---|---|---|---|
| Terminal | konsole 10 MiB | kitty 0.49.2, 77 MiB (add-on) | follows color scheme for free |
| File manager | dolphin 16 MiB | thunar 4.20.10, 9.8 MiB (add-on) | same |
| Text editor | kate 36 MiB | neovim 30 MiB (Developer) | Qt native |
| Image viewer | gwenview 11.5 MiB | | already shipped |
| PDF/documents | okular 19.5 MiB | | already shipped |
| Archives | ark 5.3 MiB | | already shipped |
| Screenshot/recording | spectacle 6.7 MiB | obs-studio 27 MiB (Creative) | |
| Media player | haruna 7 MiB (GPL-3.0, Qt/Kirigami, mpv based) | vlc 42 MiB, elisa 7 MiB (music), mpv 6.5 MiB | small, matches Qt; VLC remains an option. NOT VERIFIED: theme fit and codec handling in the VM |
| Calculator | kcalc 3 MiB | | |
| System monitor | plasma-systemmonitor 3 MiB | | |
| Password manager | keepassxc 33 MiB (Qt, local files, no cloud) | kwalletmanager 2.8 MiB (KDE wallet only) | independent of the account |
| Clipboard | Plasma built-in clipboard applet; the separate `klipper` package (0.13.0-4, 213 MiB installed) was NOT found among the dependencies of plasma-desktop/plasma-workspace, so whether the applet needs it is NOT VERIFIED | | do not add a separate app |
| Mail/calendar | thunderbird 303 MiB (self-contained) | kmail 23 MiB + akonadi stack (large dependency tree, NOT sized here) | recommendation: not in Base; offer as add-on. CONFIRM |
| Office | libreoffice-fresh 423 MiB (26.8.1) | libreoffice-still 422 MiB (26.2.6) | `still` for stability; add-on in Base? CONFIRM, it is the biggest item |
| Backup | kup 2.7 MiB + restic 41 MiB (optional) | timeshift 4 MiB (needs ext4/Btrfs setup) | defer to Phase 6 backups page |
| Disks | plasma-disks 0.6, partitionmanager 7 MiB, filelight 1.5 MiB | gparted 7.6 | partitionmanager is KDE native |
| Software installer | discover 7.7 MiB + flatpak | | Discover may list drivers (lead from plan, NOT VERIFIED) |
| Thumbnails | kio-extras 7.5, ffmpegthumbs 0.1, kdegraphics-thumbnailers 0.15 MiB | | small, add to Base |
| Phone link | kdeconnect 7 MiB | | optional, no default network service |

## 3. Cyber toolset (official repos only)

Verified present (version, inst size): nmap 7.993 26.5 MiB; tcpdump 4.99.7 1.1 MiB; wireshark-qt 4.7.4 16.9 MiB; aircrack-ng 1.7 1.7 MiB; hashcat 78.7 MiB; john 69.7 MiB; radare2 6.2.2 36 MiB; gdb 18.1 32 MiB; binwalk 3.1.0 3.8 MiB; volatility3 2.28.2 16.9 MiB; sleuthkit 4.15.0 14.6 MiB; podman 6.1.4 83 MiB; distrobox 0.6 MiB; ghidra 12.1.2 742 MiB (extended tier only).
Not found in official repos: autopsy, steam (not in extra: it needs multilib, NOT checked), broadcom-wl (module is DKMS/out-of-tree, documented only), colord-kde. Verify the rest (web testing, OSINT, reporting) in Phase 2 with a script.
"Important" tier proposal: nmap, tcpdump, wireshark-qt, aircrack-ng, john, radare2, gdb, binwalk, sleuthkit, podman, distrobox (~230 MiB). "Extended": hashcat, volatility3, ghidra, others after a check.
Rules from the plan apply: no services enabled, no open ports, capture only via group or file capabilities (wireshark-qt/dumpcap needs a `wireshark` group decision: NOT VERIFIED), consent notice shown.

## 4. Developer toolset

Verified: git 2.56.0 33 MiB; rustup 11 MiB (toolchains downloaded from the network: not official-repo offline); go 227 MiB; nodejs 26.13.0 64 MiB; jdk-openjdk 27 603 MiB (extended); neovim 31 MiB; code 1.138.0 768 MiB (repository `code` is the Microsoft build with telemetry settings: conflicts with the no-telemetry principle; vscodium NOT in repos) -> recommendation: do not ship `code`, ship kate + neovim, document the choice; docker 119 MiB and podman 83 MiB (default podman); modern CLI: ripgrep 4.4, fd 3.5, bat 5.1, eza 1.9, fzf 5.6, zoxide 1.1 MiB.

## 5. Add-ons

Gaming: gamemode 0.3 MiB, mangohud 10 MiB, wine 592 MiB; steam not in `extra` (multilib not checked). Creative: krita 198, kdenlive 94, inkscape 190, gimp 151, audacity 43, obs-studio 27 MiB. Privacy: networkmanager-openvpn 1.5, wireguard-tools 0.3 MiB; Tor/anonymity tools not yet checked.

## 6. Delivery analysis (5.5) and recommendation

Today unpackfs copies the whole live squashfs, so the install equals the ISO content, including releng leftovers (see AUDIT.md section 5). Existing ISO: 2.55 GiB.

| Option | ISO size effect | Offline install | Network drop | Complexity |
|---|---|---|---|---|
| (a) Base in ISO, Custom removes extras via state file | largest | full Base works offline | removal needs no network | low; Custom removal is a pacman -Rns per state file; risk: removing shared dependencies |
| (b) Essentials only in ISO, rest over network | smallest | system boots, apps missing | install of profile fails midway: resumable queue needed | medium; needs Phase 1 hosted repo first |
| (c) Essentials + offline repo of Base on the ISO | ISO about as big as (a) | full Base offline, Custom installs from the on-ISO repo | no network needed for Base | highest build complexity |
| (d) Calamares netinstall | small | needs network during install | install aborts, user must retry | touches Calamares sequence (Tier A) |

Recommendation: (a) for the first iteration, because it needs no hosted repo, no Calamares sequence change, and works offline; revisit (c) when the repository exists. CONFIRM.

## 7. Drivers and hardware plan

| Item | Verified | Status / limit |
|---|---|---|
| CPU microcode | intel-ucode 20260925, amd-ucode 20260916 present | Safe by default; cleanup could keep only the matching one |
| Firmware | linux-firmware is a meta-package of 12 splits (core repo) | Select splits by detected hardware to save size |
| Intel/AMD GPU | mesa 54 MiB, vulkan-intel 44, vulkan-radeon 18 | OK in VM only partially tested (VirtualBox uses VMSVGA) |
| NVIDIA | nvidia-open 615.78.08 (kernel modules, 9.7 MiB) requires nvidia-utils 948 MiB installed size | Package metadata does NOT list supported generations. The "Turing and newer" claim from the plan is NOT VERIFIED from the package; check NVIDIA release notes before coding. Older GPUs: open nouveau stack + message, never AUR |
| Hybrid graphics | nvidia-prime 1.0-6 | Boot-safety NOT VERIFIED (no hardware) |
| Broadcom Wi-Fi | linux-firmware-broadcom present; `broadcom-wl` not in repos | Out-of-tree drivers documented only |
| Printing/scanning | cups 12.8, cups-filters 1.2, sane 18.7, sane-airscan 0.5, system-config-printer 8.4, print-manager 3 MiB, hplip 40 MiB | CUPS driverless first; hplip add-on |
| Fingerprint | fprintd 0.9 MiB | NOT VERIFIED |
| Power | power-profiles-daemon 0.14 MiB (laptops only), iio-sensor-proxy | |
| Firmware updates | fwupd 2.1.9, 19 MiB | Needs network and LVFS; consent notice |
| Fallback kernel | linux-lts 6.18.60, 156 MiB (plus modules and firmware shared) | Measured: +156 MiB on disk. Recommendation: not by default; add-on |
| chwd / mhwd | NOT in official repos | Write our own detection; study chwd license first |

Not achievable here without real hardware or AUR: NVIDIA legacy, DKMS Wi-Fi drivers, Secure Boot signing, fingerprint, touchscreen, hybrid-GPU suspend behavior. Safe-graphics fallback entry (nomodeset or `modeset=0` style) is feasible as a GRUB entry; GRUB theme is Tier A, so the entry must be added outside the theme files. NOT VERIFIED.

## 8. Settings gap analysis, motion, plugins

Plasma 6.8.2 ships KCMs for display (kscreen), audio (plasma-pa), Bluetooth (bluedevil), printers (print-manager), network (plasma-nm), power (powerdevil 6.8.2-1, 6.7 MiB, a dependency of plasma-desktop), firewall (plasma-firewall), system info (kinfocenter), disks (plasma-disks), Thunderbolt (plasma-thunderbolt). Gaps: unified Security Center, profile switching, driver doctor, microphone noise suppression (easyeffects 8.3.2, 16 MiB, Qt/Kirigami; theme fit NOT VERIFIED), `colord-kde` not in repos (ICC profile management: check later). Rule: theme the built-ins, do not rewrite them.

Motion proposal: fast 120 ms, normal 200 ms, slow 300 ms, one easing curve (cubic-bezier 0.2, 0, 0, 1), wired to Plasma's animation speed factor (kdeglobals `AnimationDurationFactor`). Auto Reduced on `systemd-detect-virt` != none and on software renderers. All NOT VERIFIED visually.

Plugins (lead verification, no source review done yet): krohnkite, kwin-scripts, calamares-extensions are not in repos. Panel Colorizer, PlasmaZones, Better Blur DX, KDE Rounded Corners, Klassy, Darkly are third-party/AUR and require per-item approval plus a supply-chain review under `docs/apps/REVIEWS/` before any use. Recommendation: ship none in the first iteration; use Plasma built-in tiling, rounded corners and light/dark switching (to verify in a VM).

## 9. Questions with recommended defaults

See the Phase 0 report message: the same numbered list is kept there so you can answer with numbers.

1. Profile names/ID mapping: Base, Cyber, Developer, Custom as in 5.1. Default: yes.
2. Essentials list (section 1): default: as proposed.
3. Delivery option (section 6): default: (a).
4. Konsole and Dolphin stay defaults, kitty and Thunar are add-ons: default: yes.
5. Qt widget style: keep Breeze.
6. GTK accent: fixed sand accent.
7. Firefox userChrome: no.
8. Dock presets: not now.
9. Plugins: official repos plus reviewed vendored items only; none in the first iteration; Plasma built-in tiling.
10. Blur/transparency: opt-in only.
11. Older NVIDIA: open stack with a message.
12. LTS fallback kernel: add-on (+156 MiB), not default.
13. Calamares sequence change for driver detection: wizard first.
14. Engine stack: Python 3 + PySide6 + Kirigami (`pyside6` 6.12.0-3, `kirigami` 6.31.0-1).
15. Firewall: firewalld + plasma-firewall.
16. Snapshots: snapper + snap-pac + grub-btrfs only once root is Btrfs; Btrfs enablement is a separate Tier A item (needs your approval by name).
17. Do not ship `code` (telemetry); yes/no.
18. Media player haruna, password manager keepassxc, mail not in Base, office as add-on: yes/no.
19. Is the theme-sync script (launcher icon sync) Tier C for extension: yes/no.
