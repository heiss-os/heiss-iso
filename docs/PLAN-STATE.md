# Plan state (checkpoint)

Read this file at the start of every session. Source plan: `heiss-master-prompt.md` (kept outside the repo, in `~/share/`).

Last updated: 2026-11-14

## Done

- Phase 0 documents written on branch `docs/phase-0-aduit` (docs only, no code, no Tier A file touched):
  `DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/design/AUDIT.md`, `docs/apps/RESEARCH.md`,
  `docs/infra/REPOSITORY.md` (hosted repository + owner checklist), `docs/infra/SCREENSHOTS.md`.

## In progress

- Waiting for the owner's answers to the Phase 0 questions (see the end of the Phase 0 report; defaults are listed in `docs/apps/RESEARCH.md`, section 9).

## Next

- Phase 1a: hosted repository, signing design, CI skeleton (needs owner actions from `docs/infra/REPOSITORY.md`).
- Phase 1b: `feat/design-tokens-and-guards` (tokens, generators, contrast tests, `protected-paths` job, checksums).

## Open questions

See `docs/apps/RESEARCH.md`, section 9 (numbered, each with a recommended default).

## Not verified so far (honest list)

- Real versions of Plasma, KWin and Calamares inside the ISO that was built (the repository database says Plasma 6.8.2; Calamares 3.4.2-2 sits in `~/localrepo`). The existing ISO was not unpacked.
- UEFI, Secure Boot, real hardware, installed system after Calamares (ext4 is the Calamares default today).
- Every visual statement in `docs/design/AUDIT.md` marked "to verify": needs screenshots from the owner.

## Phase status (2026-11-10)

- Phase 0: merged (PR 37). Phase 1b: merged (PR 38). Phase 1a: owner checklist in `docs/infra/REPOSITORY.md`, waiting for owner actions.
- Phase 2: PR "feat/core-profiles" (core engine: manifests, answers, state, resolver, CLI, profiles). Merged: core engine (PR 39), hardware detection (PR 40). Metapackages merged (PR 41). Profile rename in README/CLAUDE.md: PR docs/profile-rename. Phase 2 is then complete; next is Phase 3 (privileged helper, polkit) unless the owner reorders.

## Phase 3 (2026-11-10)

PR "feat/helper-polkit": helper (`helper/`), polkit policy, D-Bus and systemd files, `docs/SECURITY-MODEL.md`, `SECURITY.md`. Owner actions: enable GitHub private vulnerability reporting; optionally `sudo pacman -S python-gobject` on the build VM so the D-Bus glue can be tested locally.
Next: Phase 4 (default apps and theming) or wiring `heiss profile apply` to the helper (client library), whichever the owner prefers.

## Apply wiring (2026-11-10)

PR "feat/apply-via-helper": `heiss profile apply` now runs the plan through the helper (client library `helper/heiss_helper/client.py`). Phase 3 follow-ups still open: saving answers, Cancel, Flatpak. Next: Phase 4 (default apps, theming) or Welcome wizard prerequisites.

## Phase 4, part 1 (2026-11-10)

PR "feat/iso-engine-and-base": ISO gets heiss-core, heiss-helper, heiss-profile-base; build script, CI package checks, `docs/ISO-E2E-TEST.md`. Waiting for: an ISO build and the end-to-end test results from the owner. Next Phase 4 PRs: mime associations and default-app configuration, GTK theming and portal color-scheme, extended theme sync, icon fixes, removal of releng leftovers (needs an owner decision).

## Phase 4, part 2 (2026-11-10)

PR "feat/file-associations": `/etc/xdg/mimeapps.list`, `scripts/check-mimeapps.py`, `docs/apps/ASSOCIATIONS.md`. Waiting for: the VM check of defaults. Still open in Phase 4: GTK theming and portal color-scheme, extended theme sync, icon fixes, clean launcher menu, shortcuts, releng leftovers (owner decision).

## Phase 4, part 3 (2026-11-10)

PR "feat/gtk-integration-audit": `heiss-gtk-audit`, GTK doc, prerequisite tests, informational CI facts. Waiting for: the audit output and screenshots from the VM (Dark and Light), together with the associations and helper tests. Still open in Phase 4: extended theme sync, icon fixes, clean launcher menu, shortcuts, terminal/file-manager theming, releng leftovers (owner decision).

## Phase 4, part 4 (2026-11-10)

PR "feat/theme-sync-extended" (stacked on the GTK audit PR): `heiss theme sync|status`, package `heiss-theme` (Konsole and kitty themes from tokens), file-conflict CI check. Waiting for: VM run (theme switch log and screenshots). Still open in Phase 4: icon fixes, clean launcher menu, shortcuts, releng leftovers (owner decision), "open terminal here" behaviour.

## Phase 4, part 5 (2026-11-10)

PR "build/remove-releng-leftovers": 37 packages removed from `packages.x86_64` (Cyber tools, rescue and imaging tools, legacy VPN/dial-up, unused storage tools); see DECISIONS.md. Waiting for: an ISO rebuild and boot/install check. Still open in Phase 4: icon fixes, file manager pins, clean launcher menu, shortcuts, "open terminal here".

## Phase 4, part 6 (2026-11-10)

PR "fix/icons": `scripts/check-launchers.py` guard (CI), audit findings; no icon files changed (Tier A, no defect found without a screenshot). Needs from the owner: dock and installer-in-dock screenshots from the next ISO. Still open: file manager pins, clean launcher menu, shortcuts, "open terminal here".

## Phase 4, part 7 (2026-11-10)

PR "feat/clean-launcher-menu": ten hide stubs in `usr/local/share/applications`, `scripts/check-menu.py` (CI), `docs/apps/LAUNCHER.md`. Needs from the owner: a Kickoff screenshot (Dark and Light). The "file manager pins" item is treated as covered by the dock-pin checks of the icon PR; Dolphin Places defaults were NOT done (KIO has no system-wide defaults file I could verify). Still open: shortcuts, "open terminal here".

## Phase 4, part 8 (2026-11-10)

PR "docs/keyboard-shortcuts": `docs/design/SHORTCUTS.md` (verified table from desktop files), `scripts/check-shortcuts.py` + CI step; no config shipped. Needs from the owner: the Plasma shortcut list from the VM (System Settings, Shortcuts, or `~/.config/kglobalshortcutsrc`). Still open: "open terminal here".

## Phase 4, part 9 (2026-11-10) and checkpoint

PR "docs/open-terminal-here": `docs/apps/TERMINAL-HERE.md`, test `core/tests/test_terminal.py`; no config shipped.

