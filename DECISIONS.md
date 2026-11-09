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

## 2026-11-10 (Phase 2, made by the assistant)

- **Manifests are TOML, not YAML.** Why: `tomllib` is in the Python standard library, so `heiss-core` and CI need no extra dependency and use a parser without code-execution features; PyYAML (`python-yaml` 6.0.3) is not installed here and I cannot install packages without the owner's sudo password. Direction for metapackages: TOML manifest -> generated PKGBUILD (single source of truth). Reconsider YAML only if the owner insists.
- **State and ownership:** only packages recorded in `/var/lib/heiss/state.json` can be removed; preinstalled packages become owned only through an explicit `--adopt` of explicitly installed packages named in a manifest.
- **`heiss profile apply` without `--dry-run` refuses** until the privileged helper (Phase 3) exists.
- **Profile contents** follow the Phase 0 recommendations the owner accepted (haruna, keepassxc, no mail and office in Base, `code` not shipped, kitty/Thunar/LTS kernel/office/mail as add-ons).

## 2026-11-10 (hardware detection, made by the assistant)

- **Hardware profiles are declarative TOML** in `hardware/` with conjunctive match rules, evaluated by a pure function, so fixtures can assert the result. Why: plan section 11.2; also lets us add hardware without code changes.
- **NVIDIA generation rule = PCI device ID >= 0x1e00** (Turing and newer) for open modules; older cards stay on nouveau with a message, never AUR. Heuristic, not verified against the package; revisit when `supported-gpus.json` can be read.
- **Guest tools only for the detected hypervisor**; microcode and GPU drivers never proposed in a VM.
- **USB detection deferred** (`lsusb` missing on the build VM; no rule needs it yet).

## 2026-11-10 (metapackages, made by the assistant)

- **TOML manifest -> generated PKGBUILD** (the direction left open in Phase 0). One source of truth; CI fails if committed package files differ from regeneration.
- **Metapackages ship only the manifest and enable nothing.** Services and configuration stay in the engine so that every change is planned, audited and reversible through the state file.
- **pkgrel is manual** (`packages/pkgrel.json`), because pacman needs a version change to see an update. Risk: forgetting to bump. Mitigation idea for later: CI comparing the dependency list with the previous release.
- **`profile/packages.x86_64` is not changed** in this PR: putting the metapackages into the ISO changes the image and needs a rebuild and VM test (Phase 10).

## 2026-11-10 (docs rename, made by the assistant)

- **README and CLAUDE.md use Base, Cyber, Developer, Custom**, with a one-line mapping from the old names. The wallpaper packages keep the internal name `Heiss-Everyday` (protected, not renamed).
- **CLAUDE.md now carries the working rules from the master plan** (section 0 asked to copy them in Phase 0, which I had missed): owner merges PRs (the old "second approver" wording is removed), Tier A protection, no unverified claims, official repositories only. Also fixed the outdated note about an absolute path in `pacman.conf`.

## 2026-11-10 (Phase 3, made by the assistant)

- **Helper transport: GDBus through python-gobject (`gi`/Gio), not `python-dbus`.** Why: official package, current API, no extra bindings. Cost: it could not be run on the build VM, so the glue is tested only in CI on a private bus. Correction of my own earlier mistake: `import gi` on this VM only found an empty namespace directory, python-gobject is NOT installed here.
- **Helper maintains the ownership state itself** (after successful steps) and offers `AdoptPackages` for the ISO content. Why: otherwise removal through the helper could never work and a client could claim packages.
- **No client-supplied content anywhere**: drop-in content comes from manifests; post-actions are four fixed ids.
- **polkit defaults `auth_admin_keep`** for all actions: one authentication per apply run. Trade-off: the dialog text does not list package names; the GUI summary page must.
- **Package-name regex tightened** in the manifest validator (no leading `-` or `.`), which also protects `heiss-core`.
- **`SECURITY.md` points to GitHub private vulnerability reporting**; I did not invent a contact address. The owner must enable that feature.
