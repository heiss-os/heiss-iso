# Heiss Control Center (Phase 6)

Split into small PRs. Status of each page:

| Page | Status |
|---|---|
| Overview (profile, privacy level, Heiss-installed package count, pending actions, kernel) | built, read-only |
| About (system, build, kernel, Plasma, links, licence, "not affiliated with Arch Linux") | built, read-only |
| Search (page titles and keywords, en/ru) | built |
| Profiles and software (chosen and applied profile, add-ons, what Heiss OS installed, pending actions) | built; shows what is chosen and installed; applies or removes the actions saved by the wizard ("apply later"); changing the profile needs its own PR |
| Appearance (Dark and Light switch) | built; the only page that changes anything, as the user |
| Advanced (opens the stock KDE System Settings; runs `heiss check` and lists the result) | built; the check changes no settings (it takes a short-lived lock file in the runtime directory, shared with `heiss theme sync`, so the theme item shows WARN while a sync runs) |
| Security Center (firewall, disk encryption, Secure Boot display, SSH, open network ports) | built, read-only: plain-language facts and advice, no fix buttons, no score |
| Network and privacy (chosen level vs. what is in place: Wi-Fi MAC setting, screen lock, firewall; the not-yet-built items listed as coming soon) | built, read-only |
| Updates and snapshots (updates waiting, last system update, restart needed, snapshots set up) | built, read-only |
| Hardware and drivers (what was detected, driver state of each proposal, driver doctor report with a Copy button) | built, read-only |
| Power and display, Backups | later (sidebar entry exists, page says "Coming soon") |

## Structure

- `control/heiss_control/model.py`: what the window shows. No Qt. Every source (os-release, answers, state, pending queue, kernel, `plasmashell --version`) is injected through `Env`, so `control/tests/` run on fixtures without Qt. A source that fails shows its error on its own card and never stops the window.
- `control/heiss_control/app.py`: PySide6 glue (one `control` object for QML). `control/heiss_control/qml/Main.qml`: sidebar, search, pages, colours from the Heiss tokens.
- `control/heiss_control/strings.py`: en/ru; a test requires both languages to have the same keys.

## Rules this shell follows

- The GUI never runs as root and never calls the helper. The only changes it makes are the Dark/Light switch (`plasma-apply-lookandfeel`, as the user, on a worker thread, same LnF ids as the wizard) and starting `systemsettings` detached from Advanced; the system check is `heiss check` run in the same process on a worker thread (it changes no settings; it only takes the short-lived theme-sync lock file); a test checks that building any screen leaves the directories untouched.
- Every `Text` in the QML is `Text.PlainText` and error messages are cut to 300 characters (a test enforces both; see DECISIONS.md, "Profiles and Appearance pages").
- The sidebar already lists the final pages; a page that is not built says "Coming soon" instead of pretending.
- Links open only if they start with `https://` and come from `os-release`.
- Plain QtQuick.Controls like the wizard, not Kirigami (see DECISIONS.md, 2026-11-13).

## Saved actions ("apply later")

The wizard's "Save answers, apply later" and an apply attempted offline put an `apply-profile` item (`{profile, addons}`) into `~/.config/heiss/pending.json`. The Profiles page lists them. "Apply saved actions now" (only on a click, with a warning that it installs software, asks for the password and needs the network) refuses to start offline (NetworkManager's state from `nmcli`, as `heiss profile apply` does; a missing or failing `nmcli` counts as online and pacman then reports the real failure) and otherwise runs `heiss_core.wizard.PendingQueue.run` on a worker thread: for each item `heiss profile apply --yes --adopt --profile=ID --addon=ID...` in a child process (`control/heiss_control/runner.py`), which goes through the helper and polkit exactly like the wizard's Apply. The ids are checked against the manifest id pattern with `fullmatch` before they reach a command line and are passed in the `--option=value` form. Done items leave the queue; a failure stops the run, keeps the item as failed with the message, and "Apply" tries again. "Remove" drops one item without running it. Not carried over: the privacy level and hardware choices of the wizard (the queue holds only profile and add-ons). The queue file is locked (`pending.json.lock`) around every load-modify-save, never while an action runs, and a run merges its result into the file as it is then: an action another process saved during the run is kept, one removed meanwhile is not brought back. The child runs as `python -I -m heiss_core` in `/` with an allowlisted environment (home, locale, the session bus and display for the polkit agent, a fixed `PATH`; the list is in `docs/WELCOME.md`), so nothing in the user's directory or environment is imported before the helper call; consequently Apply does not work from a source checkout (`PYTHONPATH=...`), only from the installed packages.

## Security Center: what it reads

`control/heiss_control/security.py` runs five short, unprivileged checks on a worker thread (the first time the page is opened, and again on "Check again"; the window code is in `control/heiss_control/app.py`): `systemctl is-active/is-enabled firewalld`, `findmnt` then `lsblk -s` for a `crypt` layer under `/`, `/sys/firmware/efi` and the SecureBoot EFI variable (display only), `systemctl is-active sshd`, `ss -H -l -t -n` for non-loopback listening ports. Every command is a literal list with `PATH=/usr/bin:/bin` and `LC_ALL=C`; the only value from outside is the device name `findmnt` prints, passed to `lsblk` as one argument after `--` and only if it starts with `/dev/`. Nothing is changed, so there are no Fix buttons, no snapshot step and no "protection score" (five checks are too few for an honest number; the page says so). Not covered yet: root account lock (needs root to read), `arch-audit` and `lynis` wrapping (not in the ISO), pending updates (Updates page).