**Phase 4 checkpoint (all items of the owner's list have a PR):** releng leftovers (#49), icon guard and audit (#50), clean launcher menu (#51), keyboard shortcuts (#52), open terminal here (this PR). PRs 47 and 48 (GTK audit, theme sync) merged earlier.
Waiting for the owner: merge the PRs; rebuild the ISO (`scripts/heiss-packages-build.sh`, then `heiss-build.sh`); VM run of `docs/ISO-E2E-TEST.md`; screenshots (Dark and Light): dock, running installer in the dock, Kickoff menu; output of `heiss-gtk-audit` and `heiss theme sync`; Plasma shortcut list; "open terminal here" results (steps in `docs/apps/TERMINAL-HERE.md`).
Not done and why: Dolphin Places defaults (no verifiable system-wide mechanism in KIO), kitty/Thunar terminal configuration (needs the VM), GTK theming files (decided by the audit output).
Next: Phase 5 (Welcome wizard) after the owner's reply.

## Round 15, item 1 (2026-11-10)

PR "feat/reviewer-agent": `.claude/agents/reviewer.md` and a paragraph in CLAUDE.md. Next: item 2 `heiss check` (branch `feat/heiss-check`), only after the owner reports this PR merged. Then Phases 5-10 one PR at a time.

## Round 15, item 2 (2026-11-10)

PR "feat/heiss-check": `heiss check [--report FILE]` (`core/heiss_core/check.py`, `core/tests/test_check.py`), `docs/ISO-E2E-TEST.md` uses it. Waiting for: the owner's run of `heiss check` on an installed VM (never run on a real installed system yet). Next: Phase 5 plan (Welcome wizard) after the owner reports this PR merged.

## Round 15, Phase 5, step 5a (2026-11-10)

PR "feat/welcome-core": `core/heiss_core/wizard.py`, `core/tests/test_wizard.py`, `docs/WELCOME.md` (the Phase 5 plan and split). Blocked for 5d/5e: the public package repository does not exist (owner checklist in `docs/infra/REPOSITORY.md`). Next without it: 5b (QML front end) after the owner reports 5a merged.

## Round 16, part 1 (2026-11-11)

PR "chore/no-attribution": rule in CLAUDE.md and `.claude/settings.json`. Merged earlier commits keep their trailers. Next: part 2 (public package repository setup).

## Round 16, part 2 (2026-11-11): partly done

PR "chore/package-repo-setup": Pages and `gh-pages` done, key generated, public key and fingerprint in `docs/infra/`. Waiting for the owner: set the two secrets and `REPO_PUSH_TOKEN`, delete the token copy, then the key backup and wipe. Phase 5d/5e still waits for the CI publishing job (not started).

## Round 16, Phase 5, step 5b (2026-11-11)

PR "feat/welcome-ui": `welcome/` (view-model, en/ru strings, PySide6 glue, one QML window), tests in CI. Apply is not wired (5e); the summary only saves answers and queues `apply-profile`. Waiting for the owner: `sudo pacman -S pyside6`, then `PYTHONPATH=core:welcome python -m heiss_welcome --force` and screenshots (Dark, Light, ru). Next: 5c (hardware screen and privacy items), after the owner reports 5b merged.

## Round 16, Phase 5, step 5c (2026-11-11)

PR "feat/welcome-hardware": hardware screen (live read-only detection, proposals as saved-but-not-applied toggles) and privacy screen (informational items, only the firewall marked in place). Waiting for the owner: screenshots of both screens in the VM (hardware shows VirtualBox guest-tools proposal). Next: 5d/5e stay blocked on the CI publishing job for the package repository; ask the owner whether to start that job or reorder (Phase 6 Control Center).

## Round 16, CI publishing job (2026-11-11)

PR "ci/publish-repo": `.github/workflows/publish-repo.yml`, `scripts/heiss-repo-assemble.sh`, `scripts/heiss-repo-verify.sh`. Secrets `REPO_GPG_PRIVATE_KEY`, `REPO_GPG_KEY_ID`, `REPO_PUSH_TOKEN` exist (checked with `gh secret list`). The assemble script was run locally with a throwaway key on a scratch clone (nothing pushed); the pacman check runs only in CI. The first real publish happens when this PR is merged to `main` (or by a manual run afterwards). Next: check the run, then `pacman -Sy` from `https://heiss-os.github.io/heiss-repo/x86_64` in the VM; then `heiss-keyring` and the `pacman.conf` entry, then 5d/5e.

## Round 16, publish workflow fix (2026-11-11)

PR "fix/publish-workflow-yaml": the first run on main (#61) failed in 0 s with "workflow file issue" and no log: a step name contained `: ` and the YAML did not parse (`mapping values are not allowed here`, line 99). The same defect meant the pull request dry run never ran either, so nothing of the job has executed yet. Fixed by rewording the step name; all three workflow files now parse with PyYAML. The first real run is the merge of this PR; still not verified: build, pacman check, publish.

## Round 18, part 1 (2026-11-11): public repository verified read-only

Checked against `https://heiss-os.github.io/heiss-repo/x86_64/` (nothing installed): tree on `gh-pages` complete (7 packages, each with `.sig`, `heiss.db`/`heiss.files` with `.sig`); `heiss.db` is zstd (`tar --zstd -tf`, not `-tzf`) and lists the same 7 packages; `heiss.db.sig` verifies with `docs/infra/heiss-public.asc` (key `DDD2 92CC C861 3FD3 324D 3833 FEA8 4CEF 8AED F132`); every package and `.sig` answers HTTP 200 and the `%FILENAME%` entries of the db match the files. Not tested: real pacman over HTTPS. PR "feat/repo-index-pages": generated `index.html` for `/` and `/x86_64/` (no directory listing on Pages); an index-only change is published without rebuilding the db.
## Round 18, part 2, step 5d-1 (2026-11-11): heiss-keyring

PR "feat/heiss-keyring": package `heiss-keyring` (key file, `heiss-trusted`, `.install` running `pacman-key --populate heiss`), `docs/infra/heiss-public.asc` added to the build archive, tests for the pinned fingerprint, CI step that installs it and checks pacman-key trust. Built locally (contents and fingerprint inspected); the populate/trust step has only run in CI, not here (needs root). NOT done, needs the owner's decision (Tier A): the `[heiss]` section in the installed system's `pacman.conf` goes into `heiss-cleanup.sh` (protected, label `design-approved`), and `heiss-keyring` must be added to `profile/packages.x86_64`. See the questions in the reply of this round. Wiring Apply in the wizard (5e) depends on both.

## Round 18, part 2, step 5d-2 (2026-11-11): repository in the installed system

PR 65, re-applied as "fix/repo-in-installed-system" (stacked on the keyring PR 64; owner approved both Tier A items): `heiss-cleanup.sh` imports the Heiss key and appends `[heiss]` (`SigLevel = Required DatabaseRequired`) only if the import worked, skippable with `HEISS_NO_REPO=1`; `heiss-keyring` in `profile/packages.x86_64`; `protected.sha256` updated. Needs the label `design-approved`. Not verified: a real installation (the ISO was not built); `pacman -Sy` on an installed system against the real repository. Next: 5e (Apply in the wizard through the helper), which then can be tested in the VM.

## Round 19 (2026-11-11): PR 65 re-applied on main

PR 65 went into `feat/heiss-keyring` instead of `main`; PR "fix/repo-in-installed-system" cherry-picks its squash commit onto `main` (no conflicts) and adds the "Before asking the owner to merge" rule to CLAUDE.md. Same content and same not-verified list as step 5d-2 above (no real installation, ISO not built). Next: 5e after this PR is merged.

**Build order for the next ISO:** `heiss-keyring` is in `profile/packages.x86_64` and comes only from `[heiss-local]`: run `scripts/heiss-packages-build.sh` (after this PR is on `main`) before `heiss-build.sh`, otherwise mkarchiso fails with "target not found".

## Round 19, Phase 5, step 5e (2026-11-11)

PR "feat/welcome-apply": Apply in the wizard (`welcome/heiss_welcome/applier.py`, view-model job state, strings en/ru, QML buttons and log, `welcome/tests/test_apply.py`, `docs/WELCOME.md`). Not verified: any run on a real system or in the VM (no `pyside6` here, ISO not built); the QML only linted. Needs from the owner in the VM: `sudo pacman -S pyside6 python-gobject`, then `PYTHONPATH=core:welcome:helper python -m heiss_welcome --force` on a machine with `heiss-helper` installed and `[heiss]` configured; screenshots of summary, applying, failure and done (Dark, Light, ru); and whether the polkit prompt appears. Not done: Welcome package, autostart and the `heiss-cleanup.sh` step (5d proper), pending-queue runner (Phase 6), Cancel, back-to-summary.

## Round 19, Phase 5, step 5d (2026-11-11)

PR "feat/welcome-package": package `heiss-welcome`, autostart for the installed system only (live excluded by `/run/archiso`), `heiss-welcome` in `profile/packages.x86_64`, tests. Built locally and the package contents inspected; nothing run. Next ISO build: `scripts/heiss-packages-build.sh` first (pyside6 comes from `extra`). Needs from the owner after a rebuild: in the live session the wizard must NOT start; after installing and logging in it must start once (screenshots, Dark/Light/ru). Phase 5 is then complete apart from the not-applied extras; next candidate is Phase 6 (Control Center) after the owner's reply.

## FINAL VM TEST LIST: items marked "Not verified" compiled so far, by phase (running checklist)

Owner's rule (2026-11-11): no ISO build and no VM check until the whole master plan is done. This list is the test script for that final check. Every PR that adds an unverified claim adds a line here under its phase (tick `[x]` only after a real run, a screenshot or a measurement). Compiled from the docs and PR texts, not from a new test, so it may still miss items: when you find one, add it. Format: `[ ] what to do / what to see`.

### Phase 1: repository, signing, guards
- [ ] A real `pacman -Sy` on the installed system against `https://heiss-os.github.io/heiss-repo/$arch` works with `SigLevel = Required DatabaseRequired` (the files and signature were checked by hand with curl and gpg, never by pacman over HTTPS).
- [ ] `pacman -S heiss-profile-cyber` (or another profile) from `[heiss]` installs.
- [ ] Encrypted backup of the signing key made by the owner and the temporary key directory wiped (owner action, `docs/infra/REPOSITORY.md`).
- [ ] UEFI and Secure Boot boot of the ISO (never tested).
- [ ] The first real `publish-repo` run against `heiss-os/heiss-repo` and GitHub Pages serving `heiss.db` over HTTPS to a real pacman (`docs/infra/REPOSITORY.md`).

### Phase 2: engine and hardware detection
- [ ] `heiss hw detect` on VirtualBox shows the VirtualBox guest-tools proposal; on real hardware the GPU, laptop and hybrid-graphics detection is correct (only fixtures were tested).
- [ ] `heiss profile apply --dry-run` plans match the real installed package set (adopt, kept and removed packages).
- [ ] NVIDIA threshold (0x1e00, Turing and newer) is a heuristic: compare with `supported-gpus.json` once the file database is synced; hybrid graphics boot safety and early KMS; Broadcom, fingerprint readers, printers, touchscreens, Bluetooth beyond `/sys/class/bluetooth`, USB devices, Secure Boot interaction (`docs/hardware/SUPPORT.md`); the synthetic fixtures were never compared with real hardware.

### Phase 3: helper and polkit
- [ ] Helper command time limit with a real pacman: on an installed system run `sudo python3 -c 'from heiss_helper.runner import Runner; print(Runner().run(["pacman","-Sw","--noconfirm","linux-firmware"], print, timeout=2))'` (download only: nothing is installed or upgraded; if the import fails, find the package with `python3 -c 'import heiss_helper; print(heiss_helper.__file__)'`) / expect `124` within about 15 s, `pgrep pacman` printing nothing and no `/var/lib/pacman/db.lck`; if the package is cached already, use a larger one that is not. If a lock stays, SIGTERM did not let pacman clean up: report it. Then `sudo python3 -c 'from heiss_helper.runner import Runner; print(Runner().run(["true"], print, timeout=None))'` / expect `0`. Never run here against the real pacman.
- [ ] State file readable by the user: on an installed system run one install through the helper (Welcome wizard Apply, or the Control Center), then run `ls -l /var/lib/heiss/state.json` / expect `-rw-r--r-- 1 root root ...`; run `ls -ld /var/lib/heiss` / expect `drwxr-xr-x ... root root`; as the ordinary user (not root) run `heiss profile diff --profile base` / expect a plan on stdout and exit 0, no traceback and no "Permission denied"; open the Control Center page "Profiles and software" / expect the profile and package cards filled, no error card. On a system that has a 0600 state.json from before this fix, run `ls -l` again after the next successful helper step / expect `-rw-r--r--`. Never run here against the real helper.
- [ ] `heiss-helper` starts on the system bus and the polkit prompt appears and works for install, services, drop-ins and removal (D-Bus glue was tested only on a private bus with fakes; `python-gobject` tests are skipped without the package).
- [ ] The D-Bus bus policy, activation file, systemd unit and polkit policy are installed and loaded by the real system (only parsed in tests); the real `CheckAuthorization` call to polkitd; the Plasma polkit agent dialog with `auth_admin_keep` (`docs/SECURITY-MODEL.md`, section 6).
- [ ] Real pacman, systemctl, snapper, mkinitcpio and grub-mkconfig runs through the helper.
- [ ] Failed install, locked pacman database, low disk space and network loss are reported properly and leave a resumable state.
- (Not built, so not testable yet: Cancel of a running helper job, Flatpak support in the helper, saving answers by the helper.)

### Phase 4: default apps and theming
- [ ] `docs/ISO-E2E-TEST.md` run in full; `heiss check` run on an installed VM (never run on a real installed system).
- [ ] File associations (`docs/apps/ASSOCIATIONS.md`) open the intended default apps: `xdg-mime query default application/pdf` gives `org.kde.okular.desktop`, `x-scheme-handler/https` gives the browser, `xdg-open https://example.org` opens it.
- [ ] `heiss-gtk-audit` output and screenshots of GTK apps in Dark and Light; portal color-scheme follows the theme.
- [ ] `heiss theme sync` log and screenshots (Konsole, kitty, launcher icon) on theme switch, Dark and Light. From `docs/design/THEME-SYNC.md`: the path unit fires on a theme switch; `busctl` reaches plasmashell, kded and the portal; the Konsole D-Bus names and `Session.setProfile` work; kitty finds `/etc/xdg/kitty/*.auto.conf`; Plasma's automatic light/dark switching.
- [ ] Dock screenshot, running installer in the dock, Kickoff menu (clean launcher) in Dark and Light; icons; Dolphin and the pinned file manager icon; every item marked "to verify" in `docs/design/AUDIT.md`; where the contrast pairs appear on screen (`docs/design/STYLE-GUIDE.md`).
- [ ] Launcher (`docs/apps/LAUNCHER.md`): no name collisions after translation (ru); the NoDisplay state of print-manager, cups, firefox and spectacle read from the installed packages; hiding mpv and vim does not damage the "Open With" lists in Dolphin.
- [ ] From `docs/apps/RESEARCH.md`: klipper is needed for the clipboard applet; Discover lists drivers; a wireshark group decision for dumpcap; haruna theme fit and codecs.
- [ ] Unpack the built ISO once and record the real Plasma, KWin and Calamares versions (only the repository database was read so far).
- [ ] Plasma shortcut list (`~/.config/kglobalshortcutsrc`, or System Settings, Shortcuts) from the VM compared with `docs/design/SHORTCUTS.md`; no `/etc/xdg/kglobalshortcutsrc` change before that list exists.
- [ ] "Open terminal here" behaviour per `docs/apps/TERMINAL-HERE.md`.
- [ ] After the 37 removed packages (PR 49): ISO boots, installs, `systemctl --failed` is empty.
- [ ] Not done: Dolphin Places defaults, kitty and Thunar terminal configuration.

### Phase 5: Welcome wizard, repository in the installed system
- [ ] Helper unit hardening: on an installed system run a real Apply that installs and removes a package (with a hook, for example a font or icon package), a snapper snapshot and `grub-mkconfig` through the Control Center / expect each to finish as before; `systemctl status heiss-helper` and `journalctl -u heiss-helper` show no `Operation not permitted` or `Address family not supported`; `systemd-analyze security heiss-helper.service` shows the new options as set; also try a hook that starts bwrap or unshare, if any package in the profiles has one (to decide on `RestrictNamespaces`). `[multilib]` stays unsupported. The same run covers `PrivateTmp` and `ProtectHome` (a hook must not fail on `/tmp` or `/home`). If an operation fails, drop the option named in the journal and record it in DECISIONS.
- [ ] Apply with the allowlisted environment: on an installed system run a real Apply from the Welcome wizard (`heiss-welcome --force`) and a saved action from the Control Center ("Apply saved actions now") / expect the system password prompt (polkit agent) to appear, the steps `[n/m] ...` to run and the apply to finish, exactly as before; if the prompt does not appear or the step list is empty, a variable the child needs is missing from the allowlist: report which (first suspect `XDG_DATA_DIRS`, then `XDG_CONFIG_DIRS`, `SHELL`). Never run here against the real helper.
- [ ] Layout vs offscreen PNGs (`scripts/render-gui.py`): run `heiss-welcome --force` in the VM in Dark, Light and ru / expect no clipped text, Back and Next visible on every step (also the hardware step), the progress bar sand on a dark track, the Applying screen with a sliding bar. Not covered by the render: the real polkit prompt, threads, animation smoothness.
- [ ] Wizard screens (welcome, profile, level, add-ons, hardware, appearance, privacy, software, backups, summary, applying, done) in Dark, Light and Russian: screenshots; layout, focus ring, Alt+Left, Inter font, error colour contrast on Light.
- [ ] Hardware screen in VirtualBox shows the guest-tools proposal; the privacy screen shows only the firewall as "In place".
- [ ] Hardware choices (5f): ticking the VirtualBox guest tools and applying installs `virtualbox-guest-utils` and enables `vboxservice.service`; a later profile change keeps them (sticky rule); NVIDIA is never ticked by default, its plan prints the kernel-parameter note and the driver path was never run (black-screen risk); `grub-mkconfig` and `mkinitcpio` post-actions run and a failure of `grub-mkconfig` (no /boot/grub) is reported; detection on the GUI thread when the hardware screen was skipped does not freeze the window.
- [ ] Theme (5g): choosing Dark and Light on the appearance screen switches the desktop at once with `plasma-apply-lookandfeel`, the wizard recolours, theme-sync reacts; Automatic changes nothing; a failure shows the note.
- [ ] Privacy 3c, Enhanced: choose Enhanced in the wizard and Apply, enter the polkit password / expect `/etc/NetworkManager/conf.d/80-heiss-privacy.conf` with `wifi.cloned-mac-address=stable`, and `~/.config/kscreenlockerrc` group `Daemon` with `Autolock=true`, `Timeout=3`, `LockGrace=5`.
- [ ] Privacy 3c, Maximum: apply Maximum, run `sudo systemctl restart NetworkManager`, then `nmcli -f 802-11-wireless.cloned-mac-address connection show <name>` and `ip link` / expect a random Wi-Fi MAC (and `Timeout=1`, `LockGrace=0`); a connection profile with its own cloned MAC keeps it; on a captive-portal network expect it may fail.
- [ ] Privacy 3c, screen lock: after Apply (re-login if needed) leave the session idle for the chosen time / expect the screen locks after 3 (Enhanced) or 1 (Maximum) minutes.
- [ ] Privacy 3c, lowering: apply Standard again / expect `preserve` in the drop-in and `Timeout=5`, `LockGrace=5`.
- [ ] Privacy 3c, screen: open the privacy screen in en and ru / expect firewall, Wi-Fi MAC and screen lock marked "In place", and DNS over TLS, VPN, Bluetooth off, linux-hardened marked "Coming soon".
- [ ] Privacy 3c, helper: `heiss profile apply --privacy=enhanced --yes` through the helper / expect success; run `python3 -m unittest discover -s helper/tests` where python-gobject is installed / expect the 10 skipped D-Bus tests to pass.
- [ ] Privacy 3c, user keys: `kwriteconfig6` writes `kscreenlockerrc` as the user during Apply / expect the keys present afterwards.
- [ ] Apply: plan preview, polkit prompt, progress, success, failure with Try again, Save for later (also re-check after the isolation fix: the installed wizard's plan and Apply still start, since the child now runs `python -I` in `/` without `PYTHON*`/`HEISS_*` variables); the signal from the worker thread to the GUI works; the window refuses to close while applying.
- [ ] `pyside6` 6.12 runs the QML; ISO size change after adding `pyside6` (52 MiB installed per `pacman -Si`); `kirigami` is not needed by the Control Center (DECISIONS.md 2026-11-13).
- [ ] Autostart: the wizard does NOT start in the live session (`/run/archiso` present) and starts once after the first login on the installed system.
- [ ] `heiss-cleanup.sh` imports the Heiss key and appends `[heiss]` on a real installation; `pacman -Sy` then works; Calamares' unpackfs copies `/usr/share/pacman/keyrings/heiss.gpg` into the target.
- [ ] ISO build order: `scripts/heiss-packages-build.sh` before `heiss-build.sh` (the keyring and welcome packages come only from `~/localrepo`).
- [ ] Wizard text as plain text: open every wizard screen in en and ru / expect everything to look as before (fonts, wrapping, colours); the apply log and error line show a literal `<` or `&` as typed, never as formatting.
- [ ] Existing installer items still unchecked: slideshow animation, glow via QtQuick.Effects, the users page logo animation, mouse selection on the desktop under VirtualBox.

### Phase 6: Control Center
- [ ] Layout vs offscreen PNGs (`scripts/render-gui.py`): open heiss-control in the VM in Dark, Light and ru, every page and the smallest window (640x420) / expect no clipped or overlapping text, accent buttons dark on sand (Dark) and light on brown (Light), the About link labels not touching their URLs. Differences expected and to report: real Plasma colours; the font (Inter is in the ISO via `inter-font` since round 22: report it if a fallback face still shows). Not covered by the render: clipboard, worker threads, animation.
- [ ] Control Center shell (`PYTHONPATH=core:control python -m heiss_control`, needs `pyside6`): the window opens; sidebar lists 11 pages; Overview shows profile, privacy level, package count, pending actions and kernel; About shows system, build, kernel, Plasma and links (a click opens the browser); unbuilt pages say "Coming soon". Screenshots in Dark, Light and ru; keyboard control (Tab, Enter, Esc clears the search); the QML has only been linted (`qmllint`), never run.
- [ ] Control Center package, install: run `scripts/heiss-packages-build.sh`, build the ISO, boot it, open Kickoff and search "Heiss" / expect "Heiss Control Center" under Settings with the stock `preferences-system` icon (check in Dark and Light), and no `heiss-control` window on the live desktop.
- [ ] Control Center package, start: click the Kickoff entry, then run `heiss-control` in Konsole / expect the same window both times, with its taskbar entry grouped under the launcher entry (`StartupWMClass=heiss-control`).
- [ ] Control Center package, dock: look at the dock / expect the pins unchanged (Dolphin, Konsole, System Settings, Firefox).
- [ ] Control Center, Profiles page: after the wizard's Apply, open "Profiles and software" / expect the chosen and applied profile names, the add-ons, and the lists of packages, services and Flatpak apps Heiss OS installed (compare with `/var/lib/heiss/state.json`); a profile saved for later shows under pending actions as "waiting"; in ru the names are Russian.
- [ ] Control Center, Appearance page: open "Appearance" / expect the current scheme shown; click Light, then Dark / expect the whole desktop to switch, the window not to freeze (progress bar), the marked button to follow, and the theme-sync log to show a run; with another colour scheme set by hand expect "unknown" and no marked button; with `plasma-apply-lookandfeel` missing expect the error text, not a crash.
- [ ] Control Center, plain text: put a package name like `<img src=http://example.invalid/x.png><b>x</b>` into the packages list of a test copy of `/var/lib/heiss/state.json`, open "Profiles and software" / expect the literal text on screen, no bold, no image and no network request; a very long error text is cut at 300 characters.
- [ ] Control Center, optional dependencies: on the ISO run `pacman -Q kconfig plasma-workspace` / expect both installed; after `heiss-control` goes from pkgrel 1 to 3 open the Appearance page / expect the current scheme shown, not "unknown".
- [ ] Control Center, Advanced page: open "Advanced", click "Open System Settings" / expect the stock KDE settings window, the Control Center window stays usable; click "Run the check" / expect the progress bar, then one line per item (OK, WARN, FAIL) matching `heiss check` run in Konsole on the same machine, and the button works again; with `systemsettings` missing expect the error text; click "Run the check" while the Appearance switch is still running / expect the theme-sync item to show WARN (the check shares the theme-sync lock file in `$XDG_RUNTIME_DIR` or `~/.local/state/heiss`), and the normal result on a rerun after the switch has finished.
- [ ] Control Center, systemsettings: on the ISO run `pacman -Q systemsettings` / expect it installed (it is only an optional dependency of `heiss-control`; if it is missing the button shows the error text); click "Open System Settings" on the Advanced page / expect the stock settings window.
- [ ] Control Center, Security Center: open "Security Center" / expect five cards (firewall, disk encryption, Secure Boot, SSH, open network ports) after a moment, each with plain text, "Look at this" ones with advice; compare with `systemctl is-active firewalld`, `lsblk -s` and `ss -ltn`; in Russian all texts are Russian; the summary line has no score.
- [ ] Control Center, Security Center, firewall: `sudo systemctl stop firewalld`, click "Check again" / expect the firewall card to say it is off, with advice; `sudo systemctl enable --now firewalld`, click again / expect OK.
- [ ] Control Center, Security Center, SSH: with sshd stopped expect the SSH card OK; `sudo systemctl start sshd`, click "Check again" / expect "Look at this" (and port 22 under open ports); stop it again / expect OK.
- [ ] Control Center, Security Center, Secure Boot: in a BIOS VM expect "BIOS mode"; on UEFI with Secure Boot off expect the "off" text as information, not a warning; with Secure Boot on expect "Secure Boot is on" (never tested: the build host is BIOS).
- [ ] Control Center, Security Center, encrypted root: install Heiss OS with disk encryption (if the installer offers it; not verified that it does), boot, open "Security Center" / expect the disk card to say the disk is encrypted (OK) and `lsblk -s -r -n -o TYPE -- "$(findmnt -n -o SOURCE /)"` to print a `crypt` line; on an unencrypted install expect "Look at this". The `crypt` branch has only run against a fake `lsblk` answer.
- [ ] Control Center, saved actions: in the wizard choose a profile and "Save answers, apply later" (or apply while offline), open "Profiles and software" / expect the item listed as waiting; click "Apply saved actions now" while offline / expect the offline text and nothing started; while an apply runs, save another action in the wizard (or remove one in a second Control Center window) / expect the new item to be in the list and in `~/.config/heiss/pending.json` after the run ends and a removed one not to come back (the lock and merge, never run on a real system); run it from the installed packages: from a source checkout with `PYTHONPATH` the Apply click fails by design (`python -I`); after the pkgrel 7 filter widening the polkit password prompt must still appear and the helper call succeed (the child no longer gets `GI_*`, `G_*`, `GSETTINGS_*`, `DBUS_SYSTEM_BUS_ADDRESS`); online, click it / expect the polkit password prompt, the step lines, the item to leave the list and the "applied" text, and `heiss profile show` / `/var/lib/heiss/state.json` to match; make the apply fail (for example hold the pacman lock, or dismiss the polkit password prompt) / expect the item to stay as failed with a message and a second click to retry; "Remove" drops an item without installing anything.
- [ ] Control Center, Network and privacy: after applying Enhanced in the wizard, open "Network and privacy" / expect the level "Enhanced", the Wi-Fi card "fixed made-up MAC per network" (OK), the screen lock "3 minutes" (OK) and the firewall state; change `Timeout` by hand in System Settings, click "Check again" / expect "Look at this" on the screen lock with advice; in Standard on a fresh install expect all OK (defaults); with no level chosen expect the "no level chosen" text and no warnings; in Russian all texts are Russian; the four "coming soon" items are listed.
- [ ] Control Center, Network and privacy, other states: apply Maximum / expect the Wi-Fi card "Every connection gets a new random MAC address ..." (OK) and the screen lock "after 1 min." (OK); switch off automatic screen locking in System Settings and click "Check again" / expect "Look at this" on the screen lock; as root delete `/etc/NetworkManager/conf.d/80-heiss-privacy.conf` and click again with Enhanced chosen / expect "Look at this" on the Wi-Fi card (connections keep the hardware MAC).
- [ ] Control Center, screen-lock defaults: on a fresh Plasma with no `kscreenlockerrc`, run `kreadconfig6 --file kscreenlockerrc --group Daemon --key Timeout --default 5` and the same for `LockGrace --default 5` and `Autolock --default true`, and compare with `/usr/share/config.kcfg/kscreenlockersettings.kcfg` / expect 5, 5 and true (that is what the page treats as the Standard level); on a fresh install in Standard expect the screen-lock card to be OK.
- [ ] Control Center search: typing "wireguard" lists Network and privacy; "брандмауэр" in ru lists the Security Center; an empty result shows the "nothing found" text.
- [ ] Overview, pending actions: put one entry in the pending queue ("Save answers, apply later" in the wizard), open the Control Center / expect the pending-actions card to show 1 and "1 waiting".
- [ ] Overview on an installed system after Apply: profile and privacy level match what the wizard applied; `plasmashell --version` is parsed on the real Plasma.

- [ ] Control Center, Updates and snapshots: open "Updates and snapshots" / expect four cards (updates waiting, last system update, restart, snapshots); compare with `pacman -Qu | wc -l`, the last `starting full system upgrade` line of `/var/log/pacman.log` and `findmnt -n -o FSTYPE /`; on the ext4 install expect "no snapshots" as information, not a warning; in Russian all texts are Russian.
- [ ] Control Center, Updates and snapshots, restart: `sudo pacman -Syu` with a new kernel, click "Check again" before rebooting / expect the restart card "Look at this"; after a reboot expect OK (never run: the check is `/usr/lib/modules/$(uname -r)` missing).
- [ ] Control Center, Updates and snapshots, waiting: with updates waiting expect the count and advice; after `sudo pacman -Syu` and "Check again" expect "none"; the page must make no network request (compare with `ss`/a firewall log while opening it).
- [ ] Control Center, Updates and snapshots, locked database: in Konsole run `sudo pacman -Syu` and stop at the confirmation prompt, then click "Check again" / expect the updates card "unknown" (not "none"); answer n, click "Check again" / expect the count or "none".
- [ ] Control Center, Updates and snapshots, long log: on a system whose `/var/log/pacman.log` is over 256 KiB with the last "starting full system upgrade" line before the final 256 KiB (`tail -c 262144 /var/log/pacman.log | grep -c 'starting full system upgrade'` prints 0), open the page / expect the last-update card "unknown", not "never".
- [ ] Control Center, Updates and snapshots, old update: with a last upgrade line older than 30 days (a test copy of the log, or a VM not updated for a month) / expect the last-update card "Look at this"; a fresh install shows the date as information.
- [ ] Control Center, Updates and snapshots, snapshots (after the Btrfs/snapper phase exists): on Btrfs with `/etc/snapper/configs/root` expect "set up"; on Btrfs without it expect "not set up"; `findmnt -n -o FSTYPE /` shows the type the card names.
- [ ] Control Center, Hardware and drivers: open "Hardware and drivers" on real hardware and in VirtualBox / expect the computer type, processor, graphics (vendor names and `vendor:device` ids matching `lspci -nn`), Bluetooth, the matching driver proposals with Installed / Can be installed, and the report; compare with `heiss hw detect`; in Russian the names and texts are Russian.
- [ ] Control Center, Hardware and drivers, report: click "Copy the report" and paste it into a text editor / expect the text on screen, "Copied." shown, and no hostname, user name, serial number, MAC address or PCI slot in it; the clipboard copy through Qt has never run.
- [ ] Control Center, Hardware and drivers, driver state: in VirtualBox expect `vm-virtualbox` Installed only after the guest tools are installed; `sudo pacman -R` one package of a proposal and click "Check again" / expect "Can be installed" (neutral colour, not red) with the missing package named; with a laptop expect `laptop-power`; NVIDIA/hybrid detection on real hardware is untested (only fixtures).
- [ ] Control Center, Hardware and drivers, report rules: on a custom kernel whose release has characters outside `[0-9A-Za-z.+_-]` or is over 40 characters, click "Check again" and "Copy the report" / expect `kernel: other` and no hostname in the report (a report over 8000 characters ends with `[truncated]`; never seen on a real machine).

### Phase 7: hardware and safe fallback
- [ ] Hardware names, other CPUs: on a Hygon or Centaur machine (rare; skip if none is available) run `grep -m1 vendor_id /proc/cpuinfo` and open the wizard hardware step / expect "Hygon" or "Centaur" and no raw vendor string; on any other CPU string expect "other", never the raw text.
- [ ] Inter font in the ISO: boot the live image and run `fc-list | grep -i "Inter"` / expect a hit; compare the ISO size with the previous build and record it in DECISIONS (not measured).
- [ ] Hardware pages after the polish (round 22): in the VM, open the wizard hardware step in ru and en / expect "Процессор: Intel" (or AMD), one "Графика: ..." line with vendor names, square tick boxes, the NVIDIA hint ending with the safe-graphics recovery step, Back/Skip/Next visible and a scroll bar when the list is longer than the window; in Control Center > Hardware and drivers expect "Can be installed" (not red), the NVIDIA warning shown in full in amber, and Inter in the search field (font from `inter-font`).
- [ ] Safe-graphics entry, menu: on an installed system (BIOS and UEFI) run `sudo grub-mkconfig -o /boot/grub/grub.cfg` / expect "Found safe graphics kernel" in the output and a menu entry "Heiss OS, safe graphics (linux)" next to the normal one (the script was run only against a stub of `grub-mkconfig_lib` and a scratch `/boot`; a real `grub-probe` was not available for a real device).
- [ ] Safe-graphics entry, boot: choose "Heiss OS, safe graphics (linux)" in the GRUB menu of a VM / expect `cat /proc/cmdline` to contain `nomodeset` and `modprobe.blacklist=nvidia,...`, `lsmod | grep nvidia` to print nothing, and a login or console to appear.
- [ ] Safe-graphics entry, after the installer: install with Calamares in a VM and boot the disk / expect `grep -c 'safe graphics' /boot/grub/grub.cfg` to be at least 1 without any manual `grub-mkconfig` (Calamares runs it; `heiss-safe-graphics` is copied into the target with the other ISO packages), and the Heiss GRUB theme to look unchanged.
- [ ] Safe-graphics entry on NVIDIA hardware: with `nvidia-open` installed and the `heiss-nvidia.conf` initramfs drop-in present, the entry still reaches a login. `modprobe.blacklist=` does not stop a module that is named explicitly in the initramfs `MODULES`, so this may fail; if it does, the entry needs `rd.`-style handling or a drop-in change. Never tried on real NVIDIA hardware.
- [ ] Safe-graphics entry, Btrfs root subvolume and linux-lts: on an installed system with a Btrfs root in a subvolume (`rootflags=subvol=`), and again after `sudo pacman -S linux-lts`, run `sudo grub-mkconfig -o /boot/grub/grub.cfg` / expect one entry "Heiss OS, safe graphics (linux)" plus a second "(linux-lts)"; `grep 'safe graphics' -A8 /boot/grub/grub.cfg` shows `rootflags=subvol=<name>` on the Btrfs system, and choosing each entry boots (tests use fakes only).
- [ ] Safe-graphics entry, script environment: on the installed system run `sudo sh -n /etc/grub.d/41_heiss_safe` / expect no output; then, with `os-prober` installed and a second OS present (and again with a separate `/boot` partition), run `sudo grub-mkconfig -o /boot/grub/grub.cfg` / expect no error and the safe-graphics entries in the main menu (not in a submenu) after the normal entry (tests used the build host's `sh`; `prepare_grub_to_access_device` was never seen with a real device).
- [ ] NVIDIA warning text: in the welcome wizard and in Control Center > Hardware and drivers, open the NVIDIA proposal in en and in ru / expect the warning to name "Heiss OS, safe graphics" and `nvidia-open-lts` and not to mention DKMS; reboot and expect the GRUB entry title to match the quoted name letter for letter.

### Tooling (not a product phase)
- [ ] guards.yml without a stored token: after the merge open the first `guards` run on main, expand "Run actions/checkout" in both jobs / expect `persist-credentials: false` under `with:` and both jobs green (tokens and protected-paths). Optional: a throwaway PR step `git config --get-all http.https://github.com/.extraheader` / expect no output. No VM step applies.
- [ ] Publish with the token in the environment: after the merge, at the next push to `main` that changes a package (the `Publish to heiss-repo` step only runs when `changed == 'true'`), open the `publish-repo` run / expect the step green, a new commit on `gh-pages` by "Heiss OS CI", and no token in the log (it is masked). If the push is rejected with an authentication error, the environment form did not reach git: report the exact error. If no package changed the step is skipped: trigger it with a change under `packages/` (for example a pkgrel bump in a later PR); a skip is not a pass. Only the masked log is checked, `ps` exposure is not measured. Not run here (needs the real secret).
- [ ] Calamares build with the pin: in the build VM run `scripts/heiss-calamares-build.sh` / expect "==> https://aur.archlinux.org/calamares.git at 167151be..., PKGBUILD sha256 8ea0869d...: as reviewed", then the layout-patch step printing a `grep -n` line with `heiss-layout.patch` inside `build()` (the anchor `local _pkgsrc_dir=` was read in the pinned PKGBUILD but the patch was never applied or built here; if the step prints nothing and the script stops, the anchor is missing: a failure), then a pacman prompt before build dependencies (no `--noconfirm`), and the package in `~/localrepo`.
- [ ] Installer from that package: boot the ISO built with it in the VM / expect the Calamares sidebar narrow (56 px) and Back/Next/Cancel evenly spaced, as before.
- [ ] Pin failure path: in a copy of the script change one hex digit of `CALAMARES_AUR_COMMIT` / expect "not in ... (rewritten history?): do not build", exit 1 and no `~/aur/calamares`; restore it, change one digit of `CALAMARES_PKGBUILD_SHA256` / expect "PKGBUILD sha256 is <real>, expected <changed>", exit 1 and no `~/aur/calamares`.
- [ ] Unattended build: in a throwaway VM run the script with `HEISS_NONINTERACTIVE=1` / expect no pacman prompt.
- [ ] Drop-in allowlist: on an installed system run an Apply that writes the zram drop-in, a privacy level (`/etc/NetworkManager/conf.d/80-heiss-privacy.conf`) and the NVIDIA proposal's `/etc/mkinitcpio.conf.d/heiss-nvidia.conf` / expect each file to appear and `journalctl -u heiss-helper` to show no "drop-in not declared" or "bad drop-in path"; `ls /etc/sudoers.d /etc/pam.d` shows nothing new from Heiss.
- [ ] Theme-sync lock: on an installed system with a normal login run `ls -l $XDG_RUNTIME_DIR/heiss-theme-sync.lock` after a theme switch / expect mode `-rw-------` owned by you and no `/tmp/heiss-theme-sync.lock`; run `heiss theme sync --no-wait & heiss theme sync --no-wait; wait` / expect one run to print "another theme sync is running" and no error; run `XDG_RUNTIME_DIR= heiss theme sync --no-wait` / expect `~/.local/state/heiss/heiss-theme-sync.lock` with mode `-rw-------` and `ls -ld ~/.local/state/heiss` showing `drwx------`; also switch the theme from the Control Center Appearance page (the path unit runs the sync) and expect the theme-sync log to show a run with no error.
- [ ] Dock lock: on a fresh live or installed first login `ls -l ${XDG_RUNTIME_DIR:-$HOME/.cache}/heiss-dock.lock` / expect the file there, no `/tmp/heiss-dock.lock`, and the dock still set up (marker `~/.config/heiss-dock-set`, `~/.cache/heiss-dock.log` without errors). Then run `XDG_RUNTIME_DIR= sh -c 'exec 9>"${XDG_RUNTIME_DIR:-$HOME/.cache}/heiss-dock.lock"'` / expect `~/.cache/heiss-dock.lock` and no `/tmp/heiss-dock.lock`.
- [ ] Safe-graphics entry, hostile values: on an installed system add `GRUB_CMDLINE_LINUX="quiet foo=bar"` to `/etc/default/grub` (and, in a second try, a parameter with a `$` or a `'`), run `sudo grub-mkconfig -o /boot/grub/grub.cfg` / expect no error, the entry "Heiss OS, safe graphics (linux)" present with `quiet foo=bar nomodeset ...` and, for the odd parameter, a backslash before the odd character in `grep -A8 'safe graphics' /boot/grub/grub.cfg`; boot the entry and expect `cat /proc/cmdline` to show the parameter without the backslash. On a Btrfs root with a subvolume name containing a space expect the same.
- [ ] Pinned actions: open the Actions tab for the first run of `core` and `publish-repo` after the merge of "fix/pin-actions-checkout" / expect both green with `actions/checkout@11d5960a...` shown in the log; on the next `actions/checkout` release choose a new SHA by hand (`gh api repos/actions/checkout/git/ref/tags/<tag>`) and change the comment together with it. `guards.yml` (Tier A) is pinned too (PR "ci/pin-guards-checkout"); `core/tests/test_workflows.py` has an empty PENDING_OWNER_APPROVAL set for future exceptions. After the merge open the first `guards` run on main / expect both jobs green, `actions/checkout@11d5960a...` in the log and "protected files unchanged". No VM step applies.
- [ ] Run `security-reviewer` in a new session on a diff that touches `helper/` (for example a copy of a past helper change) / expect findings that each name file and line, the attacker kind, the exact attacker action and the fix, a severity from the rubric, a `Variants searched:` line and a `Verdict:` line; `git status` stays clean afterwards. (Round 22 part 2: only one audit run has checked that the new text finds more.)
- [ ] In a new Claude Code session run `/agents`: `reviewer`, `security-reviewer`, `qa-verifier` and `docs-keeper` are listed; invoke each on a small diff and expect a findings list and a `Verdict:` line, and `git status` stays clean afterwards (they must not change files).
- [ ] After the first merged PR that follows the new rules: the final report carries the line `агенты: reviewer ok, security ok, qa ok, docs ok` (`n/a` for an agent that PR did not need) and the PR text has an "automated review" block that lists each agent's result and which findings were fixed.

## Round 20, item 3a (2026-11-11): hardware choices applied

PR "feat/apply-hardware-choices": `--hardware` on `heiss profile apply|diff`, resolver support with the sticky rule, wizard passes the ticked proposals, strings updated, tests (`core/tests/test_hardware_apply.py`, `welcome/tests/test_apply.py`). Not verified: see the new Phase 5 line in the FINAL VM TEST LIST. Next: 3b theme, 3c privacy level (MAC randomization, screen lock), then Phase 6.

## Round 20, item 3b (2026-11-11): theme choice applied

PR "feat/apply-theme-choice": `welcome/heiss_welcome/theme.py`, view-model hook, note on the appearance screen, CI check that plasma-workspace ships `plasma-apply-lookandfeel`, tests. Not verified: see the new Phase 5 line. Next: 3c privacy level (MAC randomization, screen lock).

## Round 20, subagents (2026-11-11)

PR "chore/more-agents": `.claude/agents/security-reviewer.md`, `qa-verifier.md`, `docs-keeper.md`, rules in `CLAUDE.md`, `core/tests/test_agents.py` (front matter, unique names, read-only tools, no tabs). Not verified: the definitions have not been run by Claude Code as registered subagents yet (they are only picked up in a new session); this PR used them as written instructions. Next: step 3c, privacy level.

## Round 20, item 3c (2026-11-11): privacy level applied

PR "feat/apply-privacy-level": `core/heiss_core/privacy.py`, `--privacy` on `heiss profile apply|diff`, helper method `WritePrivacy` (documented in `docs/SECURITY-MODEL.md`), wizard passes the level, privacy screen marks Wi-Fi MAC and screen lock as in place, tests (`core/tests/test_privacy.py`, helper and welcome tests). Not verified: see the new Phase 5 line in the FINAL VM TEST LIST (nothing ran on a real system; key names were read from the man pages and the shipped kcfg). Still "Coming soon": DNS over TLS, VPN/WireGuard, Bluetooth off, linux-hardened. Next: Phase 6 (Control Center) after the owner's reply.

## Phase 6, step 1 (2026-11-13): Control Center shell

PR "feat/control-center-shell": `control/` (model without Qt, PySide6 glue, one QML window), `docs/CONTROL-CENTER.md`, tests in CI. Read-only: Overview and About are built, search covers page titles and keywords, the other nine sidebar pages say "Coming soon". No package, desktop file or ISO entry yet. Not verified: any run of the window (no `pyside6` here; the QML only passed `qmllint` with the same warning classes as the wizard). Owner question: licence of `branding/` for the About page. Next: Profiles and software and Appearance pages (with the package and desktop file), then the security and system pages.

## Phase 6, step 2 (2026-11-13): Control Center package

PR "feat/control-center-package": `packages/heiss-control`, `control/data/heiss-control.desktop`, entry in `profile/packages.x86_64`, build script archives `control/`, tests. Not verified: a real ISO build and the launcher entry in Kickoff (final VM test list, Phase 6). `pyside6` is already in the ISO via the wizard, so there is no new runtime dependency. The new cases in `core/tests/test_packages.py` ran (221 core tests OK) and `makepkg` was run locally with the package contents listed. Next: Profiles and software (read-only) and Appearance pages.

## Phase 6, step 3 (2026-11-13): Profiles and Appearance pages

PR "feat/control-center-profiles-appearance": read-only Profiles and software page, Appearance page (Dark and Light only, switched as the user on a worker thread), `control/heiss_control/theme.py`, tests, heiss-control pkgrel 2. Not verified: any run of the window (no `pyside6` here), the real `plasma-apply-lookandfeel` and `kreadconfig6` calls, the worker-thread signal; see the two new Phase 6 lines in the FINAL VM TEST LIST. The new CI step (`kreadconfig6` shipped by `kconfig`, needs `pacman -F`) runs for the first time in this PR's CI; it was not run locally. The wizard QML (`welcome/heiss_welcome/qml/Main.qml`) used the default `Text` format for strings from files and commands; the same fix is a separate PR, branch `fix/wizard-plain-text`, not in this PR. Not done: changing the profile or add-ons (needs the helper), the pending-queue runner, "Automatic" theme, accent, wallpapers, fonts, density, animations. Next: the security and system pages (Security Center, Updates and snapshots, Network and privacy, Advanced), or the profile change through the helper, after the owner's reply.

## Phase 5 follow-up (2026-11-13): wizard QML plain text

PR "fix/wizard-plain-text": all 14 `Text` items of `welcome/heiss_welcome/qml/Main.qml` are `Text.PlainText`, test added, heiss-welcome pkgrel 5. Not verified: the wizard window with the change (no `pyside6` here; the QML only passed `qmllint`). The existing wizard screenshot item in the FINAL VM TEST LIST covers it: text must look as before.

## Phase 6, step 4 (2026-11-13): Advanced page

PR "feat/control-center-advanced": `control/heiss_control/tools.py`, Advanced page (stock System Settings, `heiss check` on a worker thread), tests, heiss-control pkgrel 3. Verified by a real run on the build host (not a Heiss system): `tools.run_check()` returned its eight items (2 OK, 2 WARN, 4 FAIL: no state file, no helper files, hide stubs and live packages present) as expected for a non-installed system. Not verified: the window and the worker-thread signal (no `pyside6` here), `systemsettings` starting, the check on an installed system. Not done: journal, services, Heiss logs, bug-report bundle (need decisions on what may leave the machine). Next: Security Center, Updates and snapshots, Network and privacy, or profile change through the helper, after the owner's reply.

## Phase 6, step 5 (2026-11-13): Security Center page (read-only)

PR "feat/control-center-security": `control/heiss_control/security.py` (firewall, disk encryption, Secure Boot display, SSH, open ports), page with plain-language advice, 79 control tests, heiss-control pkgrel 4. Verified by a real run of `security.collect()` on the build host (firewall off, disk not encrypted, BIOS mode, sshd on, port 22 open: each matched the host). Not verified: the window and the worker thread (no `pyside6` here), UEFI and Secure Boot (build host is BIOS), an encrypted root (never tested; only a fake `lsblk` answer), an installed Heiss system. Not done: fixes, snapshots, score, `lynis`/`arch-audit`, root-lock check, pending updates. Next: Updates and snapshots, Network and privacy, or the profile change through the helper, after the owner's reply.

## Phase 6, step 6 (2026-11-13): saved actions

PR "feat/control-center-pending": the Profiles page runs or removes the actions the wizard saved ("apply later"): `control/heiss_control/runner.py` (child process `heiss profile apply --yes`), offline refusal, one run at a time, step lines, retry after a failure; 96 control tests; heiss-control pkgrel 6 (5 before the security fixes). Not verified: the window and the worker thread (no `pyside6`), a real apply through the helper and polkit from this window (the runner was tested with a fake command only), the offline detection via `nmcli` on a real machine. Security review fixes in the same PR: the child runs isolated (`-I`, cwd `/`, no `PYTHON*`/`LD_*`), the queue is locked and merged on save, ids matched with `fullmatch` in core; heiss-core pkgrel 8, heiss-control 6. The same weakness in the wizard's `CliApplier` is fixed by PR "fix/wizard-apply-isolated" (see below). Not done: privacy level and hardware choices from the queue, moving the runner into `heiss_core`. Next: Updates and snapshots, Network and privacy, or the profile change through the helper, after the owner's reply.

## Phase 5 follow-up (2026-11-13): wizard Apply isolated

PR "fix/wizard-apply-isolated": `welcome/heiss_welcome/applier.py` starts `python -I -m heiss_core` in `/` with a cleaned environment (plan and Apply), tests with a fake child that reports its cwd and environment, heiss-welcome pkgrel 6; the security review also widened the filter (`GI_*`, `G_*`, `GSETTINGS_*`, `DBUS_SYSTEM_BUS_ADDRESS`) in both places, including `control/heiss_control/runner.py` (heiss-control pkgrel 7). Not verified: that the Control Center's Apply and the wizard's Apply still reach the helper with the widened filter (no `G_*`/`GI_*` variable should be needed by the polkit agent or the D-Bus client; never run on a real system); a real apply from the wizard through the helper and polkit (the existing Phase 5 Apply item in the FINAL VM TEST LIST covers it; it must still work from the installed `heiss-welcome` after this change), the window (no `pyside6` here). Next: Updates and snapshots, Network and privacy, or the profile change through the helper, after the owner's reply.

## Phase 6, step 7 (2026-11-13): Network and privacy page (read-only)

PR "feat/control-center-privacy": `control/heiss_control/privacy_view.py`, the page (chosen level vs. Wi-Fi MAC drop-in, screen-lock keys and firewall, coming-soon list), shared fact-card QML component, 111 control tests, heiss-control pkgrel 8. Verified by a real run of `privacy_view.collect()` on the build host (no drop-in, `kreadconfig6` missing so the lock is "could not be read", firewall off). Not verified: the window and worker thread (no `pyside6`), `kreadconfig6` on a real Plasma, an installed system with a level applied. Not done: changing the level (profile-change PR), DNS over TLS, VPN, Bluetooth, linux-hardened (listed as coming soon), the live NetworkManager value. Next: Updates and snapshots, or the profile change through the helper, after the owner's reply.

## Phase 6, step 8 (2026-11-14): Updates and snapshots page (read-only)

PR "feat/control-center-updates": `control/heiss_control/updates_view.py` (updates waiting, last system update, restart needed, snapshots set up), the page, shared fact-card component, strings en/ru, tests, heiss-control pkgrel 9. Verified by a real run of `updates_view.collect()` on the build host (no updates, last upgrade date matched the pacman log, no restart needed, ext4 so no snapshots). Not verified: the window and worker thread (no `pyside6`, no `qmllint` here), Btrfs and snapper states (build host is ext4, only fakes), a pending-update count, the restart check after a real kernel update; see the three new Phase 6 lines in the FINAL VM TEST LIST. Not done: update and rollback buttons, snapshot list, Arch news, firmware (fwupd). Next: Phase 7 (hardware and drivers) after this PR is merged.

## Phase 7, step 1 (2026-11-14): Hardware and drivers page (read-only) and driver doctor report

PR "feat/control-center-hardware": `control/heiss_control/hardware_view.py` (facts, driver state per proposal, report without personal data), the page with a Copy button, strings en/ru, tests (fixtures of every detection case), heiss-control pkgrel 10. Verified by a real run of `hardware_view.collect()` on the build host (a VirtualBox VM: form factor vm, `vm-virtualbox` proposal installed) and on the hybrid-laptop fixture. Not verified: the window, worker thread and clipboard (no `pyside6` here), real hardware (GPU, hybrid, Broadcom), the report pasted from the window; see the four new lines under Phase 6 (Hardware and drivers) in the FINAL VM TEST LIST. Not done in Phase 7: snapshot before driver changes, safe-graphics boot entry and LTS fallback (needs a size measurement and the owner's decision), install-time detection (Calamares step, Tier A), driver install from the page (helper), themed hardware settings (display, audio, camera, Bluetooth, printers, input, power), the Hardware check view with simple tests. Next: the safe fallback and snapshot-before-driver-change design, after this PR is merged.

## Phase 7, step 2 (2026-11-14): safe fallback design (docs only)

PR "docs/phase-7-safe-fallback": `docs/hardware/SAFE-FALLBACK.md` (problem, what would be built, four questions for the owner). No code. Package facts (linux-lts 155.46 MiB download, nvidia-open-lts exists) read with `pacman -Si`; the pacman file database is not synced here, so whether `nvidia-utils` blacklists nouveau and what `grub-mkconfig` generates are NOT VERIFIED (also stated in the document). No FINAL VM TEST LIST line yet: nothing is built; the PR that builds the grub.d package adds them. Recommended answers: 1 A, 2 A, 3 A, 4 A. Found: the NVIDIA profile warning promises a safe graphics boot entry that does not exist. Waiting for the owner's answers to questions 1-4 in the document. Next: the grub.d package and warning text fix, after the answers.

## Phase 7, step 3 (2026-11-15): safe-graphics boot entry and NVIDIA warning text

Owner's answers to `docs/hardware/SAFE-FALLBACK.md`: 1 A, 2 A, 3 A, 4 A. PR "feat/phase-7-safe-graphics" is step (1) and (2) of the agreed order: new package `heiss-safe-graphics` (`packages/heiss-safe-graphics`, installs `/etc/grub.d/41_heiss_safe`, listed in `profile/packages.x86_64`, no Calamares or `heiss-cleanup.sh` change), warning text of `hardware/gpu-nvidia-open.toml` corrected (names the real entry, `nvidia-open-lts` instead of "DKMS"), heiss-core pkgrel 9, tests `core/tests/test_safe_graphics.py`. Verified: the script run against a stub library and a scratch `/boot` (15 tests, including the Btrfs subvolume branch, the linux plus linux-lts pair, glob characters in `GRUB_CMDLINE_LINUX` and the absence of any environment override of `/boot`), once against the real `/usr/share/grub/grub-mkconfig_lib` (menu text correct; `grub-probe` could not open a fake device), `makepkg` of the package (one file, mode 755 in `etc/grub.d`). Not verified: see the seven new lines under Phase 7 in the FINAL VM TEST LIST (real `grub-mkconfig`, booting the entry, NVIDIA hardware, UEFI). Not done: `linux-lts` and `nvidia-open-lts` installed together with the NVIDIA driver (answer 2 A), the confirmation step and "only offered if the entry is installed" (answer 3 A, step 3 of the order), "Remove this driver" through the helper (step 4). Next: step 3 of the SAFE-FALLBACK work order (confirmation in the wizard and the Hardware page).

## Round 21, part 1 (2026-11-15): GUI rendered offscreen
PR "chore/gui-offscreen-check": `scripts/render-gui.py` (both apps, every page, dark and light, en and ru, fixture data, PNGs in a temporary directory), `tests/test_render_gui.py`, CI job `qml-lint`, ISO-E2E-TEST section. The ten D-Bus tests that were skipped for lack of `python-gobject` ran: 10 OK (`python3 -m unittest helper.tests.test_dbus_integration`, run on the build VM and again by the QA agent; also run in CI). The render found and fixed: the Control Center window did not load at all since #84 (`feat/control-center-hardware`) (two buttons with `id: cb`); every accent button label drew black (property named `onAccent` is read as a signal handler); progress bars used the stock blue and white; Russian link label overlapped its URL on About; the wizard's long option hints were cut at the right edge and the hardware step pushed Back and Next off an 800 px screen; the language switch had a light highlight under sand text; the search field placeholder had no colour; `undefined` assigned to `bool` in three bindings. Not fixed, owner decision: `inter-font` is not in the ISO although `kdeglobals` asks for Inter (DECISIONS 2026-11-11: optional on purpose), so the live system shows a fallback font. Checked offscreen only (from the Phase 5 and 6 lines of the FINAL VM TEST LIST): layout, wrapping and overflow of every wizard and Control Center page in en and ru, colours in both themes, empty and failed states, the smallest window. Next: Part 2 (security-reviewer method).

## Round 22 (2026-11-15): hardware pages polish
PR "fix/hardware-pages-polish", from the owner's look at the offscreen PNGs: one shared vendor-name function in heiss-core (`cpu_vendor_name`, `pci_vendor_name`, `gpu_vendor_names`) used by the wizard and the Control Center (wizard now says "Процессор: Intel" and one line "Графика: Intel и NVIDIA", PCI ids stay in the Control Center); wizard hardware choices are square tick boxes (round dots stay for choose-one lists); the hardware intro sentence has no double colon; new optional `recovery` text in a hardware profile (the wizard shows the short recovery step, the Control Center the full warning, never cut mid-sentence: limit 1200); "Не установлено" became "Можно установить" in a neutral colour and the driver warning uses the token `neutral_text` instead of red; the wizard list has a visible scroll bar and a fade at the bottom edge and tighter info lines; the search field sets its own font. `inter-font` added to `profile/packages.x86_64` (it was NOT there although the task text said so; see DECISIONS). pkgrel: heiss-core 10, heiss-welcome 8, heiss-control 12. Checked offscreen only: wording, layout, colours, scroll sign (renders of the hardware step at 1280x800 and 1024x600, the Control Center hardware and security pages, both themes, en and ru). Not verified: real fonts (Inter), real GPU hardware, the real safe-graphics boot entry. Next: Part 2 of heiss-task-26 (security-reviewer method), then Phase 7.

## Round 22, part 2 (2026-11-15): security-reviewer method
PR "chore/security-reviewer-tob": `.claude/agents/security-reviewer.md` rewritten (threat model with four attacker kinds, method, 13 checks, severity rubric, output format, audit mode), `docs/security/REVIEW-METHOD.md` (sources, no code copied or installed). The improved agent was then run once over the existing privileged code as a read-only audit; its findings are reported to the owner and fixed in separate PRs, one at a time, after this one is merged (entries follow as they are made). Not verified: that the new text makes the agent find more (one audit run only); the new agent file is read from disk, so a session started before the change may still use the old registered text. Next: audit fix PRs one at a time, then Phase 7.

## Round 22, part 2b (2026-11-15): audit fixes
First audit of the privileged code by the improved `security-reviewer`: 0 HIGH, 3 MEDIUM, 9 LOW. MEDIUM 1 (publish secrets without a GitHub Environment) is an accepted risk with a trigger, see DECISIONS 2026-11-15. Fix PRs, one at a time: (1) PR "fix/pin-actions-checkout": every `uses:` in `core.yml` and `publish-repo.yml` pinned to a commit SHA (`guards.yml` is Tier A: pinned in its own PR "ci/pin-guards-checkout", owner approved the item on 2026-11-15; the PR carries the `design-approved` label), test `core/tests/test_workflows.py`; (2) PR "fix/calamares-aur-pin": the Calamares AUR build pinned to commit `167151be...` and checked by `scripts/heiss-aur-fetch.sh`, no default `--noconfirm`, tests `core/tests/test_aur_fetch.py` (Tier A: `heiss-calamares-build.sh`, needs `design-approved`); then the LOW items (PR "fix/regex-fullmatch": `fullmatch` in the helper and manifest validators, done; `state.json` mode (PR "fix/state-file-mode": done), helper command timeout (PR "fix/helper-command-timeout": done), `persist-credentials: false` and the token off the command line (PRs "ci/workflow-credentials" for `core.yml` and `publish-repo.yml`; `guards.yml` (Tier A): PR "ci/guards-persist-credentials": done, owner approved the item, label `design-approved`), environment allowlist (PR "fix/child-env-allowlist": done), helper unit hardening (PR "fix/helper-unit-hardening": done), drop-in directory allowlist (PR "fix/dropin-dir-allowlist": done), theme-sync lock file (PR "fix/theme-sync-lock-dir": done), GRUB value quoting (PR "fix/grub-safe-quoting": done)). Not verified for (1): that the pinned action behaves as `v4` did (the PR's own CI run is the check); the SHA was taken from the GitHub API and not compared with another source.

PR "fix/dropin-dir-allowlist" (audit LOW): drop-in paths limited to three exact directories and `*.conf` names, checked in the manifest validator and twice in the helper; tests in `core/tests/test_core.py` and `helper/tests/test_helper.py` (sudoers.d, pam.d, profile.d, cron.d, subdirectory, symlinked directory); heiss-core pkgrel 12, heiss-helper pkgrel 6. Remaining LOW items: theme-sync lock file, GRUB value quoting.

PR "fix/theme-sync-lock-dir" (audit LOW): the theme-sync lock file no longer falls back to `/tmp`. It lives in `$XDG_RUNTIME_DIR` when that is an absolute path, owned by the user and not group/other writable, else in `~/.local/state/heiss` (mode 0700); opened with `O_NOFOLLOW`, checked to be a regular file of this user; with no safe place the sync runs without a lock and logs it. 9 new tests in `core/tests/test_themesync.py` (`RealLock`), heiss-core pkgrel 13. The same pattern in `heiss-setup-dock.sh` (Tier A) is fixed by PR "fix/dock-lock-dir" (owner approved). Remaining LOW item: GRUB value quoting.

PR "fix/dock-lock-dir" (audit LOW, Tier A item approved by the owner, label `design-approved`): `heiss-setup-dock.sh` lock moved to `${XDG_RUNTIME_DIR:-$HOME/.cache}/heiss-dock.lock`; `protected.sha256` regenerated; `core/tests/test_dock_lock.py` (2 tests, the lock block run with `sh` and a scratch `HOME`). No package change (the script ships in the ISO airootfs). Remaining LOW item: GRUB value quoting.

PR "fix/grub-safe-quoting" (audit LOW, the last one): `41_heiss_safe` escapes each kernel parameter, the root device, the Btrfs subvolume name and the boot directory as a GRUB word, quotes the menu-entry id, and leaves out values with a newline or non-ASCII byte (see DECISIONS); 6 new tests in `core/tests/test_safe_graphics.py` (299 core tests), `heiss-safe-graphics` pkgrel 2, checksum in the PKGBUILD updated. The audit list of round 22 part 2b is complete after this PR. Next: Phase 7 (step 3 of the SAFE-FALLBACK work order: confirmation in the wizard and the Hardware page).
