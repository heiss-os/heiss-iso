# End-to-end test of the helper and `heiss profile apply` in a VM

Goal: the next ISO build proves (or breaks) the chain `heiss` CLI -> D-Bus -> polkit -> helper -> pacman/systemd on a real installed system. Nothing below has been run yet: everything is "not verified" until you send the results.

## What the ISO now contains

`profile/packages.x86_64` gains `heiss-core`, `heiss-helper` and `heiss-profile-base` (which pulls Essentials and the default apps: delivery option (a), Base in the ISO). The packages are built into `[heiss-local]`.

Size: the existing ISO (built 2026-11-04) is 2.55 GiB. NOT measured after the change (an ISO build needs sudo here). The 35 directly added packages weigh 288 MiB installed / 83 MiB download, but several (plasma-workspace, kwin, powerdevil, ...) are already dependencies of plasma-desktop, and their new dependencies are not counted, so the real growth is smaller than that and needs a measured build.

## Build

```bash
cd ~/heiss-iso            # the repository, on the branch to test, changes committed
scripts/heiss-packages-build.sh      # builds heiss-core, heiss-helper, heiss-profile-* from git HEAD into ~/localrepo
HEISS_FAST=1 scripts/heiss-build.sh  # then the ISO as usual
```

If the ISO build says a `heiss-*` package is not found, the first step was skipped.

## In the live session (optional, quick)

```bash
heiss profile list
heiss hw detect
busctl --system call org.heiss.Helper1 /org/heiss/Helper1 org.heiss.Helper1 Ping   # expect: s "0.1.0"
pkaction --action-id org.heiss.packages.install                                    # expect the action, no error
```

## After installing to disk and logging in as the created user

1. Plan only (changes nothing):
   ```bash
   heiss profile apply --dry-run --profile base --adopt
   ```
   Expect: a list of packages to adopt, services to enable (firewalld, bluetooth, ...), a drop-in `/etc/systemd/zram-generator.conf.d/heiss.conf`.
2. Apply (a polkit password dialog must appear; the password is the user's own):
   ```bash
   heiss profile apply --profile base --adopt --yes
   ```
   Expect `[1/N] ...` lines, streamed output, `done`.
3. Check the result:
   ```bash
   systemctl is-enabled firewalld.service bluetooth.service
   cat /etc/systemd/zram-generator.conf.d/heiss.conf
   sudo cat /var/lib/heiss/state.json
   sudo cat /var/log/heiss/audit.log
   journalctl -t heiss --no-pager | tail -20
   ```
4. Profile change over the network (needs internet):
   ```bash
   heiss profile apply --profile cyber --yes
   heiss profile apply --profile base --yes     # removes only what Heiss installed for cyber
   ```
5. Offline refusal: disconnect the network, then `heiss profile apply --profile developer --yes`. Expect "no network connection ... nothing was changed".
6. Rejection of bad input (a polkit dialog may still appear; expect error `Invalid`):
   ```bash
   busctl --system call org.heiss.Helper1 /org/heiss/Helper1 org.heiss.Helper1 InstallPackages as 1 evil-package
   ```
7. Cancelling the polkit dialog must give `NotAuthorized` and change nothing.

## Please send back

The terminal output of steps 1-7, `systemctl --failed`, `journalctl -u heiss-helper --no-pager`, and the audit log. Mark anything that looked odd, especially: the dialog text, how long each step took, and any step that stalled.

## Known risks to look at first

- `systemctl enable sddm.service` while `display-manager.service` already points at it (should be a no-op; if it prints "File exists", report it).
- The helper's systemd options (`PrivateTmp`, `ProtectHome`) against pacman hooks.
- `fakeroot` printed `payload not recognized` during `makepkg` on the build VM: the packages were still created and inspected, but the cause is unknown.
- Everything about the real polkit call: it was only tested against a fake in CI.

## Theme sync and terminals (added with `heiss theme sync`)

In the desktop session:

```bash
heiss theme status                       # report only, changes nothing
# System Settings -> Appearance -> Global Theme -> Heiss Light, wait 5 s, then:
journalctl --user -u heiss-theme-sync --no-pager | tail -20
cat ~/.local/state/heiss/theme-sync.log
```

Open a NEW Konsole window and keep one that was open before the switch: both must show the Light colors. Switch back to Heiss Dark and repeat. Expected in the log: six `theme-sync:` lines per switch; anything marked `warn` or `failed` is what I need to see. Details and the list of unverified assumptions: `docs/design/THEME-SYNC.md`.