## Network and privacy: what it reads

`control/heiss_control/privacy_view.py` (first time the page is opened, and on "Check again", on a worker thread): the chosen level from the answers (`/etc/heiss/profile.toml`, else `~/.config/heiss/answers.toml`), the NetworkManager drop-in the level writes (`/etc/NetworkManager/conf.d/80-heiss-privacy.conf`, read as a file; no file means NetworkManager's own default, `preserve`), the screen-lock keys `Autolock`, `Timeout`, `LockGrace` of `kscreenlockerrc` via `kreadconfig6` with KDE's own defaults as `--default` (so an unset key counts as the default, which equals the Standard level; a key that cannot be read, or a non-numeric `Timeout` or `LockGrace`, is shown as unknown and is not compared, and `Autolock` false is "Look at this" when a level is chosen), and the firewall as in the Security Center. Each in-place value is compared with the table in `heiss_core.privacy`: equal is OK, different is "Look at this" with advice to apply the level again; with no level chosen nothing is compared. It shows the file and the settings, not the running NetworkManager's active value (that changes only when NetworkManager restarts), and it cannot change anything: re-applying a level is `heiss profile apply --privacy=LEVEL` or the wizard (a button comes with the profile-change PR). DNS over TLS, VPN and WireGuard, Bluetooth off and `linux-hardened` are listed as coming soon, as in the wizard.

## Updates and snapshots: what it reads

`control/heiss_control/updates_view.py` (first time the page is opened, and on "Check again", on a worker thread): `pacman -Qu` (reads the local package database; no network, no root, so the count is as of the last refresh; exit 1 with the pacman lock held counts as unknown, other pacman errors cannot be told from "no updates"), the last `starting full system upgrade` line in the last 256 KiB of `/var/log/pacman.log` (older than 30 days is a warning; "unknown" if the log is longer than that and the line is not in the tail, or if the date is in the future), whether `/usr/lib/modules/<running kernel>` still exists (if not, the kernel was replaced and a restart is needed), and `findmnt -n -o FSTYPE /` plus `/etc/snapper/configs/root` for snapshots. Commands are literal lists with `PATH=/usr/bin:/bin`. Nothing is changed: no update button, no rollback, no snapshot listing (`snapper list` needs root) and no Arch news (needs network).

## Hardware and drivers: what it reads

`control/heiss_control/hardware_view.py` (first time the page is opened, and on "Check again", on a worker thread) runs the same read-only detection as `heiss hw detect` (`heiss_core.hardware`: `lspci -nn -mm`, `/sys/class/dmi`, `/sys/class/power_supply`, `/sys/class/bluetooth`, `/proc/cpuinfo`, `systemd-detect-virt --vm`) against `/usr/share/heiss/hardware`, and `pacman -Qq` to see whether the packages of each matching profile are installed (installed, not installed, nothing to install, or unknown when pacman gives no list). A safe-by-default proposal that is missing is a warning, other missing ones are information. Texts come from the hardware profile files shipped by `heiss-core` (names, descriptions and warnings in en and ru) and are drawn as plain text. The driver doctor report is plain text with the kernel release, form factor, CPU vendor, virtualization type, GPU `vendor:device` ids, Bluetooth yes/no and the state of each proposal; it has no hostname, user name, serial numbers, PCI slot addresses, MAC addresses or DMI vendor and product strings (a test checks the PCI slots and DMI strings of every fixture). "Copy the report" puts it on the clipboard; nothing is sent anywhere. The kernel release is included only if it is plain (`[0-9A-Za-z.+_-]`, up to 40 characters), the CPU vendor only as intel, amd or other, and a report longer than 8000 characters ends with a "[truncated]" line. `HEISS_HARDWARE` overrides the profile directory (a test hook, the same variable the wizard reads; the page never runs as root). Installing a driver is not done here: the page names the wizard or `heiss profile apply --hardware=ID`. Not built (rest of Phase 7): snapshot before driver changes, safe-graphics boot entry, install-time detection (a Calamares step is Tier A), the themed hardware settings.

## Advanced page: what the check trusts

The system items of `heiss check` run with a fixed `PATH=/usr/bin:/bin`; its theme item (`kreadconfig6`, `gsettings`, `busctl --user`) uses the user's own environment, as `heiss theme status` does. Every command line of the check is a literal list (read in `core/heiss_core/check.py`); values from files are only compared and shown. `systemsettings` is started through the user's `PATH`.

## Known limit

`plasmashell --version` runs on the GUI thread with a 3 s timeout when About is built. A hanging `plasmashell` would freeze the window for up to 3 s; the Appearance switch already runs on a worker thread, `plasmashell --version` does not yet.

## Package

`packages/heiss-control` (depends on `python`, `pyside6`, `heiss-core`) installs the app, `/usr/bin/heiss-control` and `/usr/share/applications/heiss-control.desktop` (visible in the launcher menu, Settings category). It is in `profile/packages.x86_64`, so it comes from `[heiss-local]`: run `scripts/heiss-packages-build.sh` before the ISO build. The dock pins are not changed (replacing the pinned System Settings is a Tier B item that needs its own "ok"). The icon is the stock `preferences-system`; a Heiss icon is not made yet.

Optional dependencies: `systemsettings` (opened from Advanced), `kconfig` (`kreadconfig6`, reads the colour scheme) and `plasma-workspace` (`plasma-apply-lookandfeel`, switches it); without them the Appearance page shows "unknown" or an error text.

Run from a checkout: `PYTHONPATH=core:control python -m heiss_control` (needs `pyside6`).
