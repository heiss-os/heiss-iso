# Safe fallback and snapshot before driver changes (Phase 7 design)

Status: the owner answered 1 A, 2 A, 3 A, 4 A (2026-11-15). Built: order step 1 (package `heiss-safe-graphics`, `packages/heiss-safe-graphics/41_heiss_safe`) and step 2 (NVIDIA warning text). Step 3a built (2026-11-16): the NVIDIA proposals are offered only when the safe-graphics entry is installed (`requires` in the hardware profile, see DECISIONS). Step 3b built (2026-11-16): second confirmation for drivers that are not safe by default. Step 4a built (2026-11-16): `linux-lts` and `nvidia-open-lts` are installed together with `gpu-nvidia-open`. Step 4b built (2026-11-16): `heiss hw remove ID` and the helper method `RemoveHardware`. Step 4c built (2026-11-16): the Control Center "Remove this driver" button. All four steps of the agreed order are built; none ran on real hardware. The text below is the original proposal. No Tier A file is touched by this document. Items marked NOT VERIFIED
could not be checked on the build host (no UEFI, no real GPU, the pacman file database is not synced there).

## Problem

A bad GPU driver can leave the user with a black screen and no way back. Today:

- The NVIDIA profile (`hardware/gpu-nvidia-open.toml`) tells the user: "If the screen stays black, choose the safe
  graphics boot entry". That entry did not exist when this was written; it is built by the package `heiss-safe-graphics` (see Status). The warning promises something we do not ship. (Text since changed: round 22 moved the recovery step to the first sentence and added a short `recovery` text for the wizard.)
- Update 2026-11-19 (H2c): the helper has no snapshot step any more (snapshots were removed from the product, DECISIONS 2026-11-18 and 2026-11-19). There is **no snapshot** and the only rollback is removing the packages the state file recorded.
- No second kernel is installed (`profile/packages.x86_64` has `linux` only). (Changed in step 4a: `linux-lts` comes with the NVIDIA driver, still not in the ISO.)

## What would be built

1. **Safe-graphics boot entry** (GRUB, installed system only). An extra menu entry that boots the same kernel with
   `nomodeset` and the NVIDIA modules kept out (`modprobe.blacklist=nvidia,nvidia_modeset,nvidia_uvm,nvidia_drm`),
   so the machine reaches a text or generic-graphics desktop and the user can remove the driver.
   - Mechanism: a script in `/etc/grub.d/` (for example `41_heiss_safe`) shipped by a Heiss package, picked up
     by `grub-mkconfig`, which the helper allows as a post-action that manifests can request (`policy.py`, `grub-mkconfig`). It is not
     part of the GRUB theme, so it does not touch the protected theme files (`docs/apps/RESEARCH.md`: "the entry
     must be added outside the theme files").
   - Where it is written decides whether Tier A is involved: a package file in `/etc/grub.d/` is not a protected
     path; wiring it from `heiss-cleanup.sh` or the Calamares bootloader module would be (protected). The
     proposal is to ship it as a package file only.
   - NOT VERIFIED: that `grub-mkconfig` on a real installed system picks the script up and the entry boots; UEFI;
     that `nomodeset` plus the module blacklist is enough on NVIDIA hardware; whether `nvidia-utils` already blacklists nouveau (file database not synced here).
2. **A second kernel (`linux-lts`) as a fallback**. `pacman -Si` (core): linux-lts 6.18.60-1, 155.46 MiB download,
   155.95 MiB installed; `linux-lts-headers` 58.85 MiB download, 273.51 MiB installed (only needed for DKMS).
   `nvidia-open-lts` exists in the repositories (1:615.78.08-10, 9.7 MiB, depends on `linux-lts`), so the
   "with the LTS kernel use the DKMS variant" sentence in the NVIDIA warning was out of date and was
   corrected in step 2 and step 4a. `grub-mkconfig` lists installed kernels on its own. Cost: about 156 MiB on disk and
   a longer `mkinitcpio` run for every kernel update.
3. **Snapshot before a driver change**, in the order: (a) snapper snapshot if the system has one, (b) otherwise an
   explicit confirmation that says "no snapshot is available, rollback means removing the packages", shown by the
   wizard and by the Hardware page before it offers a driver that is not `safe_by_default`.
4. **Rollback in one step**: `heiss profile apply` already removes what a profile installed (state file). A
   "Remove this driver" action on the Hardware page would call the same path through the helper. Built (steps 4b and 4c, 2026-11-16); not run on real hardware.

## Decisions needed from the owner

1. **Safe-graphics boot entry as a Heiss package file in `/etc/grub.d/`** (not touching Calamares config or
   `heiss-cleanup.sh`). Answer: A (package file, recommended) / B (wire it through `heiss-cleanup.sh`, Tier A, needs the
   `design-approved` label) / C (not now).
2. **Second kernel.** Answer: A (install `linux-lts` and `nvidia-open-lts` only together with the NVIDIA driver,
   not in the ISO or by default, so the fallback exists exactly where the risk is; recommended) / B (always ship
   `linux-lts` in the installed system, +156 MiB for everyone) / C (no second kernel, rely on the safe-graphics
   entry alone).
3. **NVIDIA without a snapshot.** Until Btrfs exists. Answer: A (the NVIDIA open driver stays never pre-ticked, which is already
   true, and applying it needs a second explicit confirmation that names the missing snapshot and the safe-graphics
   entry; it is offered only if the safe-graphics entry is installed; recommended) / B (hide it until Btrfs and
   snapshots exist).
4. **Order of work.** Answer: A (recommended: (1) the grub.d package and a test of the generated menu text with a scratch
   `grub-mkconfig` where possible, (2) correct the NVIDIA warning text and the LTS statement, (3) confirmation step
   in the wizard and Hardware page, (4) "Remove this driver" through the helper. Install-time detection stays in the
   first-run wizard (a Calamares step is Tier A and is not proposed here)) / B (another order, say which).

Recommended reply in one line: 1 A, 2 A, 3 A, 4 A.

## Not covered here

Btrfs and snapper enablement in Calamares (separate Tier A item), Secure Boot signing of any added kernel module
(DKMS and signed modules are out of scope without real hardware), AUR drivers (not allowed), the themed hardware
settings and the Hardware check view (later Phase 7 PRs).
