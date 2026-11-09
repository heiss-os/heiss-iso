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

## Commands

```
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile list
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile show cyber
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile diff --profile cyber --addon addon-kitty
PYTHONPATH=core python3 -m heiss_core --profiles profiles profile apply --dry-run --profile base
```

`apply` shows the plan, asks `Apply these changes? [y/N]` (`--yes` skips the question; without a terminal and without `--yes` it refuses), then runs the plan through the privileged helper. Order: claim (`--adopt`), install, enable services, write drop-ins, disable services, remove, post actions; removals come last so a failed install never strips the system. KDE settings from manifests are written as the user afterwards. Before anything changes it refuses when the plan contains Flatpak changes (not supported yet) or when packages must be downloaded and NetworkManager reports no connection. If a step fails it stops and says which step; earlier steps stay applied and `heiss profile diff` shows what is left. `apply` needs `python-gobject` and the helper installed. `diff` and `apply --dry-run` read the real system (`pacman`, `systemctl`) and `/var/lib/heiss/state.json`; override with `HEISS_STATE` and `HEISS_ETC`.

## Ownership and removal

`/var/lib/heiss/state.json` lists what Heiss installed. A profile change removes only packages in that list that no selected manifest wants and that no other installed package requires; the rest is reported as "kept". Packages already on the system (for example everything on the ISO) are not Heiss-owned unless adopted with `--adopt`, which claims only explicitly installed packages named in the selected manifests. Delivery option (a) needs this adoption step on first boot so that "Custom" can remove Base extras; the call is part of the wizard work (Phase 5).

## Packages

`packages/` holds six packages, built by `scripts/heiss-packages-build.sh` from git HEAD into `[heiss-local]` (uncommitted changes are not included):

- `heiss-core`: the Python engine, the `heiss` command, ALL manifests (`/usr/share/heiss/profiles`, so every profile and add-on is known before its metapackage is installed) and the hardware profiles (`/usr/share/heiss/hardware`).
- `heiss-helper`: the privileged D-Bus service, its D-Bus policy and activation file, the systemd unit and the polkit actions. Depends on `heiss-core`, `python-gobject`, `polkit`, `dbus`.
- `heiss-profile-essentials`, `-base`, `-cyber`, `-developer`: generated from the manifests by `scripts/gen-profile-packages.py` (TOML -> PKGBUILD; never edit by hand, CI runs `--check`). They are EMPTY: they only depend on the packages of their manifest and on the metapackage of each manifest they require (cyber -> base -> essentials). They enable no services and have no install scripts; services, drop-ins and KDE settings are applied by the engine.

Not packaged as metapackages: `custom` and the add-ons (the engine installs their packages directly).

Bump the matching value in `packages/pkgrel.json` whenever a package's dependency list or content changes, otherwise installed systems will not see an update. `heiss-core` and `heiss-helper` take their version from `__version__` in the code (a test checks that the PKGBUILDs agree).

Relation to the engine: the engine installs the manifest packages explicitly and records them in the state file, so removal stays precise. The ISO contains `heiss-core`, `heiss-helper` and `heiss-profile-base` (see `docs/ISO-E2E-TEST.md`); `scripts/check-iso-packages.py` (CI) checks every ISO list entry exists in the repositories or is a local package.
