# Plan state (checkpoint)

Read this file at the start of every session. Source plan: `heiss-master-prompt.md` (kept outside the repo, in `~/share/`).

Last updated: 2026-11-10

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
