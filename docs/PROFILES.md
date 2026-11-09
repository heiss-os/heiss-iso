# Profiles and add-ons

Manifests live in `profiles/*.toml` (one file per id, file name = id). They are validated by `core/heiss_core/manifest.py`; unknown keys, bad names, non-`/etc/**/*.d/` drop-in paths and unlisted post-actions are rejected.

| id | kind | requires | packages | download / installed (packages alone, without dependencies) |
|---|---|---|---|---|
| essentials | profile | none | 49 | 412 / 1039 MiB |
| base | profile | essentials | 20 | 53 / 167 MiB |
| cyber | profile | base | 11 | 80 / 286 MiB |
| developer | profile | base | 20 | 162 / 746 MiB |
| custom | profile | essentials | 0 | 0 / 0 MiB |
| addon-kitty, addon-thunar | addon | none | 1 / 3 | 19 / 77 and 3 / 15 MiB |
| addon-lts-kernel | addon | none | 1 | 155 / 156 MiB |
| addon-cyber-extended | addon | cyber | 3 | 380 / 837 MiB |
| addon-developer-extended | addon | developer | 3 | 443 / 750 MiB |
| addon-office, addon-mail | addon | none | 1 | 148 / 422 and 82 / 303 MiB |

Sizes come from `scripts/check-packages.py` (pacman sync database, 2026-11-09). They exclude dependencies, so real downloads are larger; not yet exact. Shared packages (gdb, podman, distrobox) are counted in each manifest that lists them.

## Rules

- Official repositories only. `scripts/check-packages.py` and the CI job `packages-exist` fail if a package disappears.
- Installing a profile never weakens defaults: only `essentials` enables services (NetworkManager, SDDM, Bluetooth, firewalld, fstrim.timer).
- Konsole and Dolphin are the defaults. Kitty and Thunar are add-ons.
- Not in any profile yet: NVIDIA and other hardware-dependent packages (Phase 7), Flatpak/Flathub (an answer, off by default), Inter font (ships with the branding package, Phase 10), Heiss's own packages (not written yet).

## Commands (read-only for now)

```
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile list
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile show cyber
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile diff --profile cyber --addon addon-kitty
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile apply --dry-run --profile base
```

`apply` without `--dry-run` refuses until the privileged helper exists (Phase 3). `diff` and `apply --dry-run` read the real system (`pacman`, `systemctl`) and `/var/lib/heiss/state.json`; override with `HEISS_STATE` and `HEISS_ETC`.

## Ownership and removal

`/var/lib/heiss/state.json` lists what Heiss installed. A profile change removes only packages in that list that no selected manifest wants and that no other installed package requires; the rest is reported as "kept". Packages already on the system (for example everything on the ISO) are not Heiss-owned unless adopted with `--adopt`, which claims only explicitly installed packages named in the selected manifests. Delivery option (a) needs this adoption step on first boot so that "Custom" can remove Base extras; the call is part of the wizard work (Phase 5).
