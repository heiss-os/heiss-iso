# Protection of Tier A files

Tier A (see the Phase 0 audit) is the approved look and boot chain. Two mechanical guards enforce it.

## protected.sha256 and the path list

- `docs/design/protected-paths.txt`: path prefixes that count as Tier A, plus the guard files themselves.
- `docs/design/protected.sha256`: SHA-256 of every tracked file under those prefixes.
- `scripts/check-protected.py verify`: fails when a protected file changed, disappeared, or a new file appeared under a protected prefix.
- `scripts/check-protected.py update`: regenerates the checksum file.

## CI job `protected-paths` (`.github/workflows/guards.yml`)

Runs on every pull request and on pushes to `main`. It fails unless the PR carries the label `design-approved`.

### How a deliberate Tier A change works

1. The owner approves a specific item by name.
2. The PR makes the change AND runs `python3 scripts/check-protected.py update` so `protected.sha256` matches.
3. The owner adds the label `design-approved` to that PR (the job then reports instead of failing) and merges.
4. After the merge the job on `main` passes again because the checksums were updated in the same PR.

Without step 3 the PR cannot be merged cleanly: the job is red. To make that binding, mark `protected-paths` as a required status check in the branch protection of `main` (owner action, GitHub settings).

## Limits (honest)

- Only tracked files are checked. A file that is never committed is not protected.
- The label is set by a human: anyone with triage rights can add it. The guard stops accidents, not a determined maintainer.
- Rename detection is not special: a rename shows up as REMOVED + NEW.

## Token guards (`tokens` job)

- `scripts/gen-theme.py --check`: generated outputs in `branding/tokens/generated/` must match the tokens.
- `scripts/check-contrast.py`: WCAG AA for text pairs and terminal colors. Findings caused by frozen palette values are listed in `known_exceptions` and printed on every run (see STYLE-GUIDE.md).
- `tests/test_tokens.py`: generated KDE schemes must contain every existing key of `HeissDark.colors` / `HeissLight.colors` with the identical value (extra keys allowed).
