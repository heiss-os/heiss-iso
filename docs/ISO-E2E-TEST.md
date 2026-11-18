# End-to-end test of the helper and `heiss profile apply` in a VM

Goal: the next ISO build proves (or breaks) the chain `heiss` CLI -> D-Bus -> polkit -> helper -> pacman/systemd on a real installed system. Nothing below has been run yet: everything is "not verified" until you send the results.

## What the ISO contains

`profile/packages.x86_64` lists the Heiss packages `heiss-core`, `heiss-helper`, `heiss-profile-base` (pulls Essentials and the default apps: Base is in the ISO), `heiss-theme`, `heiss-keyring`, `heiss-welcome`, `heiss-control` and `heiss-safe-graphics`, plus `inter-font`. All of them are built into `[heiss-local]` (`~/localrepo`) by `scripts/heiss-packages-build.sh`; Calamares comes from `scripts/heiss-calamares-build.sh`.

Size: NOT measured with the current package list. The last ISO built (2026-11-04, `~/share/hhhheiss-2026.11.04-x86_64.iso`) is 2.55 GiB and predates the Heiss packages, `pyside6` and `inter-font`; `linux-lts` and `nvidia-open-lts` are not in the ISO (they come with the NVIDIA driver). The real size is read from the first build of round 23, part 3.

## Build

Run on the build VM as the normal user (no root: the ISO script calls `sudo` itself and asks for the password). The packages are built from git HEAD of the checked-out branch, so the work must be committed and clean. For a release test use `main`, up to date; to test a branch, check it out instead.

```bash
cd ~/heiss-iso
git checkout main
git pull
git status --short
```

1. Calamares (only if `~/localrepo/calamares-*.pkg.tar.zst` is missing or you want the pinned AUR build; the one from 2026-11-01 is enough for a first build). It asks pacman questions, answer them:
   ```bash
   bash scripts/heiss-calamares-build.sh
   ```
2. The Heiss packages (the log is also saved for reading):
   ```bash
   bash scripts/heiss-packages-build.sh 2>&1 | tee ~/heiss-packages.log
   ```
   Expect `==> Building from commit <hash>` (the hash of `git log -1`) and `Done. Now build the ISO.`
3. The ISO (15-40 minutes; `sudo` asks for your password, possibly again at the copy step; on a `[Y/n]` question press Enter):
   ```bash
   HEISS_FAST=1 bash scripts/heiss-build.sh 2>&1 | tee ~/heiss-build-script.log
   ```
   `HEISS_FAST=1` uses zstd for the squashfs: quicker, ISO bigger (not the final size). Leave it out for the release-size image.
4. After it ends, whatever the result, put the logs where they can be read (the share is mounted by the script only at its end, so the logs are written to the home directory first). `~/build.log` is the full mkarchiso log; it is missing or old if the script stopped before mkarchiso (then the script log is the one to read):
   ```bash
   mkdir -p ~/share
   mountpoint -q ~/share || sudo mount -t vboxsf share ~/share -o uid=$(id -u),gid=$(id -g)
   cp ~/heiss-packages.log ~/heiss-build-script.log ~/build.log ~/share/
   ls -l ~/share/*.log
   ```

Where things end up: the ISO in `~/heiss-iso/out/heiss-*.iso` and, copied with a checksum, in `~/share/` (the script then prints `sha256 OK`); the logs in `~/share/heiss-packages.log`, `~/share/heiss-build-script.log` and `~/share/build.log`. If the ISO build says a `heiss-*` package is not found, step 2 was skipped or failed. To see what the script would do without building: `bash scripts/heiss-build.sh --dry-run`.

The script deletes the old `~/archiso-work` and `out/*.iso` first and removes `~/share/heiss-*.iso` before copying the new one. It does not touch other files in the share.

After a successful build the image is inspected without booting it (see "Static checks on the built image" in `docs/PLAN-STATE.md`); the VM install test is the owner's step after that.

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

## One command that checks the installed system

`heiss check` (part of `heiss-core`, already in the ISO and in Base; no extra package) prints one line per item, `OK`, `FAIL` or `WARN` (WARN = cannot be judged here, for example no desktop session or not running as root). Exit code 0 means no FAIL. Run it as the normal user first (this covers user units and the theme), then once with `sudo` (only the root-lock item needs it; as root the user-unit and theme items are reported as WARN "not checked as root"; the check makes no network calls). Under `sudo`, `~` is root's home, so give a path that the user can read:

```bash
heiss check --report ~/heiss-check.txt
sudo heiss check --report /tmp/heiss-check-root.txt
```

