# Image audit (`scripts/audit-image.sh`)

A repeatable, read-only inspection of a built ISO. It replaces the by-hand steps of round 25 (list the squashfs, grep for Arch strings, look at units, permissions, pacman.conf, keyring, the safe-graphics script, size).

```
bash scripts/audit-image.sh out/heiss-2026.11.17-x86_64.iso
```

No root needed. It prints one line per check (`OK`, `WARN`, `FAIL`, plus `INFO` for numbers) and ends with the counts. Exit status 0 means no FAIL, 1 at least one FAIL, 2 wrong usage or a missing tool (`unsquashfs`, `bsdtar`).

## Where it works

- The image is unpacked **in part** (only `/etc`, the Heiss, Calamares and Plasma branding files, the pacman keyrings, the pacman database, `usr/local/bin`) with `unsquashfs -no-xattrs -ig` as a normal user; boot menus are read from the ISO with `bsdtar`.
- The work directory is `/var/tmp/heiss-audit.XXXXXX` (a normal disk). It **refuses** a memory file system (tmpfs, ramfs): the full squashfs is about 2.2 GB and a copy in tmpfs once hit the quota. Set `AUDIT_TMP=/some/disk/dir` to use another parent.
- The directory is deleted when the script ends, but only if it is a real directory (not a link) created by this script, named `heiss-audit.*`. The unpacked image has read-only directories, so permissions are restored first.
- `--root DIR [--boot DIR]` audits an already unpacked tree (used by `tests/test_audit_image.py`; there the tests build small fake trees).

## What is checked

| Area | FAIL when | WARN / INFO |
|---|---|---|
| Identity | os-release NAME or PRETTY_NAME mentions Arch; `/etc/issue` or `/etc/motd` says Arch Linux | desktop entries, installer branding and look-and-feel with "Arch Linux" text; `/etc/lsb-release` present or absent (INFO) |
| Boot menus | a visible title (`title`, `MENU LABEL`, `menuentry "..."`) says Arch | an EFI shell binary in the boot files (WARN) |
| Telemetry | an enabled unit looks like telemetry, popcon, reflector, cloud-init, ping; NetworkManager connectivity check on; Calamares tracking enabled or in the sequence | |
| Permissions | `/etc/shadow` or `/etc/gshadow` readable by group or others; world-writable files; sudoers.d files writable by group or others | root hash in the live image (INFO) |
| Repository | heiss keyring missing or without the pinned fingerprint; no `[heiss]` section (pacman.conf or the cleanup script) or no `SigLevel = Required DatabaseRequired` | |
| Packages | a Heiss package (`heiss-core`, `-helper`, `-theme`, `-keyring`, `-welcome`, `-control`, `-safe-graphics`, `-profile-base`) missing; `41_heiss_safe` not executable or without `nomodeset` | `refind` and `arch-install-scripts` still in the live image (expected: the install cleanup removes them); package count and installed size (INFO) |

Not checked (needs a running system): behaviour after boot, the Calamares run, UEFI and Secure Boot, anything that only exists after the install cleanup. See the FINAL VM TEST LIST in `docs/PLAN-STATE.md`.

## The agent

`.claude/agents/branding-auditor.md` runs the script on the newest image and reports its lines. `CLAUDE.md` asks for it on every PR that touches `profile/` or `packages/`. It first checks that the image is newer than the last change to those directories; an older image describes the old state, and the PR text then says "image not inspected".

## Extending it

Add the check in `scripts/audit-image.sh` as a plain `ok`/`warn`/`fail` line, add a good-tree and a broken-tree case to `tests/test_audit_image.py`, and a row to the table above. Keep it read-only and keep every `rm` behind the guard in `cleanup`.
