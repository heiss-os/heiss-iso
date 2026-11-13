# Plan state (checkpoint)

Read this file at the start of every session. Source plan: `heiss-master-prompt.md` (kept outside the repo, in `~/share/`).

Last updated: 2026-11-13

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
- [ ] Apply: plan preview, polkit prompt, progress, success, failure with Try again, Save for later; the signal from the worker thread to the GUI works; the window refuses to close while applying.
- [ ] `pyside6` 6.12 runs the QML; ISO size change after adding `pyside6` (52 MiB installed per `pacman -Si`); `kirigami` is not needed by the Control Center (DECISIONS.md 2026-11-13).
- [ ] Autostart: the wizard does NOT start in the live session (`/run/archiso` present) and starts once after the first login on the installed system.
- [ ] `heiss-cleanup.sh` imports the Heiss key and appends `[heiss]` on a real installation; `pacman -Sy` then works; Calamares' unpackfs copies `/usr/share/pacman/keyrings/heiss.gpg` into the target.
- [ ] ISO build order: `scripts/heiss-packages-build.sh` before `heiss-build.sh` (the keyring and welcome packages come only from `~/localrepo`).
- [ ] Existing installer items still unchecked: slideshow animation, glow via QtQuick.Effects, the users page logo animation, mouse selection on the desktop under VirtualBox.

### Phase 6: Control Center
- [ ] Control Center shell (`PYTHONPATH=core:control python -m heiss_control`, needs `pyside6`): the window opens; sidebar lists 11 pages; Overview shows profile, privacy level, package count, pending actions and kernel; About shows system, build, kernel, Plasma and links (a click opens the browser); unbuilt pages say "Coming soon". Screenshots in Dark, Light and ru; keyboard control (Tab, Enter, Esc clears the search); the QML has only been linted (`qmllint`), never run.
- [ ] Control Center package, install: run `scripts/heiss-packages-build.sh`, build the ISO, boot it, open Kickoff and search "Heiss" / expect "Heiss Control Center" under Settings with the stock `preferences-system` icon (check in Dark and Light), and no `heiss-control` window on the live desktop.
- [ ] Control Center package, start: click the Kickoff entry, then run `heiss-control` in Konsole / expect the same window both times, with its taskbar entry grouped under the launcher entry (`StartupWMClass=heiss-control`).
- [ ] Control Center package, dock: look at the dock / expect the pins unchanged (Dolphin, Konsole, System Settings, Firefox).
- [ ] Control Center, Profiles page: after the wizard's Apply, open "Profiles and software" / expect the chosen and applied profile names, the add-ons, and the lists of packages, services and Flatpak apps Heiss OS installed (compare with `/var/lib/heiss/state.json`); a profile saved for later shows under pending actions as "waiting"; in ru the names are Russian.
- [ ] Control Center, Appearance page: open "Appearance" / expect the current scheme shown; click Light, then Dark / expect the whole desktop to switch, the window not to freeze (progress bar), the marked button to follow, and the theme-sync log to show a run; with another colour scheme set by hand expect "unknown" and no marked button; with `plasma-apply-lookandfeel` missing expect the error text, not a crash.
- [ ] Control Center search: typing "wireguard" lists Network and privacy; "брандмауэр" in ru lists the Security Center; an empty result shows the "nothing found" text.
- [ ] Overview, pending actions: put one entry in the pending queue ("Save answers, apply later" in the wizard), open the Control Center / expect the pending-actions card to show 1 and "1 waiting".
- [ ] Overview on an installed system after Apply: profile and privacy level match what the wizard applied; `plasmashell --version` is parsed on the real Plasma.

### Tooling (not a product phase)
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

PR "feat/control-center-profiles-appearance": read-only Profiles and software page, Appearance page (Dark and Light only, switched as the user on a worker thread), `control/heiss_control/theme.py`, tests, heiss-control pkgrel 2. Not verified: any run of the window (no `pyside6` here), the real `plasma-apply-lookandfeel` and `kreadconfig6` calls, the worker-thread signal; see the two new Phase 6 lines in the FINAL VM TEST LIST. The new CI step (`kreadconfig6` shipped by `kconfig`, needs `pacman -F`) runs for the first time in this PR's CI; it was not run locally. Not done: changing the profile or add-ons (needs the helper), the pending-queue runner, "Automatic" theme, accent, wallpapers, fonts, density, animations. Next: the security and system pages (Security Center, Updates and snapshots, Network and privacy, Advanced), or the profile change through the helper, after the owner's reply.
