# Heiss Control Center (Phase 6)

Split into small PRs. Status of each page:

| Page | Status |
|---|---|
| Overview (profile, privacy level, Heiss-installed package count, pending actions, kernel) | built, read-only |
| About (system, build, kernel, Plasma, links, licence, "not affiliated with Arch Linux") | built, read-only |
| Search (page titles and keywords, en/ru) | built |
| Profiles and software, Appearance | next PR |
| Security Center, Updates and snapshots, Network and privacy, Advanced | later PRs |
| Hardware and drivers (Phase 7), Power and display, Backups | later (sidebar entry exists, page says "Coming soon") |

## Structure

- `control/heiss_control/model.py`: what the window shows. No Qt. Every source (os-release, answers, state, pending queue, kernel, `plasmashell --version`) is injected through `Env`, so `control/tests/` run on fixtures without Qt. A source that fails shows its error on its own card and never stops the window.
- `control/heiss_control/app.py`: PySide6 glue (one `control` object for QML). `control/heiss_control/qml/Main.qml`: sidebar, search, pages, colours from the Heiss tokens.
- `control/heiss_control/strings.py`: en/ru; a test requires both languages to have the same keys.

## Rules this shell follows

- The GUI never runs as root and this version never writes anything: no helper call, no file written. A test checks that building the screen leaves the directories untouched.
- The sidebar already lists the final pages; a page that is not built says "Coming soon" instead of pretending.
- Links open only if they start with `https://` and come from `os-release`.
- Plain QtQuick.Controls like the wizard, not Kirigami (see DECISIONS.md, 2026-11-13).

## Not built or packaged yet

No `heiss-control` package, no `.desktop` file and no ISO entry in this PR. They come with the next PR, together with the first page that needs the helper. Run by hand: `PYTHONPATH=core:control python -m heiss_control` (needs `pyside6`).
