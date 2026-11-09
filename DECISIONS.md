# Decisions

Format: date, what, why. Newest at the bottom.

## 2026-11-09 (owner decisions, from the master plan)

- **Base stays:** Arch, KDE Plasma, Calamares, no telemetry, root locked after install, Inter + JetBrains Mono, Heiss Dark / Heiss Light with the sand accent. Why: already approved; not up for change without discussion.
- **Profile names:** Base, Cyber, Developer, Custom. Old names map as Everyday -> Base, Security -> Cyber, Developer -> Developer, Universal -> Custom (replaced). Internal IDs and wallpaper package names stay as they are (wallpapers are protected). Why: product naming decided by the owner; assets already use the old IDs.
- **Languages:** Russian and English from day one, every new string translatable.
- **Control Center** is a standalone app; stock KDE System Settings stay under "Advanced".
- **Blur, transparency, heavy compositor effects:** opt-in only.
- **Review workflow:** the owner merges PRs; there is no second approver. `main` is protected (PR required, no force push). Why: corrects the old CLAUDE.md wording.
- **Official Arch repositories and our own repository only.** AUR / KDE Store / GitHub projects need explicit per-item approval and an entry here. AUR packages are never installed automatically.

## 2026-11-09 (Phase 0, made by the assistant, pending owner confirmation)

- **Phase 0 is docs only** on branch `docs/phase-0-aduit` (branch name spelling is the owner's), created from fresh `main` at `e0eeb08`. Why: the plan forbids code before the owner answers the questions.
- **Facts found that differ from the plan text** are recorded in `docs/design/AUDIT.md`, section 1 (for example: `heiss-theme-sync` only switches the launcher icon; `@LOCALREPO@` is already rendered by `scripts/heiss-build.sh`, so the "known problem" in CLAUDE.md about an absolute path is outdated).

## 2026-11-09 (PR 38, owner decision)

- **Keep every existing palette value unchanged; add derived AA text tokens.** Added `accent_text`, `positive_text`, `neutral_text`, `negative_text`, `info_text` (computed, not hand-picked: the frozen color mixed toward the theme text color in 5% steps until 4.5:1 on window, view, panel and button). Light accent_text = #6D5D3F. Why: the Light accent #8C7448 and the frozen semantic colors fail AA as text; the owner wants them fixed without changing the palette. How to apply: use `*_text` for text and icons, frozen colors for fills and the KDE scheme. Remaining failures of the frozen colors used directly stay listed as known exceptions.
- **Dark `negative_text` differs from `negative`** (#E38C84 vs #E06C64) because the frozen red does not reach 4.5:1 on the button color. Derived value only, scheme untouched.
