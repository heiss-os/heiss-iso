# Heiss Control Center (Phase 6)

Split into small PRs. Status of each page:

| Page | Status |
|---|---|
| Overview (profile, privacy level, Heiss-installed package count, pending actions, kernel) | built, read-only |
| About (system, build, kernel, Plasma, links, licence, "not affiliated with Arch Linux") | built, read-only |
| Search (page titles and keywords, en/ru) | built |
| Profiles and software (chosen and applied profile, add-ons, what Heiss OS installed, pending actions) | built, read-only; changing the profile needs the helper (later PR) |
| Appearance (Dark and Light switch) | built; the only page that changes anything, as the user |
| Advanced (opens the stock KDE System Settings; runs `heiss check` and lists the result) | built; the check changes no settings (it takes a short-lived lock file in the runtime directory, shared with `heiss theme sync`, so the theme item shows WARN while a sync runs) |
| Security Center (firewall, disk encryption, Secure Boot display, SSH, open network ports) | built, read-only: plain-language facts and advice, no fix buttons, no score |
| Updates and snapshots, Network and privacy | later PRs |
| Hardware and drivers (Phase 7), Power and display, Backups | later (sidebar entry exists, page says "Coming soon") |

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

## Security Center: what it reads

`control/heiss_control/security.py` runs five short, unprivileged checks on a worker thread (once when the page opens, again on "Check again"): `systemctl is-active/is-enabled firewalld`, `findmnt` then `lsblk -s` for a `crypt` layer under `/`, `/sys/firmware/efi` and the SecureBoot EFI variable (display only), `systemctl is-active sshd`, `ss -H -l -t -n` for non-loopback listening ports. Every command is a literal list with `PATH=/usr/bin:/bin`; the only value from outside is the device name `findmnt` prints, passed to `lsblk` as one argument after `--` and only if it starts with `/dev/`. Nothing is changed, so there are no Fix buttons, no snapshot step and no "protection score" (five checks are too few for an honest number; the page says so). Not covered yet: root account lock (needs root to read), `arch-audit` and `lynis` wrapping (not in the ISO), pending updates (Updates page).

## Advanced page: what the check trusts

The system items of `heiss check` run with a fixed `PATH=/usr/bin:/bin`; its theme item (`kreadconfig6`, `gsettings`, `busctl --user`) uses the user's own environment, as `heiss theme status` does. Every command line of the check is a literal list (read in `core/heiss_core/check.py`); values from files are only compared and shown. `systemsettings` is started through the user's `PATH`.

## Known limit

`plasmashell --version` runs on the GUI thread with a 3 s timeout when About is built. A hanging `plasmashell` would freeze the window for up to 3 s; the Appearance switch already runs on a worker thread, `plasmashell --version` does not yet.

## Package

`packages/heiss-control` (depends on `python`, `pyside6`, `heiss-core`) installs the app, `/usr/bin/heiss-control` and `/usr/share/applications/heiss-control.desktop` (visible in the launcher menu, Settings category). It is in `profile/packages.x86_64`, so it comes from `[heiss-local]`: run `scripts/heiss-packages-build.sh` before the ISO build. The dock pins are not changed (replacing the pinned System Settings is a Tier B item that needs its own "ok"). The icon is the stock `preferences-system`; a Heiss icon is not made yet.

Optional dependencies: `systemsettings` (opened from Advanced), `kconfig` (`kreadconfig6`, reads the colour scheme) and `plasma-workspace` (`plasma-apply-lookandfeel`, switches it); without them the Appearance page shows "unknown" or an error text.

Run from a checkout: `PYTHONPATH=core:control python -m heiss_control` (needs `pyside6`).
