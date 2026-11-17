# Package review of the installed system (round 25, PR E)

Data: the package database of the image built on 2026-11-17 (`heiss-2026.11.17`), read without root from the squashfs (`var/lib/pacman/local`). The image holds 932 packages, 5016 MiB installed. After the first-boot cleanup (`heiss-cleanup.sh` removes the live-only packages and the orphaned dependencies) an installed system has about 877 packages and 4875 MiB (a simulation of that removal; the owner's real count was about 940). Nothing here was measured on a running system.

How to read it: "explicit" means named in `profile/packages.x86_64` or a Heiss manifest; everything else (about 800 packages) is pulled in as a dependency and is only worth a decision when it is large. A package that a Heiss package or KDE depends on is never removed.

## Decisions for the packages the owner named

| Package | Size | Pulled in by | Decision | Reason |
|---|---|---|---|---|
| reflector | 0.2 MiB | `heiss-profile-essentials` | keep | Listed in Essentials as a user tool. No `reflector.service` or timer is enabled anywhere in the image (checked in the image and by `tests/test_package_review.py`), so it never runs on its own. |
| refind | 1.9 MiB | nothing | **left out of the ISO** | The bootloader is GRUB (`efiBootLoader: grub`). Removed from `packages.x86_64`; `heiss-cleanup.sh` removes it from older images. |
| os-prober | 0.1 MiB | `heiss-profile-essentials`, optional for grub | keep | Dual boot: `heiss-boot-branding.sh` turns it on only when it finds another OS. It is not the source of the extra "(EFI BootNext)" lines (those came from `31_efi_bootnext`, fixed in PR C). |
| arch-install-scripts | 0.0 MiB | `archinstall` only | **removed from the installed system** | `heiss-cleanup.sh` (LIVE_PKGS). It stays in the ISO. |
| archlinux-appstream-data | 21.0 MiB | `discover` (hard dependency) | keep | Cannot go without removing Discover, which is in Base. Whatever "Arch" Discover shows comes from this data and the repository names; it cannot be changed here. Owner question 1. |
| kuserfeedback | 2.0 MiB | `discover`, `dolphin`, `kate`, `plasma-workspace` | keep (not removable) | KDE needs the library. Nothing is switched on by the image: the Calamares tracking module is not in the install sequence and its `user` tracking is `enabled: false`; the library only reports when the user turns it on in System Settings. That the setting is really off on a running system is a VM check. |
| qt6-webengine | 283.8 MiB | `qt6-webview` (from `discover`) and `signon-ui` (from `kaccounts-integration` <- `purpose` <- gwenview, okular, spectacle) | keep (not removable) | The only way to drop it is to drop Discover, Gwenview, Okular and Spectacle, which are Base apps. Benefit: online accounts and Discover's web views. Owner question 2. |
| ripgrep-all | 13.5 MiB | `kio-extras` (Dolphin, plasma-workspace) | keep (not removable) | Dolphin's file search needs it through kio-extras. |
| haruna | 6.8 MiB | `heiss-profile-base` | keep | Base profile, accepted in Phase 0. |
| keepassxc | 33.0 MiB | `heiss-profile-base`, `qtkeychain-qt6` | keep | Base profile, accepted in Phase 0; also required by `qtkeychain-qt6`. |
| partitionmanager | 6.9 MiB | `heiss-profile-base` | keep | Base profile (disk tools next to `plasma-disks`). |
| foot-, ghostty-, kitty-, kmscon-, rxvt-unicode-terminfo | 0.0 MiB each | nothing | keep | Fine, as the owner said. |
| lsb-release | 0.0 MiB | `open-vm-tools` only | not installed on non-VMware | The cleanup removes `open-vm-tools` off VMware, and `lsb-release` goes with it, so `/etc/lsb-release` does not exist there. That is fine: no Heiss tool calls `lsb_release` (checked by `tests/test_package_review.py`). On VMware the hook from PR #115 keeps the file branded. |

## Largest packages of an installed system (estimate)

firefox 307 MiB (explicit), qt6-webengine 284, llvm-libs 165 (mesa), linux 151, linux-firmware-intel 142, qt6-declarative 135, noto-fonts 107 (explicit), linux-firmware-nvidia 104, linux-firmware-marvell 80 (explicit), python 74, perl 72, qt6-base 68, plasma-workspace 58, breeze-icons 57, sof-firmware 55 (explicit), mesa 54, linux-firmware-atheros 53, gtk3 53, pyside6 52, glibc 51, ffmpeg 48, vulkan-intel 44. Almost all are dependencies of Essentials or Base, or firmware pulled in by `linux-firmware`.

## Every explicit package of the ISO list

| Package | Size | Decision | Reason |
|---|---|---|---|
| refind | 1.9 MiB | left out of the ISO | GRUB is the bootloader (Calamares `efiBootLoader: grub`); removed from the ISO list, the cleanup removes it from older images |
| alsa-utils | 2.5 MiB | keep | mixer tools; Essentials lists it |
| amd-ucode | 0.6 MiB | keep | CPU microcode, Essentials |
| arch-install-scripts | 0.0 MiB | remove from the installed system | only archinstall needs it; the cleanup now removes it (LIVE_PKGS) |
| archinstall | 7.9 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| base | 0.0 MiB | keep | core |
| bolt | 0.4 MiB | keep | Thunderbolt authorisation (KDE Thunderbolt page); inert |
| brltty | 9.5 MiB | remove from the installed system | live accessibility; removed by the cleanup (already) |
| btrfs-progs | 6.8 MiB | keep | Btrfs and snapshots are planned |
| cryptsetup | 3.6 MiB | keep | encrypted disks |
| darkhttpd | 0.1 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| dhcpcd | 0.5 MiB | keep | 0.5 MiB, optional for NetworkManager, service not enabled; harmless |
| diffutils | 1.5 MiB | keep | core tool |
| dmidecode | 0.2 MiB | keep | kinfocenter requires it |
| dmraid | 0.3 MiB | keep | 0.3 MiB, old RAID metadata tool; harmless, no dependants |
| dosfstools | 0.4 MiB | keep | FAT tools, needed for the EFI partition |
| e2fsprogs | 5.3 MiB | keep | ext4 tools |
| efibootmgr | 0.1 MiB | keep | Essentials; grub-install needs it |
| espeakup | 0.0 MiB | remove from the installed system | live accessibility; removed by the cleanup (already) |
| ethtool | 1.0 MiB | keep | network diagnostics |
| exfatprogs | 0.3 MiB | keep | exFAT USB sticks |
| f2fs-tools | 0.7 MiB | keep | F2FS tools, small |
| fatresize | 0.0 MiB | keep | kpmcore (Partition Manager) optional |
| foot-terminfo | 0.0 MiB | keep | 0.0 MiB, SSH sessions from that terminal |
| ghostty-terminfo | 0.0 MiB | keep | 0.0 MiB, same |
| gpart | 0.1 MiB | keep | 0.1 MiB, partition table recovery |
| gpm | 0.4 MiB | remove from the installed system | live console mouse; removed by the cleanup (already) |
| gptfdisk | 0.7 MiB | keep | gdisk and sgdisk |
| grml-zsh-config | 0.1 MiB | keep | 0.1 MiB, goes with zsh |
| grub | 43.2 MiB | keep | bootloader; Essentials |
| hdparm | 0.2 MiB | keep | 0.2 MiB disk tool |
| hyperv | 0.2 MiB | keep | Hyper-V guest tools; the cleanup keeps them only on Hyper-V |
| intel-ucode | 34.3 MiB | keep | CPU microcode, Essentials |
| iw | 0.3 MiB | keep | Wi-Fi diagnostics |
| iwd | 2.2 MiB | keep | 2.2 MiB, optional NetworkManager backend; not enabled |
| kitty-terminfo | 0.0 MiB | keep | 0.0 MiB, same (kitty is an add-on) |
| kmscon-terminfo | 0.0 MiB | keep | 0.0 MiB, same |
| less | 0.3 MiB | keep | pager, man needs it |
| libfido2 | 0.5 MiB | keep | security keys (systemd, openssh optional) |
| libusb-compat | 0.0 MiB | keep | small compatibility library |
| linux | 151.4 MiB | keep | kernel |
| linux-firmware | 0.0 MiB | keep | firmware metapackage; pulls the Intel, NVIDIA, AMD, Atheros parts, not removable |
| linux-firmware-marvell | 79.8 MiB | keep | 80 MiB, Marvell Wi-Fi and storage firmware (some Surface and embedded boards); owner question 3 |
| livecd-sounds | 0.3 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| lvm2 | 5.3 MiB | keep | LVM volumes; Calamares can install onto LVM |
| man-db | 2.4 MiB | keep | man pages |
| man-pages | 5.7 MiB | keep | man pages |
| mdadm | 1.0 MiB | keep | software RAID; libblockdev needs it |
| memtest86+ | 0.2 MiB | remove from the installed system | live menu entry; removed by the cleanup (already) |
| memtest86+-efi | 0.4 MiB | remove from the installed system | live menu entry; removed by the cleanup (already) |
| mkinitcpio | 0.2 MiB | keep | initramfs generator |
| mkinitcpio-archiso | 0.0 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| mkinitcpio-nfs-utils | 0.1 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| modemmanager | 4.7 MiB | keep | mobile broadband; NetworkManager uses it |
| mtools | 0.4 MiB | keep | FAT image tools, small |
| nano | 2.8 MiB | keep | editor, Essentials |
| nbd | 0.2 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| nfs-utils | 1.4 MiB | remove from the installed system | live only; removed by the cleanup (already) |
| ntfsprogs | 0.8 MiB | keep | NTFS tools, dual boot |
| nvme-cli | 6.6 MiB | keep | 6.6 MiB, NVMe health; no dependants, useful for support |
| open-vm-tools | 4.6 MiB | keep | VMware tools; the cleanup keeps them only on VMware |
| openssh | 6.8 MiB | keep | SSH client; sshd is disabled by the cleanup and never enabled |
| parted | 2.7 MiB | keep | partition tool |
| pcsclite | 0.3 MiB | keep | smart cards; keepassxc and wpa_supplicant need it |
| ppp | 0.9 MiB | keep | modemmanager requires it |
| pv | 0.4 MiB | keep | tiny pipe viewer |
| qemu-guest-agent | 1.1 MiB | keep | the cleanup keeps it only on QEMU/KVM |
| reflector | 0.2 MiB | keep | 0.2 MiB, listed in Essentials; no unit or timer is enabled (a test checks this), so it never runs on its own |
| rsync | 0.9 MiB | keep | core tool |
| rxvt-unicode-terminfo | 0.0 MiB | keep | 0.0 MiB, same |
| screen | 0.8 MiB | keep | 0.8 MiB, terminal multiplexer for support sessions; no dependants (owner question 4) |
| smartmontools | 2.1 MiB | keep | plasma-disks and kpmcore need it |
| sof-firmware | 55.1 MiB | keep | 55 MiB, audio on many recent laptops |
| squashfs-tools | 0.9 MiB | keep | small |
| sudo | 7.9 MiB | keep | Essentials; root is locked |
| syslinux | 4.3 MiB | remove from the installed system | live BIOS menu only; removed by the cleanup (already) |
| systemd-resolvconf | 0.0 MiB | keep | resolv.conf compatibility for resolved |
| terminus-font | 3.0 MiB | keep | 3 MiB console font, readable text consoles on HiDPI |
| tmux | 1.4 MiB | keep | 1.4 MiB, terminal multiplexer (owner question 4) |
| tpm2-tss | 3.7 MiB | keep | fwupd, gnupg and libsecret require it |
| udftools | 0.4 MiB | keep | kpmcore and udisks optional (UDF discs) |
| usb_modeswitch | 0.2 MiB | keep | switches USB modems for ModemManager |
| usbutils | 0.4 MiB | keep | lsusb |
| vim | 5.4 MiB | keep | 5.4 MiB editor (owner question 4); nano is the default |
| virtualbox-guest-utils | - | keep | the cleanup keeps it only on VirtualBox |
| wireless-regdb | 0.0 MiB | keep | Wi-Fi regulatory database, Essentials |
| wpa_supplicant | 8.3 MiB | keep | NetworkManager's Wi-Fi backend |
| xdg-utils | 0.3 MiB | keep | qt6-base requires it |
| xfsprogs | 4.6 MiB | keep | XFS tools |
| zsh | 6.9 MiB | keep | 6.9 MiB, shell for users who choose it (owner question 4) |
| plasma-desktop | 41.9 MiB | keep | Essentials |
| sddm | 5.3 MiB | keep | Essentials |
| xorg-server | 3.9 MiB | keep | X11 server for SDDM; Essentials also lists xorg-xwayland |
| mesa | 53.9 MiB | keep | Essentials |
| konsole | 10.4 MiB | keep | Essentials |
| dolphin | 16.3 MiB | keep | Essentials |
| kate | 36.1 MiB | keep | Base |
| noto-fonts | 106.8 MiB | keep | 107 MiB, Essentials (many scripts) |
| xdg-desktop-portal-kde | 3.1 MiB | keep | Essentials |
| calamares | 9.6 MiB | remove from the installed system | installer; removed by the cleanup (already) |
| os-prober | 0.1 MiB | keep | Essentials requires it: finds other operating systems for the GRUB menu (on only when another OS is found) |
| plymouth | 2.2 MiB | keep | Essentials, boot splash |
| polkit-kde-agent | 0.2 MiB | keep | Essentials |
| networkmanager | 18.1 MiB | keep | Essentials |
| plasma-nm | 14.1 MiB | keep | Essentials |
| firefox | 307.2 MiB | keep | 307 MiB, Essentials browser |
| ark | 5.2 MiB | keep | Base |
| gwenview | 11.5 MiB | keep | Base |
| okular | 19.6 MiB | keep | Base |
| spectacle | 6.7 MiB | keep | Base |
| kscreen | 3.7 MiB | keep | Essentials |
| plasma-pa | 2.5 MiB | keep | Essentials |
| pipewire-pulse | 0.5 MiB | keep | Essentials |
| wireplumber | 1.3 MiB | keep | Essentials |
| ttf-jetbrains-mono | 7.4 MiB | keep | design font |
| inter-font | 14.3 MiB | keep | design font |
| python | 74.0 MiB | keep | Heiss tools |
| heiss-core | 0.1 MiB | keep | Heiss |
| heiss-helper | 0.0 MiB | keep | Heiss |
| heiss-profile-base | 0.0 MiB | keep | Heiss |
| heiss-theme | 0.0 MiB | keep | Heiss |
| heiss-keyring | 0.0 MiB | keep | Heiss |
| heiss-welcome | 0.1 MiB | keep | Heiss |
| heiss-control | 0.1 MiB | keep | Heiss |
| heiss-safe-graphics | 0.0 MiB | keep | Heiss |

## Owner questions (one list, with a recommendation)

1. **archlinux-appstream-data (21 MiB, Arch names in Discover).** Options: (a) keep Discover and this data; (b) drop Discover from Base and with it the data and `qt6-webview`. Recommendation: (a) for now, Discover is the graphical update and Flatpak front end.
2. **qt6-webengine (284 MiB).** Options: (a) accept it; (b) drop Gwenview, Okular, Spectacle and Discover from Base. Recommendation: (a): removing four core apps to save 284 MiB is not a good trade.
3. **linux-firmware-marvell (80 MiB, explicit).** `linux-firmware` does not pull it in; the releng list added it. Options: (a) keep (Marvell Wi-Fi on some Surface and embedded boards); (b) remove from `packages.x86_64` (saves 80 MiB on every system, those devices lose Wi-Fi until the package is installed). Recommendation: (a) until there is hardware evidence.
4. **Terminal tools without dependants (screen, tmux, vim, zsh with grml-zsh-config, nvme-cli, openssh: about 23 MiB).** Options: (a) keep for support and the Cyber and Developer profiles; (b) move them into the Cyber and Developer manifests only. Recommendation: (a) now, (b) when the profile content is reviewed.

None of the four is changed in this PR; the answers decide a later PR.

