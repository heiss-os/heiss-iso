# Heiss Welcome (first-run wizard): plan and state

Master plan section 7. Stack as in `docs/ARCHITECTURE.md`: PySide6 + QML (Kirigami), official packages (`pyside6` 6.12.0, `kirigami` 6.31.0, `qt6-declarative` 6.12.0 exist in the repositories; installed size of pyside6 52 MiB, not yet added to any package list).

## Split into PRs

| Step | What | Needs the public package repository? | State |
|---|---|---|---|
| 5a `feat/welcome-core` | GUI-free model `core/heiss_core/wizard.py`: step order, per-profile defaults, validation, Back/Next/Skip, skip-whole = Base, resume file, done marker, pending-actions queue, summary as a dry-run plan | no | merged (PR 56) |
| 5b | `heiss-welcome` PySide6/QML app drawing the model; screens 0-11, en/ru strings, keyboard control | no (UI), but offline-only without it | this PR (see below) |
| 5c | hardware screen wired to `heiss hw detect`, privacy screen items marked implemented / "coming soon" | no | this PR |
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

## Front end (5b)

- `welcome/heiss_welcome/viewmodel.py`: no Qt; builds each screen as a dict (title, "what this will change", options, buttons) and runs the actions; saves resume state after each action. Tested in `welcome/tests`.
- `strings.py`: en/ru texts (a test checks both languages have the same keys). Profile and add-on names come from the manifests.
- `app.py`: thin PySide6 glue (one `wizard` object for QML). `qml/Main.qml`: one data-driven window, Inter font, Heiss palette, sand accent, Back/Next/Skip, Alt+Left for Back, visible focus ring, accessible names.
- Run by hand: `PYTHONPATH=core:welcome python -m heiss_welcome --force` (needs `pyside6`; config dir override `HEISS_CONFIG_DIR`, manifests `HEISS_PROFILES`).
- **Not in this PR, on purpose:** Apply (needs the repository, 5e), so the summary offers only "Save answers, apply later" (writes `answers.toml` and one `apply-profile` queue item). The hardware and backups screens are "coming soon" placeholders (5c). Accent, density, font size and the per-item privacy toggles have no screen yet. No autostart, no package (5d). Wizard-side live preview of the theme is not done.

## Hardware and privacy screens (5c)

- Hardware: `ViewModel.report()` runs `heiss_core.hardware` detection once when the screen is first shown (live: `lspci`, `/sys`, `systemd-detect-virt`; read-only; a failure means "no proposals", never blocks). Facts (type, processor, virtualization, GPUs, hybrid graphics) are shown as text; each matching hardware profile is a toggle, ticked by default only when `safe_by_default`. Choices are stored in `extras.hardware_toggles` and are **not applied by anything yet** (no step reads them). Detection runs on the UI thread (a few subprocess calls); moving it to a worker is a follow-up.
- Privacy: the level is a real answer; the item list below it is informational with a badge. Only the firewall (firewalld, enabled by the Essentials manifest at every level) is marked "In place"; DNS over TLS, MAC randomization, VPN/WireGuard, Bluetooth off at Maximum, screen lock and linux-hardened (Confident/Advanced only) are marked "Coming soon". Per-item toggles have no screen because nothing could act on them.
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
