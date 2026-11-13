# Heiss Welcome (first-run wizard): plan and state

Master plan section 7. Stack as in `docs/ARCHITECTURE.md`: PySide6 + QML (Kirigami), official packages (`pyside6` 6.12.0, `kirigami` 6.31.0, `qt6-declarative` 6.12.0 exist in the repositories; installed size of pyside6 52 MiB, not yet added to any package list).

## Split into PRs

| Step | What | Needs the public package repository? | State |
|---|---|---|---|
| 5a `feat/welcome-core` | GUI-free model `core/heiss_core/wizard.py`: step order, per-profile defaults, validation, Back/Next/Skip, skip-whole = Base, resume file, done marker, pending-actions queue, summary as a dry-run plan | no | merged (PR 56) |
| 5b | `heiss-welcome` PySide6/QML app drawing the model; screens 0-11, en/ru strings, keyboard control | no (UI), but offline-only without it | this PR (see below) |
| 5c | hardware screen wired to `heiss hw detect`, privacy screen items marked implemented / "coming soon" | no | this PR |
| 5d | `heiss-welcome` package with an autostart entry for the installed system only (this PR); no `heiss-cleanup.sh` step needed | autostart: no; Apply of a non-Base profile: yes | package built locally, never run |
| 5e | applying screen through the helper (this PR); pending queue run from the Control Center (done, Phase 6 step 6) | yes (profiles other than the ISO's Base come from `[heiss]`) | repository exists; applying written, never run |

## Model (5a)

- Steps in order: welcome, profile, level, addons, hardware, appearance, privacy, software, backups, summary, applying, done. `skip` is allowed on level..backups; welcome, profile and summary are not skippable. Skipping the whole wizard gives Base with all defaults.
- `set(path, value)` validates through `answers.validate`; a bad value changes nothing. Choosing a profile sets that profile's defaults (Cyber: privacy `enhanced`) only for answers the user did not choose.
- **Answers vs extras.** Only keys of the answers schema (`/etc/heiss/profile.toml`) are real answers. Accent, density, font scale, hardware toggles and the backups choice are `extras`: saved and resumable, **not applied by anything yet**. Their application is added together with the screens that need them.
- Resume: `~/.config/heiss/wizard-state.json` (written after each step by the front end). An interrupted "applying" resumes at the summary, because the plan is recomputed against the real system. A corrupt or foreign file is ignored.
- Done marker `~/.config/heiss/welcome-done`; saved answers `~/.config/heiss/answers.toml`.
- **Pending queue** `~/.config/heiss/pending.json`: only the kind `apply-profile` with `{profile, addons}`. Items are validated when added and again when read (a hand-edited file is rejected; ids are matched in full, so a trailing newline is refused). Every load-modify-save is under an exclusive lock (`pending.json.lock`), and `run` merges its result into the file as it is after the run, so an item added or removed meanwhile is respected. Offline nothing runs; a failure stops the run, keeps the item as `failed` with the message; the user retries or removes it. The queue holds no commands and no package names, so it cannot widen what the helper allows.
- Level: Beginner and Confident confirm changes step by step; advanced sections (for example linux-hardened under privacy) show for Confident and Advanced.

## Front end (5b)

- `welcome/heiss_welcome/viewmodel.py`: no Qt; builds each screen as a dict (title, "what this will change", options, buttons) and runs the actions; saves resume state after each action. Tested in `welcome/tests`.
- `strings.py`: en/ru texts (a test checks both languages have the same keys). Profile and add-on names come from the manifests.
- `app.py`: thin PySide6 glue (one `wizard` object for QML). `qml/Main.qml`: one data-driven window, Inter font, Heiss palette, sand accent, Back/Next/Skip, Alt+Left for Back, visible focus ring, accessible names.
- Run by hand: `PYTHONPATH=core:welcome python -m heiss_welcome --force` (needs `pyside6`; config dir override `HEISS_CONFIG_DIR`, manifests `HEISS_PROFILES`). The plan and Apply start `python -I -m heiss_core` in `/` without `PYTHON*`, `LD_*`, `GCONV*`, `LOCPATH`, `NLSPATH`, `GIO_*`, `GI_*`, `G_*`, `GSETTINGS_*`, `HEISS_*` and `DBUS_SYSTEM_BUS_ADDRESS`, so from a source checkout they only work with `heiss_core` installed (installed packages are the supported way; the screens themselves run from a checkout).
- **Not in this PR, on purpose:** Apply (needs the repository, 5e), so the summary offers only "Save answers, apply later" (writes `answers.toml` and one `apply-profile` queue item). The hardware and backups screens are "coming soon" placeholders (5c). Accent, density, font size and the per-item privacy toggles have no screen yet. No autostart, no package (5d). Wizard-side live preview of the theme is not done.

## Hardware and privacy screens (5c)

- Hardware: `ViewModel.report()` runs `heiss_core.hardware` detection once when the screen is first shown (live: `lspci`, `/sys`, `systemd-detect-virt`; read-only; a failure means "no proposals", never blocks). Facts (type, processor, virtualization, GPUs, hybrid graphics) are shown as text; each matching hardware profile is a toggle, ticked by default only when `safe_by_default`. Choices are stored in `extras.hardware_toggles` and are **not applied by anything yet** (no step reads them). Detection runs on the UI thread (a few subprocess calls); moving it to a worker is a follow-up.
- Privacy: the level is a real answer; the item list below it is informational with a badge. The firewall (firewalld, enabled by the Essentials manifest at every level) is marked "In place"; since step 3c also the Wi-Fi MAC address and the screen lock (see below). DNS over TLS, VPN/WireGuard, Bluetooth off at Maximum and linux-hardened (Confident/Advanced only) are marked "Coming soon". Per-item toggles have no screen because nothing could act on them.
- Not verified: the screens were never shown (no PySide6 here); detection was only tested with the fixtures in `core/tests/fixtures/hw`, not on real hardware or in VirtualBox through the wizard.

## Known small gaps

- Pending ids are reused after the newest item is removed (harmless: ids are only handles).
- A resumed state may name `done` without the marker file; the front end decides what to show.

## Not verified

- Nothing in 5a runs on a real system; it is tested with fixtures only (`core/tests/test_wizard.py`).
- The QML was only linted with `qmllint` (no syntax errors; only unqualified-access warnings for the `wizard` context object). It was never run: `pyside6` is not installed on the build VM. Inter font and its fallback, whether `appearance.theme` is applied to the window (it is not), the Alt+Left shortcut, the Bridge/PySide6 behaviour, error colour contrast on Light, layout, focus order, scaling, the colour-scheme detection (`Qt.styleHints.colorScheme`) and the Russian text fit are unjudged without a screenshot from the owner.
- Whether `pyside6` and `kirigami` fit the ISO size budget (needs a build).

## What the owner must do for 5d/5e

The hosted repository does not exist (checked on GitHub: organisation `heiss-os` has no `heiss-repo`). Steps: `docs/infra/REPOSITORY.md`, "Checklist for the owner".

## Applying (5e)

- The summary computes the plan (`heiss --json profile apply --dry-run --adopt --profile=P --addon=A...`, read-only, run on a worker thread once per selection; a failure is retried when the user comes back to the summary) and shows counts: packages to install/remove, services to enable/disable, or "nothing needs to change". If the plan cannot be computed, Apply is off and only "Save answers, apply later" is offered.
- **Apply** runs `heiss profile apply --yes --adopt ...` in a child process on a worker thread (`welcome/heiss_welcome/applier.py`; callbacks that raise do not abandon the pipe). The command goes through the privileged helper (D-Bus + polkit, which asks for the password). Its `[n/total] description` lines become the step text, other lines the log (last 12 shown). The window stays responsive; there is no GLib in the Qt process.
- Success: step `done`, answers saved to `answers.toml`, done marker written. Failure (including no network, found by the command's own preflight): the applying screen stays with the error, **Try again** re-runs the command, **Save answers, apply later** queues an `apply-profile` item and finishes. The window refuses to close while applying (`onClosing`), because the command keeps changing the system; there is no Cancel yet. If the app still dies, the saved state resumes at the summary and the plan is recomputed. The worker thread only updates the job record; the wizard and the store are touched on the GUI thread (`refresh()`), and the done step is set only after the answers were saved.
- `profile`, `addons`, the ticked hardware proposals and the privacy level (3c) are applied; the other answers (animations, software choices) are still saved only, as in 5a-5c. Beginner/Confident per-step confirmation is not implemented: the summary is the single confirmation.
- Not verified: everything on a real system. The QML was only linted (no syntax errors); `pyside6` is not installed here, so the thread-to-GUI signal (`jobUpdated`), the layout and the polkit prompt flow are untested; the real `heiss profile apply` was never run from the wizard. Tests use a fake applier and a fake command (`welcome/tests/test_apply.py`).

## Package and autostart (5d)

- Package `heiss-welcome` (`packages/heiss-welcome`): the `heiss_welcome` Python package with its QML, `/usr/bin/heiss-welcome`, and `/etc/xdg/autostart/heiss-welcome.desktop`. Depends on `python`, `pyside6` (extra: 52 MiB installed, 9.2 MiB download, plus `shiboken6` 0.7 MiB; `qt6-declarative` comes with Plasma), `heiss-core`; `heiss-helper` is optional (needed for Apply, already in the ISO).
- **Installed system only, without touching Tier A:** the autostart entry runs `sh -c "test -e /run/archiso || exec heiss-welcome"`, and `/run/archiso` exists only on the live image. The wizard exits at once when the user's `~/.config/heiss/welcome-done` exists, so it starts once per user.
- The package is in `profile/packages.x86_64`, so the ISO build needs it in `~/localrepo` first (`scripts/heiss-packages-build.sh`).
- Not verified: that `/run/archiso` is really absent on an installed system and present in the live session (reasoned from archiso, not seen); the autostart on a real login; the ISO size change (no build); that `pyside6` 6.12 runs the QML.

## Hardware choices are applied (5f)

- The ticked proposals of the hardware screen (`ViewModel.hardware_ids()`; detection failed or skipped: none) are passed to the plan and to Apply as `--hardware=ID`. `heiss profile apply|diff` accepts `--hardware ID` (repeatable) and `resolver.resolve(..., hardware=, catalog=)` adds the profile's packages, services, drop-ins and post-actions to the plan; the helper already trusts hardware manifests, so the steps run through the usual calls and polkit.
- **Kept, not removed:** a hardware profile whose OWN packages (those the profile does not already want, e.g. not `mesa`) are all Heiss-owned stays wanted on later applies (`resolver.sticky_hardware`); the profiles that fit this machine break ties between siblings that share a package (the two hybrid-graphics profiles share `nvidia-prime`), so changing the profile never proposes removing a graphics driver or the guest tools. Unticking an applied item later does NOT uninstall it: removal needs an explicit action (Control Center, Phase 6).
- **Kernel parameters are not applied** (changing the boot loader is a separate risk): the plan prints a `note:` for each profile that asks for them (today `gpu-nvidia-open`: `nvidia-drm.modeset=1`). NVIDIA open modules are never ticked by default (`safe_by_default` is false) and carry a warning.
- Post-actions of a hardware profile (`mkinitcpio`, `grub-mkconfig`) run only when packages or drop-ins change; `grub-mkconfig` is a hard step and assumes GRUB (Heiss installs GRUB), a failure ends the apply as failed after the packages are installed. `hardware_ids()` runs detection on the GUI thread if the hardware screen was skipped.
- Not verified: any real install of a hardware package (VirtualBox guest tools, microcode, GPU drivers); the NVIDIA path in particular (black-screen risk, kernel param missing); on a real machine whether the sticky rule keeps drivers after a profile change.

## Theme choice is applied (5g)

- Picking Dark or Light on the appearance screen switches the running desktop at once (`welcome/heiss_welcome/theme.py`: `plasma-apply-lookandfeel --apply org.heiss.dark.desktop` or `org.heiss.light.desktop`, as the user, no shell, on the worker thread). Plasma then applies colors, icons and style, and the existing theme-sync path unit should do the rest (not verified). The wizard window follows the color scheme, so it changes too (a live preview).
- **Automatic** changes nothing: Plasma's own automatic light/dark switching is not configured by Heiss. Quick successive clicks are numbered: only the newest choice switches the desktop. A failed switch is shown as a note under the question; it never blocks the wizard. CI checks that `plasma-workspace` ships the tool (`pacman -F`).
- Animations stay "saved only" until the motion system (Phase 8).
- Not verified: `plasma-apply-lookandfeel` on a live Plasma session with these LnF packages, the window recolouring, and whether the theme-sync path unit fires after it.

## Privacy level applied (3c)

- Apply passes `--privacy=<level>` (`standard`, `enhanced`, `maximum`; the wizard answer). `heiss_core/privacy.py` holds the data: a NetworkManager drop-in `/etc/NetworkManager/conf.d/80-heiss-privacy.conf` (`wifi.cloned-mac-address` preserve / stable / random, `ethernet.cloned-mac-address` preserve / preserve / stable, random MAC while scanning) and the screen lock keys in `~/.config/kscreenlockerrc` group `Daemon` (`Autolock=true`, `Timeout` 5 / 3 / 1 minutes, `LockGrace` 5 / 5 / 0 seconds). Key names and defaults were read from the NetworkManager man pages and the shipped `kscreenlockersettings.kcfg`.
- The drop-in is written by the new helper method `WritePrivacy(level)` (polkit action `org.heiss.config.write`): the client sends only the level name; path and content are constants. Screen lock keys are written as the user with `kwriteconfig6`, like the other KDE settings. Only differences from the system are planned; without `--privacy` the CLI changes nothing about privacy.
- **Takes effect:** the screen lock at the next lock timer start (already-running session may need re-login); the MAC setting when NetworkManager restarts (reboot) and per connection: a connection profile with its own cloned MAC keeps it, and `random` can break captive portals and MAC allow lists. No service is restarted by Heiss.
- Not done (still "Coming soon"): DNS over TLS, VPN/WireGuard, Bluetooth off at Maximum, linux-hardened.
- Not verified: any run on a real system (NetworkManager reading the file, the MAC actually changing, kscreenlocker honouring the keys, the polkit prompt); the D-Bus integration tests need python-gobject and were skipped here.
- The wizard always passes the level, so even the default Standard writes the drop-in (explicit NetworkManager defaults) and sets the KDE lock to 5 minutes / 5 seconds grace. The drop-in and the KDE keys are not recorded in `state.json`: nothing removes them when a profile changes; they are only overwritten by the next level. Also not verified: the real `heiss profile apply --privacy` run (needs root and the helper), and the `kscreenlockerrc` keys written by `kwriteconfig6` as the user.
