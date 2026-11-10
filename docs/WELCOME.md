# Heiss Welcome (first-run wizard): plan and state

Master plan section 7. Stack as in `docs/ARCHITECTURE.md`: PySide6 + QML (Kirigami), official packages (`pyside6` 6.12.0, `kirigami` 6.31.0, `qt6-declarative` 6.12.0 exist in the repositories; installed size of pyside6 52 MiB, not yet added to any package list).

## Split into PRs

| Step | What | Needs the public package repository? | State |
|---|---|---|---|
| 5a `feat/welcome-core` | GUI-free model `core/heiss_core/wizard.py`: step order, per-profile defaults, validation, Back/Next/Skip, skip-whole = Base, resume file, done marker, pending-actions queue, summary as a dry-run plan | no | this PR |
| 5b | `heiss-welcome` PySide6/QML app drawing the model; screens 0-11, en/ru strings, keyboard control | no (UI), but offline-only without it | not started |
| 5c | hardware screen wired to `heiss hw detect`, privacy screen items marked implemented / "coming soon" | no | not started |
| 5d | `heiss-welcome.desktop` autostart in the installed system only, `heiss-cleanup.sh` step, `heiss-welcome` package | autostart: no; Apply of a non-Base profile: yes | blocked on the repository |
| 5e | applying screen through the helper, pending queue run from the Control Center (Phase 6) | yes (profiles other than the ISO's Base come from `[heiss]`) | blocked on the repository |

## Model (5a)

- Steps in order: welcome, profile, level, addons, hardware, appearance, privacy, software, backups, summary, applying, done. `skip` is allowed on level..backups; welcome, profile and summary are not skippable. Skipping the whole wizard gives Base with all defaults.
- `set(path, value)` validates through `answers.validate`; a bad value changes nothing. Choosing a profile sets that profile's defaults (Cyber: privacy `enhanced`) only for answers the user did not choose.
- **Answers vs extras.** Only keys of the answers schema (`/etc/heiss/profile.toml`) are real answers. Accent, density, font scale, hardware toggles and the backups choice are `extras`: saved and resumable, **not applied by anything yet**. Their application is added together with the screens that need them.
- Resume: `~/.config/heiss/wizard-state.json` (written after each step by the front end). An interrupted "applying" resumes at the summary, because the plan is recomputed against the real system. A corrupt or foreign file is ignored.
- Done marker `~/.config/heiss/welcome-done`; saved answers `~/.config/heiss/answers.toml`.
- **Pending queue** `~/.config/heiss/pending.json`: only the kind `apply-profile` with `{profile, addons}`. Items are validated when added and again when read (a hand-edited file is rejected). Offline nothing runs; a failure stops the run, keeps the item as `failed` with the message; the user retries or removes it. The queue holds no commands and no package names, so it cannot widen what the helper allows.
- Level: Beginner and Confident confirm changes step by step; advanced sections (for example linux-hardened under privacy) show for Confident and Advanced.

## Known small gaps

- Pending ids are reused after the newest item is removed (harmless: ids are only handles).
- A resumed state may name `done` without the marker file; the front end decides what to show.

## Not verified

- Nothing in 5a runs on a real system; it is tested with fixtures only (`core/tests/test_wizard.py`).
- No screen exists yet: no screenshot can be judged.
- Whether `pyside6` and `kirigami` fit the ISO size budget (needs a build).

## What the owner must do for 5d/5e

The hosted repository does not exist (checked on GitHub: organisation `heiss-os` has no `heiss-repo`). Steps: `docs/infra/REPOSITORY.md`, "Checklist for the owner".
