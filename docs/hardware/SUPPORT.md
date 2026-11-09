# Hardware detection and support (Phase 2)

`heiss hw detect` is read-only. It collects facts (`lspci -nn -mm`, `/sys/class/dmi`, `/sys/class/power_supply`, `/sys/class/bluetooth`, `/proc/cpuinfo`, `systemd-detect-virt --vm`), matches them against declarative profiles in `hardware/*.toml` and prints proposals. Nothing is installed or changed here; proposals will go through the resolver and the privileged helper (Phases 3 and 7).

```
PYTHONPATH=core python3 -m heiss_core hw detect --hardware hardware            # live system
PYTHONPATH=core python3 -m heiss_core hw detect --hardware hardware --fixture core/tests/fixtures/hw/nvidia-hybrid-laptop --lang ru
```

## Profile format

One TOML file per profile (`schema_version`, `id`, `name`/`description`/`warnings` in en and ru, `safe_by_default`, `packages`, `services`, `kernel_params`, `dropins`, `post_actions`, and a `[match]` table). All match keys must hold: `cpu_vendor`, `virt` (`none` or the exact `systemd-detect-virt` name), `form_factor` (`laptop`, `desktop`, `vm`), and `pci`, a list of conditions, each satisfied by some device (`vendor`, `class` = display or network, `devices`, `device_min`, `device_max`). Rollback is the removal of what the profile installed, tracked by the state file.

`safe_by_default = true` only marks a proposal as pre-selected; nothing is applied without confirmation.

## Shipped profiles and what they do

| Profile | Matches | Installs |
|---|---|---|
| cpu-microcode-intel / -amd | CPU vendor, not in a VM | intel-ucode / amd-ucode |
| gpu-intel, gpu-amd | PCI vendor 8086 / 1002, display class | Mesa, Vulkan (+ intel-media-driver) |
| gpu-nvidia-open | NVIDIA display, device ID >= 0x1e00 | nvidia-open, nvidia-utils, early KMS drop-in; needs confirmation |
| gpu-nvidia-legacy | NVIDIA display, device ID <= 0x1dff | nothing new; stays on the open nouveau stack; message; never AUR |
| hybrid-nvidia-intel / -amd | laptop with both GPUs | nvidia-prime |
| wifi-broadcom | PCI vendor 14e4 network | linux-firmware-broadcom; warning that older chips need an out-of-tree driver that is NOT installed |
| laptop-power | laptop | power-profiles-daemon |
| vm-virtualbox / -vmware / -qemu / -hyperv | matching hypervisor | guest tools for that hypervisor only |

## Tests and honesty

- Fixtures in `core/tests/fixtures/hw/`: one REAL capture (`virtualbox-vmsvga`, taken on the build VM, only non-identifying fields) and five SYNTHETIC ones written by hand from known PCI IDs (`synthetic: true` in `facts.json`): Intel iGPU laptop, AMD desktop, NVIDIA modern, NVIDIA old, NVIDIA + Intel hybrid laptop, Broadcom Wi-Fi laptop. Synthetic fixtures check the rules, not real hardware.
- The NVIDIA threshold (open modules for device IDs from 0x1e00, Turing and newer) is a heuristic taken from NVIDIA's public statement, NOT verified against the package: the pacman file database is not synced here, so `supported-gpus.json` could not be inspected. The profile warning says so.
- NOT verified: any real hardware, hybrid graphics behavior and boot safety, early KMS, Broadcom behavior, USB devices (not collected yet: `lsusb` is not installed on the build VM), fingerprint readers, printers, touchscreens, Bluetooth detection beyond `/sys/class/bluetooth`, Secure Boot interaction, install-time use.
- Not built yet: snapshot before driver changes, safe-graphics boot entry, the "driver doctor" report (Phase 7).
