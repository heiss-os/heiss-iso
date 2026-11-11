# Security model of the privileged helper

Scope: `helper/` (`heiss-helper`, D-Bus name `org.heiss.Helper1`) and how `heiss-core`, the Welcome wizard and the Control Center use it. Status: first iteration, implemented and unit tested; the GDBus and polkit glue is only tested in CI on a private bus (see "Not verified").

## 1. Goals and non-goals

- A GUI or CLI running as an ordinary user can ask for a small, fixed set of system changes. Everything else stays impossible, even after the user authenticates.
- Non-goals: defending against root, against a compromised Arch mirror or signing key (pacman signatures are the control there), or against a user who is allowed to become admin and wants to break their own system. The helper limits *what* can be done, not *whether an admin may*.

## 2. Architecture

```
GUI/CLI (user) --D-Bus--> heiss-helper (root, systemd Type=dbus, exits after 60 s idle)
                              |-- polkit CheckAuthorization(caller bus name, action id)
                              |-- allowlists from root-owned manifests (/usr/share/heiss/...)
                              `-- fixed argv: pacman, systemctl, snapper, mkinitcpio, grub-mkconfig, ...
```

Files: `helper/heiss_helper/{policy,actions,dispatch,runner,audit}.py` (logic, tested without a bus), `service.py` / `polkit.py` / `__main__.py` (GDBus glue), `helper/data/` (D-Bus policy and activation, systemd unit, polkit actions).

## 3. What a client can ask for

| D-Bus method | polkit action | What it does | Validation |
|---|---|---|---|
| InstallPackages(as) | org.heiss.packages.install | `pacman -S --needed --noconfirm -- names` | every name must exist in a manifest (profiles or hardware); name regex forbids a leading `-` or `.`; max 500, no duplicates |
| RemovePackages(as) | org.heiss.packages.remove | `pacman -R --noconfirm -- names` (no `-s`, no `-c`: never cascades) | name in manifests AND recorded as installed by Heiss AND not in the essentials manifest |
| AdoptPackages(as) | org.heiss.packages.adopt | records already installed, explicitly installed packages as Heiss-owned | name in manifests; installed; explicit; not owned yet |
| SetServices(as, as) | org.heiss.services.manage | `systemctl enable/disable -- units` (never `--now`) | unit in manifests; no overlap |
| WriteDropin(s) | org.heiss.config.write | writes ONE file | path must equal a drop-in declared in a manifest; the CONTENT is taken from the manifest, never from the client |
| WritePrivacy(s) | org.heiss.config.write | writes ONE fixed file (`/etc/NetworkManager/conf.d/80-heiss-privacy.conf`) | the argument is only a level name (`standard`, `enhanced`, `maximum`); path and content are constants in `heiss_core/privacy.py`, never from the client; no service is restarted |
| RunPostAction(s) | org.heiss.postaction.run | fixed argv (`mkinitcpio -P`, `grub-mkconfig -o /boot/grub/grub.cfg`, ...) | id must be one of four known ids |
| UpdateSystem() | org.heiss.system.update | `pacman -Syu --noconfirm` | none needed; always a full upgrade, never `-Sy` alone |
| CreateSnapshot(s) | org.heiss.snapshot.create | `snapper -c root create --description ...` | description regex, 80 chars |

All polkit actions default to `allow_any=no`, `allow_inactive=no`, `allow_active=auth_admin_keep` (one authentication covers the several calls of one apply run). Texts are in English and Russian.

There is no method that takes a command, a file path to read, or file content.

## 4. Controls

1. **Authorization first, validation second.** An unauthorized caller always gets `NotAuthorized`, so the allowlist cannot be probed.
2. **No shell.** Commands are argument lists built in `actions.py`/`policy.py`; the environment is reset to `LC_ALL=C` and a fixed `PATH`; stdin is `/dev/null`. A test fails if `shell=True`, `os.system`, `eval` or `exec` appear in the helper.
3. **Option injection.** Names cannot start with `-`; every argv puts `--` before client data.
4. **Trusted allowlists.** Manifests are loaded on every call from `/usr/share/heiss/{profiles,hardware}`. The directories and files must be owned by root and not group- or world-writable and not symlinks, otherwise every request is refused.
5. **Drop-in writes.** Normalized absolute path under `/etc/`, no symlink on any path component, target must not be a non-regular file, written to a temporary file with `O_EXCL|O_NOFOLLOW`, `fsync`, then `os.replace`; mode 0644.
6. **Ownership state.** `/var/lib/heiss/state.json` (root-owned, locked with `flock`, atomic writes) is updated by the helper after a successful step, so a client cannot claim packages. Packages that were already installed before an install call are not recorded as Heiss-owned.
7. **One job at a time**, a `db.lck` check, at least 1 GiB free space, best-effort snapshot before install/remove/update (a failed snapshot is a warning, an explicit `CreateSnapshot` failure is an error).
8. **Resource limits.** At most 8 requests wait for polkit or validation; more are refused with `Busy`. Output is capped at 20000 lines per command and 3600 s per command.
9. **Signals go only to the caller** (unicast), so other users do not see job output.
10. **Audit.** Every call is logged to journald (identifier `heiss`) and `/var/log/heiss/audit.log` with uid, method, parameters and result. Control characters are replaced; drop-in content is never logged (tested).
11. **Idle exit.** The helper quits after 60 seconds without calls and is restarted by D-Bus activation.
12. **systemd hardening:** `NoNewPrivileges`, `PrivateTmp`, `ProtectHome`, `ProtectControlGroups`, `ProtectKernelTunables`, `RestrictRealtime`, `LockPersonality`. Deliberately not set: `ProtectSystem` (pacman writes `/usr`), a capability bounding set (pacman's download sandbox needs setuid-related capabilities). Whether `PrivateTmp`/`ProtectHome` break any pacman hook is NOT verified.

## 5. Self-review: how could the helper be abused?

| # | Attack or failure | Result |
|---|---|---|
| 1 | Package name with shell metacharacters, newlines, `--overwrite=*`, `-Syu` | Rejected by regex and allowlist; even a manifest entry cannot start with `-` (manifest validator and tests). |
| 2 | Ask for an arbitrary package to be installed or an arbitrary file written | Only manifest-declared names and drop-ins; content comes from the manifest. |
| 3 | Plant a malicious drop-in path via symlink in `/etc` | Symlink check on every component; only root can create symlinks there anyway. A check-then-use race needs a root-level attacker. |
| 4 | Edit the manifests to widen the allowlist | Requires write access to root-owned directories; the helper refuses to run if they are writable by others. A malicious manifest in a legitimate signed Heiss package is a supply-chain risk, controlled by package signing (Phase 1a) and review. |
| 5 | Remove essential software (NetworkManager, the kernel, the helper's own dependencies) | Essentials are never removable through the helper; non-owned packages are never removable; no cascade. |
| 6 | Trick the user into approving a harmful call | polkit shows the action text. Weak point: the dialog does not list package names. Mitigation planned: GUI shows the exact plan before calling (the wizard summary page). |
| 7 | Disable the firewall or other security services through `SetServices` | Possible with admin authentication, because `firewalld.service` and `bluetooth.service` are in manifests (privacy settings need it). It is audit-logged. Accepted risk; the Security Center must always ask for explicit confirmation. |
| 8 | Local user floods the helper with requests | Admission cap of 8 and a single running job; each call still triggers polkit work. A prompt-spamming local process is an annoyance, not a privilege gain. NOT rate limited per user. |
| 9 | Read job output of another user | Signals are unicast to the caller's bus name. |
| 10 | Log injection | Control characters are replaced; length capped. |
| 11 | A caller keeps the `auth_admin_keep` authorization alive | Retained per caller process for polkit's short timeout; a different process needs its own authentication. |
| 12 | A package install script (pacman hook/.install) does something harmful | Out of scope: pacman runs signed package scripts as root by design. |
| 13 | `-Sy` partial upgrades | There is no code path that refreshes databases except `UpdateSystem` (`-Syu`). Install without a fresh database may fail with a 404; the user then runs the full update. |
| 14 | Crash in validation leaves the lock held or a half-started job | Unexpected exceptions become a clean `Failed` refusal; the job lock is always released (tests). |
| 15 | Network drops mid-install | pacman downloads first and applies the transaction atomically; a failure ends the job with an error and nothing is recorded as owned. NOT verified with real network faults. |

## 6. Not verified (honest list)

- The GDBus glue (`service.py`, `polkit.py`, `__main__.py`) could not be run on the build VM (python-gobject is not installed and I may not install it). CI runs an integration test on a private bus with a fake authorizer; the real `CheckAuthorization` call to polkitd has never been exercised, and the `((sa{sv})sa{ss}us)` call signature comes from the polkit documentation.
- The D-Bus bus policy, activation file, systemd unit and polkit policy file are not installed or loaded anywhere yet; they are only parsed in tests.
- Real `pacman`, `systemctl`, `snapper`, `mkinitcpio`, `grub-mkconfig` runs through the helper.
- The helper's behaviour with a real polkit agent dialog (Plasma) and `auth_admin_keep`.
- Packaging: the files are not yet shipped by a package (Phase 10), so nothing runs on an installed system.
- `heiss profile apply` and the Gio client (`helper/heiss_helper/client.py`) are tested against the service on a private bus in CI only, with a fake polkit; never against a real polkitd, real pacman or a real system.
- Pending design work: a `Cancel` method, flatpak actions, saving the answers file (`/etc/heiss/profile.toml` is root-owned and the helper has no method to write it yet), forgetting state entries of packages that disappeared.
