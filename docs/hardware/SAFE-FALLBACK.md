# Safe fallback and snapshot before driver changes (Phase 7 design, nothing built yet)

Status: proposal for the owner. No code, no Tier A file is touched by this document. Items marked NOT VERIFIED
could not be checked on the build host (no UEFI, no real GPU, the pacman file database is not synced there).

## Problem

A bad GPU driver can leave the user with a black screen and no way back. Today:

- The NVIDIA profile (`hardware/gpu-nvidia-open.toml`) tells the user: "If the screen stays black, choose the safe
  graphics boot entry". **That entry does not exist.** The warning promises something we do not ship.
- The helper takes a best-effort snapshot before install/remove/update, but only when `snapper` and
  `/etc/snapper/configs/root` exist (`helper/heiss_helper/actions.py`). The installer creates ext4 today
  (`docs/PLAN-STATE.md`, Phase 6 note: Btrfs and snapshots are a separate Tier A item), so on a fresh install
  there is **no snapshot** and the only rollback is removing the packages the state file recorded.
- No second kernel is installed (`profile/packages.x86_64` has `linux` only).

## What would be built

1. **Safe-graphics boot entry** (GRUB, installed system only). An extra menu entry that boots the same kernel with
   `nomodeset` and the NVIDIA modules kept out (`modprobe.blacklist=nvidia,nvidia_modeset,nvidia_uvm,nvidia_drm`),
   so the machine reaches a text or generic-graphics desktop and the user can remove the driver.
   - Mechanism: a script in `/etc/grub.d/` (for example `41_heiss_safe`) shipped by a Heiss package, picked up
     by `grub-mkconfig`, which the helper already runs as a post-action (`policy.py`, `grub-mkconfig`). It is not
     part of the GRUB theme, so it does not touch the protected theme files (`docs/apps/RESEARCH.md`: "the entry
     must be added outside the theme files").
   - Where it is written decides whether Tier A is involved: a package file in `/etc/grub.d/` is not a protected
     path; wiring it from `heiss-cleanup.sh` or the Calamares bootloader module would be (protected). The
     proposal is to ship it as a package file only.
   - NOT VERIFIED: that `grub-mkconfig` on a real installed system picks the script up and the entry boots; UEFI;
     that `nomodeset` plus the module blacklist is enough on NVIDIA hardware.
2. **A second kernel (`linux-lts`) as a fallback**. `pacman -Si` (core): linux-lts 6.18.60-1, 155.46 MiB download,
   155.95 MiB installed; `linux-lts-headers` 58.85 MiB download, 273.51 MiB installed (only needed for DKMS).
   `nvidia-open-lts` exists in the repositories (1:615.78.08-10, 9.7 MiB, depends on `linux-lts`), so the
   "with the LTS kernel use the DKMS variant" sentence in the NVIDIA warning is out of date and should be
   corrected in a later PR. `grub-mkconfig` lists installed kernels on its own. Cost: about 156 MiB on disk and
   a longer `mkinitcpio` run for every kernel update.
3. **Snapshot before a driver change**, in the order: (a) snapper snapshot if the system has one, (b) otherwise an
   explicit confirmation that says "no snapshot is available, rollback means removing the packages", shown by the
   wizard and by the Hardware page before it offers a driver that is not `safe_by_default`.
4. **Rollback in one step**: `heiss profile apply` already removes what a profile installed (state file). A
   "Remove this driver" action on the Hardware page would call the same path through the helper. Not built.

## Decisions needed from the owner

1. **Safe-graphics boot entry as a Heiss package file in `/etc/grub.d/`** (not touching Calamares config or
   `heiss-cleanup.sh`). Recommended: yes. Alternative: wire it through `heiss-cleanup.sh` (Tier A, needs the
   `design-approved` label). Answer: A (package file) / B (Tier A route) / C (not now).
2. **Second kernel.** Recommended: install `linux-lts` (and `nvidia-open-lts` when the NVIDIA profile is chosen)
   only together with the NVIDIA driver, not in the ISO or by default, so the fallback exists exactly where the
   risk is. Alternatives: always ship `linux-lts` in the installed system (+156 MiB for everyone); or no second
   kernel (rely on the safe-graphics entry alone). Answer: A / B / C.
3. **NVIDIA without a snapshot.** Until Btrfs exists, recommended: the NVIDIA open driver is never pre-ticked
   (already true), and applying it needs a second explicit confirmation that names the missing snapshot and the
   safe-graphics entry; and it is offered only if the safe-graphics entry is installed. Alternative: hide it until
   Btrfs and snapshots exist. Answer: A / B.
4. **Order of work.** Recommended: (1) the grub.d package and a test of the generated menu text with a scratch
   `grub-mkconfig` where possible, (2) correct the NVIDIA warning text and the LTS statement, (3) confirmation step
   in the wizard and Hardware page, (4) "Remove this driver" through the helper. Install-time detection stays in the
   first-run wizard (a Calamares step is Tier A and is not proposed here).

## Not covered here

Btrfs and snapper enablement in Calamares (separate Tier A item), Secure Boot signing of any added kernel module
(DKMS and signed modules are out of scope without real hardware), AUR drivers (not allowed), the themed hardware
settings and the Hardware check view (later Phase 7 PRs).
