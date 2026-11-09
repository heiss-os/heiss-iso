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
- Phase 2: PR "feat/core-profiles" (core engine: manifests, answers, state, resolver, CLI, profiles). Merged: core engine (PR 39), hardware detection (PR 40). In review: metapackages (feat/profile-metapackages). Still to do in Phase 2: README/docs rename PR.
