# Automatic screenshots (proposal, not built)

Goal: capture the booted ISO without a manual step, so visual claims can be checked.

## Option 1: QEMU inside the build VM, `screendump` through the QEMU monitor

- Boot the ISO with `qemu-system-x86_64 -cdrom ... -m 4096 -vga std -display none -monitor unix:...` and send `screendump file.ppm` (or `-qmp` with `screendump`), convert with `magick`/`pnmtopng`.
- Keystrokes via `sendkey` allow navigating the live session.

Verified facts about THIS VM (2026-11-09): `systemd-detect-virt` = `oracle` (VirtualBox), `/dev/kvm` absent, no `vmx` flag in `/proc/cpuinfo`, `qemu-system-x86_64` not installed.

Consequence, stated honestly: no hardware acceleration, so QEMU would run in TCG (pure emulation). A KDE Plasma session in TCG will be very slow (boot likely many minutes, animations not representative). Static screenshots may still work; performance and motion cannot be judged. NOT VERIFIED: I did not try it. Needs `pacman -S qemu-base` (sudo, password needed from the owner).

## Option 2: VirtualBox on the host

`VBoxManage controlvm <vm> screenshotpng file.png` from the owner's host, scripted. Works with real acceleration of the host. Needs the owner to run the script (not possible from the build VM).

## Option 3: in-guest capture

`spectacle -b -n -o file.png` or `grim` inside the live session via a startup script that writes to the VirtualBox shared folder. Shared folder writes used `cp`-truncation workarounds before (see `heiss-build.sh`: `dd` + sha256); reuse that method.

## Recommendation

Option 3 for static captures (smallest change, reflects the real VirtualBox renderer), Option 2 for sequences. QEMU/TCG only if the owner wants fully offline CI later. Decision needed from the owner.
