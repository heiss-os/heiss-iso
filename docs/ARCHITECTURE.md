# Architecture (target design, Phase 0 proposal)

Status: proposal. Nothing here is implemented yet. Items marked CONFIRM need an owner answer (see `docs/apps/RESEARCH.md`, section 9).

## 1. Overview

```
 Welcome wizard (GUI)   Control Center (GUI)   CLI: heiss ...
          \                    |                   /
           +-----------  heiss-core (Python, no GUI deps)  -----------+
           |   answers schema | resolver | state | hw detection      |
           +----------------------------+------------------------------+
                                        | D-Bus (system bus), polkit
                              heiss-helper  org.heiss.Helper1  (root, systemd-activated)
                                        |
                  pacman | systemctl | drop-in config writes | snapper | flatpak
```

Rule: the GUI never runs as root; the helper accepts only structured commands (action id + validated parameters).

## 2. Components

| Component | Language / stack (CONFIRM) | Role |
|---|---|---|
| `heiss-core` | Python 3, stdlib + PyYAML/tomllib, no Qt | Answers model, manifests, resolver, state, hardware detection, CLI |
| `heiss-helper` | Python 3, `dbus` binding from official repos | Privileged executor on the system bus |
| `heiss-welcome` | PySide6 + QML (Kirigami) | First-run wizard, installed system only |
| `heiss-control` | PySide6 + QML (Kirigami) | Control Center |
| `heiss-profile-*` | metapackages | `essentials`, `base`, `cyber`, `developer` |
| `heiss-theme` | generated files | Output of `scripts/gen-theme.py` |
| `heiss-drivers` | data + core module | Hardware profiles |

Verified in the repositories (2026-11-09): `pyside6 6.12.0-3`, `qt6-declarative 6.12.0-3`, `kirigami 6.31.0-1`, `kirigami-addons 1.16.0-1`. There is no `python-pyside6` package; the package is named `pyside6`.

## 3. Data model

- System answers: `/etc/heiss/profile.toml`, user answers: `~/.config/heiss/`. Both carry `schema_version`, are validated on load and migrated when the version differs.
- State: `/var/lib/heiss/state.json` records which packages and services Heiss installed. A profile change removes only what Heiss installed and nothing else needs.
- Manifests: `profiles/*.yaml` (id, names en/ru, packages, flatpaks, services, drop-ins, KDE keys, post-actions, sizes, dependencies, conflicts). Direction YAML -> PKGBUILD is the proposed default (one source of truth, generated metapackages); decision pending, to be recorded in `DECISIONS.md`.

## 4. Resolver and execution

answers + manifests + current state -> plan (install / enable / configure / remove). `--dry-run` prints the plan. Execution is idempotent, atomic per step, resumable. Never `pacman -Sy` without `-u`. Before applying: snapshot if available, free-space check, network check, lock against parallel pacman runs.

## 5. Helper security model (summary; full text goes to `docs/SECURITY-MODEL.md` in Phase 3)

- Separate polkit actions: install packages, manage services, write config, snapshots.
- Package names validated against an allowlist built from the manifests; paths normalized; writes only into drop-in directories.
- No arbitrary command strings. Logging to journald (tag `heiss`) plus an audit log without secrets.
- First iteration may use `pkexec` + allowlist, with a written plan to move to D-Bus.

## 6. Data flow examples

1. Wizard "Apply": answers saved -> resolver builds plan -> user sees summary -> core sends action requests to the helper one by one -> helper snapshots, runs, reports progress -> state file updated.
2. Offline: network actions go to a "Pending actions" queue stored next to the answers; the Control Center runs them later.
3. Theme switch: see "Theme sync" below.

## 7. Theme sync (extension of the existing `heiss-theme-sync`)

Today it only sets the launcher icon variant after a Global Theme change (triggered by a systemd user path unit watching `~/.config/kdeglobals` plus an autostart entry). Target: one Dark/Light/Auto switch updates color scheme, Plasma style, icons, wallpaper, splash, GTK3/4 CSS, portal color-scheme, Konsole, kitty, launcher icon; one log line per target. Plasma 6.8 offers automatic light/dark switching natively (to verify in a VM); the sync script must react to it, not duplicate it.

## 8. File layout (target)

```
profiles/            manifests (YAML)
packages/<name>/     PKGBUILDs (heiss-branding, heiss-core, heiss-helper, ...)
branding/tokens/     heiss-tokens.json (single source of truth)
scripts/gen-theme.py generator, stdlib only
docs/                this documentation
profile/             archiso profile (unchanged structure)
```

## 9. Boot and install flow (as of today, for reference)

Live ISO (archiso, releng-based) -> SDDM autologin as `liveuser` -> Calamares autostart. Calamares sequence (protected): welcome, locale, keyboard, partition, usersq, summary; exec: partition, mount, unpackfs, machineid, fstab, locale, keyboard, localecfg, shellprocess@boot, shellprocess@cleanup, usersq, hwclock, bootloader, umount. `heiss-cleanup.sh` strips live-only parts inside the target chroot. There is no `packages`, `services-systemd` or `netinstall` step in the sequence today.