Items: failed units (system and user), profile and state file consistency, launcher menu (hide stubs and duplicate names), the 37 packages removed in PR 49 absent (a package that Heiss itself installed for Cyber is expected), the Hyprland session (session files, configs, SDDM theme present, no KDE packages left; a WARN until the first login has copied `~/.config/hypr/hyprland.lua`), helper (`org.heiss.Helper1` answers `Ping`, polkit and D-Bus files installed), no live leftovers (liveuser, archiso packages, root locked). The report holds the full output, the exact commands and their raw output (except the read-only commands of the theme item, which are listed by `heiss theme status`).

Run it after step 3 and after step 4 above. A fresh install before any `heiss profile apply` is expected to give `WARN profile-state` (no state file yet).

## Please send back

`~/heiss-check.txt` and `/tmp/heiss-check-root.txt`, the terminal output of steps 1-7, `systemctl --failed`, `journalctl -u heiss-helper --no-pager`, and the audit log. Mark anything that looked odd, especially: the dialog text, how long each step took, and any step that stalled.

## Known risks to look at first

- `systemctl enable sddm.service` while `display-manager.service` already points at it (should be a no-op; if it prints "File exists", report it).
- The helper's systemd options (`PrivateTmp`, `ProtectHome`) against pacman hooks.
- `fakeroot` printed `payload not recognized` during `makepkg` on the build VM: the packages were still created and inspected, but the cause is unknown.
- Everything about the real polkit call: it was only tested against a fake in CI.

## Theme sync and terminals (KDE preview image only, obsolete: `heiss theme sync` is removed)

In the desktop session:

```bash
heiss theme status                       # report only, changes nothing
# System Settings -> Appearance -> Global Theme -> Heiss Light, wait 5 s, then:
journalctl --user -u heiss-theme-sync --no-pager | tail -20
cat ~/.local/state/heiss/theme-sync.log
```

Open a NEW Konsole window and keep one that was open before the switch: both must show the Light colors. Switch back to Heiss Dark and repeat. Expected in the log: six `theme-sync:` lines per switch; anything marked `warn` or `failed` is what I need to see. Details were in the removed THEME-SYNC document (see git history before H1a).

## The Hyprland session (H1; nothing of it has run yet)

Before the first boot: in the VM settings enable 3D acceleration (VirtualBox: Display, Graphics Controller VMSVGA, tick "Enable 3D Acceleration"). Without it the session retries once with software rendering (about 10 s longer); the boot entry "safe graphics" starts software rendering at once.

In the live session and again after an installation:

```bash
cat ~/.local/state/heiss/session.log
ls ~/.config/hypr ~/.config/waybar ~/.config/heiss/theme
heiss check
```

Expected: the log has `starting Hyprland with /home/.../.config/hypr/hyprland.lua` and no `exited with`, and the screen shows no "autogenerated config" or "start-hyprland" banner; the three directories hold the copied files (`hyprland.lua`, `heiss-user.lua`, `hypridle.conf`, `hyprlock.conf`, `config.jsonc`, `hypr-colors.conf`, `wallpaper`); `heiss check` shows `OK session`.

Theme (H1b):

```bash
heiss theme get
heiss theme set light
heiss theme set dark
heiss theme status
heiss-gtk-audit after-dark
```

Expected: `get` prints `dark` at the first login; `set light` prints seven lines `theme: <target>: ...`, none `failed`, and the bar, launcher (Alt+D), a Thunar window, Firefox and kitty turn light at once or at their next start; `set dark` turns them back; `status` shows `current theme` and no `warn`. Send back the output of the `set` commands and a screenshot in each theme.

## Looking at the windows without a display (`scripts/render-gui.py`)

A developer tool, not part of the VM test. On any machine with `pyside6` (no root, no display, no helper):

```bash
python3 scripts/render-gui.py            # PNGs go to a new directory under $TMPDIR, the paths are printed
python3 scripts/render-gui.py --out ~/share/gui-shots --only control --lang ru --theme light
```

It starts the real `Main.qml` of heiss-welcome (the key-binding window: search, empty result, own configuration, both languages) and
heiss-control (every page, a search, and the smallest window) with `QT_QPA_PLATFORM=offscreen`, on the hardware
fixtures of `core/tests/fixtures/hw` and fake sources, in dark and light, in `en` and `ru`, and prints every Qt/QML
warning and error. Look at the PNGs; expect `Qt/QML warnings and errors: 0`. The test `tests/test_render_gui.py`
runs it (skipped without PySide6).

What this does **not** show (still needs the VM): the real fonts (Inter is not installed on the build VM, so text is
drawn in a fallback face), the real Plasma colour scheme and window decoration, animations, the polkit prompt, the
worker threads and signals (the script's bridge is synchronous), the clipboard, anything the real helper or system
tools return. The light theme is rendered from a copy of the QML with the one colour-scheme test replaced
(the offscreen platform has no colour scheme).
