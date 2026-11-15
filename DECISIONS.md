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

## 2026-11-09 (Phase 0, pending owner confirmation)

- **Phase 0 is docs only** on branch `docs/phase-0-aduit` (branch name spelling is the owner's), created from fresh `main` at `e0eeb08`. Why: the plan forbids code before the owner answers the questions.
- **Facts found that differ from the plan text** are recorded in `docs/design/AUDIT.md`, section 1 (for example: `heiss-theme-sync` only switches the launcher icon; `@LOCALREPO@` is already rendered by `scripts/heiss-build.sh`, so the "known problem" in CLAUDE.md about an absolute path is outdated).

## 2026-11-09 (PR 38, owner decision)

- **Keep every existing palette value unchanged; add derived AA text tokens.** Added `accent_text`, `positive_text`, `neutral_text`, `negative_text`, `info_text` (computed, not hand-picked: the frozen color mixed toward the theme text color in 5% steps until 4.5:1 on window, view, panel and button). Light accent_text = #6D5D3F. Why: the Light accent #8C7448 and the frozen semantic colors fail AA as text; the owner wants them fixed without changing the palette. How to apply: use `*_text` for text and icons, frozen colors for fills and the KDE scheme. Remaining failures of the frozen colors used directly stay listed as known exceptions.
- **Dark `negative_text` differs from `negative`** (#E38C84 vs #E06C64) because the frozen red does not reach 4.5:1 on the button color. Derived value only, scheme untouched.

## 2026-11-10 (Phase 2)

- **Manifests are TOML, not YAML.** Why: `tomllib` is in the Python standard library, so `heiss-core` and CI need no extra dependency and use a parser without code-execution features; PyYAML (`python-yaml` 6.0.3) is not installed here and I cannot install packages without the owner's sudo password. Direction for metapackages: TOML manifest -> generated PKGBUILD (single source of truth). Reconsider YAML only if the owner insists.
- **State and ownership:** only packages recorded in `/var/lib/heiss/state.json` can be removed; preinstalled packages become owned only through an explicit `--adopt` of explicitly installed packages named in a manifest.
- **`heiss profile apply` without `--dry-run` refuses** until the privileged helper (Phase 3) exists.
- **Profile contents** follow the Phase 0 recommendations the owner accepted (haruna, keepassxc, no mail and office in Base, `code` not shipped, kitty/Thunar/LTS kernel/office/mail as add-ons).

## 2026-11-10 (hardware detection)

- **Hardware profiles are declarative TOML** in `hardware/` with conjunctive match rules, evaluated by a pure function, so fixtures can assert the result. Why: plan section 11.2; also lets us add hardware without code changes.
- **NVIDIA generation rule = PCI device ID >= 0x1e00** (Turing and newer) for open modules; older cards stay on nouveau with a message, never AUR. Heuristic, not verified against the package; revisit when `supported-gpus.json` can be read.
- **Guest tools only for the detected hypervisor**; microcode and GPU drivers never proposed in a VM.
- **USB detection deferred** (`lsusb` missing on the build VM; no rule needs it yet).

## 2026-11-10 (metapackages)

- **TOML manifest -> generated PKGBUILD** (the direction left open in Phase 0). One source of truth; CI fails if committed package files differ from regeneration.
- **Metapackages ship only the manifest and enable nothing.** Services and configuration stay in the engine so that every change is planned, audited and reversible through the state file.
- **pkgrel is manual** (`packages/pkgrel.json`), because pacman needs a version change to see an update. Risk: forgetting to bump. Mitigation idea for later: CI comparing the dependency list with the previous release.
- **`profile/packages.x86_64` is not changed** in this PR: putting the metapackages into the ISO changes the image and needs a rebuild and VM test (Phase 10).

## 2026-11-10 (docs rename)

- **README and CLAUDE.md use Base, Cyber, Developer, Custom**, with a one-line mapping from the old names. The wallpaper packages keep the internal name `Heiss-Everyday` (protected, not renamed).
- **CLAUDE.md now carries the working rules from the master plan** (section 0 asked to copy them in Phase 0, which I had missed): owner merges PRs (the old "second approver" wording is removed), Tier A protection, no unverified claims, official repositories only. Also fixed the outdated note about an absolute path in `pacman.conf`.

## 2026-11-10 (Phase 3)

- **Helper transport: GDBus through python-gobject (`gi`/Gio), not `python-dbus`.** Why: official package, current API, no extra bindings. Cost: it could not be run on the build VM, so the glue is tested only in CI on a private bus. Correction of my own earlier mistake: `import gi` on this VM only found an empty namespace directory, python-gobject is NOT installed here.
- **Helper maintains the ownership state itself** (after successful steps) and offers `AdoptPackages` for the ISO content. Why: otherwise removal through the helper could never work and a client could claim packages.
- **No client-supplied content anywhere**: drop-in content comes from manifests; post-actions are four fixed ids.
- **polkit defaults `auth_admin_keep`** for all actions: one authentication per apply run. Trade-off: the dialog text does not list package names; the GUI summary page must.
- **Package-name regex tightened** in the manifest validator (no leading `-` or `.`), which also protects `heiss-core`.
- **`SECURITY.md` points to GitHub private vulnerability reporting**; I did not invent a contact address. The owner must enable that feature.

## 2026-11-10 (apply wiring)

- **`heiss profile apply` runs through the helper** with confirmation (`--yes` to skip; refuses without a terminal). Order: adopt, install, enable, drop-ins, disable, remove, post actions; KDE settings last as the user. Why: removals last so a failure never strips the system; KDE settings only after the privileged part succeeded.
- **Pre-flight refusals before any change:** Flatpak changes (unsupported), downloads while NetworkManager says offline (`nmcli`, no probing of the network by us; unknown counts as online and pacman reports the real failure).
- **Client sends only names and ids**, never file content; the helper reads content from its own manifests.
- **Gaps recorded:** the answers file is not saved by `apply` (needs a helper method), state entries of vanished packages are not forgotten, no cancel.

## 2026-11-10 (Phase 4, first ISO-changing PR, owner instruction)

- **The ISO now contains `heiss-core`, `heiss-helper` and `heiss-profile-base`**, built into `[heiss-local]`, so the next ISO build tests the helper and `heiss profile apply` end to end. Base in the ISO is delivery option (a) from Phase 0. Before/after ISO size is NOT measured (needs a real build).
- **`heiss-core` ships all manifests; metapackages are empty.** Why: otherwise `apply --profile cyber` could not find `cyber.toml` before `heiss-profile-cyber` was installed. Supersedes the earlier choice that metapackages ship their manifest.
- **Packages are built from git HEAD** by `scripts/heiss-packages-build.sh` (replaces `heiss-profile-build.sh`); `sha256sums=('SKIP')` is acceptable because the archive is generated locally from a commit, not downloaded. `heiss-build.sh` (Tier A) was not edited; the build order is documented instead.
- **Found by running the packaged layout:** `PacmanSystem` crashed when `flatpak` is not installed (it is not on the ISO). A missing command is now reported as "no data", with tests.
- **Not changed in this PR:** the releng leftovers in `packages.x86_64` (clonezilla, nmap, ...), mime associations, theming: separate Phase 4 PRs.

## 2026-11-10 (file associations)

- **Defaults live in `/etc/xdg/mimeapps.list`** (system-wide XDG file): reaches the live session, the installed system and new users, and per-user choices still win. New file, no existing config edited.
- **One app per job, only Base apps:** Dolphin, Firefox, Kate, Gwenview, Okular, Haruna (video and audio), Ark, KeePassXC. No `mailto:` handler because Base has no mail client.
- **Aliases listed next to canonical MIME names** where tools disagree; unknown types were dropped by checking against shared-mime-info.
- **Guard in CI:** every desktop file must exist in a Base package (`pacman -F`), so a renamed desktop file or a package removed from Base fails the build instead of silently breaking a default.

## 2026-11-10 (GTK)

- **No GTK configuration is shipped yet; Plasma's `kde-gtk-config` stays the single owner of GTK settings.** Why: the package database shows it already ships the kded `gtkconfig` module, a GTK3 color-reload module, Breeze window-decoration CSS and depends on `xsettingsd` and `xdg-desktop-portal-gtk`. Writing the same files from Heiss would race with it, and I cannot run GTK here to see the actual files.
- **`heiss-gtk-audit` (read-only, in `heiss-core`) collects the facts in the VM.** The next GTK step is chosen from its output (decision table in `docs/design/GTK.md`). Generated token CSS for GTK stays staged in `branding/tokens/generated/`.
- **GTK prerequisites are guarded by a test:** kde-gtk-config, breeze-gtk and both portal backends must stay in every profile.

## 2026-11-10 (theme sync)

- **`heiss theme sync` replaces the shell logic** (the entry point `heiss-theme-sync.sh`, the path unit and the autostart entry stay). Python in heiss-core so it can be unit tested against a scripted desktop; one log line per target; failures are visible; exit code 1 only on failure.
- **Set only what nothing else sets** (launcher icon, Konsole default profile and running sessions); **check the rest** (Plasma consistency against the Look-and-Feel defaults, kde-gtk-config module, GSettings, portal) and report differences instead of writing Plasma-owned files (Tier B).
- **kitty follows the portal** through `*-theme.auto.conf` files; no sync target writes kitty config.
- **New package `heiss-theme`** (generated from the tokens: Konsole schemes and profiles, `/etc/xdg/konsolerc`, kitty files) and it is in the ISO list. Terminal font size token `terminal` = 11 pt.
- **CI guard against file conflicts:** no file of our packages may also be shipped by an official package (`pacman -F`), because pacstrap would fail the ISO build.
- **Stacked on PR 47** (the GTK audit) because both bump the pkgrel of heiss-core.

## 2026-11-10 (releng leftovers, on the owner's instruction)

- **37 packages removed from `profile/packages.x86_64`** (about 118 MiB installed, before squashfs compression; real ISO size NOT measured). Groups: Cyber tools (`nmap`, `tcpdump`, `ddrescue`, `testdisk`, `tpm2-tools`, `sequoia-sq`, `openpgp-card-tools`, `bind`, `ldns`, `ndisc6`), imaging and rescue (`clonezilla`, `partimage`, `partclone`, `fsarchiver`), terminal curiosities (`lynx`, `irssi`, `mc`, `lftp`), legacy dial-up and VPN clients (`pptpclient`, `wvdial`, `xl2tpd`, `vpnc`, `openconnect`, `openvpn`, `linux-atm`, `wireless_tools`), unused storage tools (`bcachefs-tools`, `jfsutils`, `nilfs-utils`, `open-iscsi`, `mmc-utils`, `sdparm`, `sg3_utils`, `lsscsi`, `b43-fwcutter`), `dnsmasq`, `usbmuxd`.
- **Checked, not assumed:** the dependency closure of the remaining list plus the `essentials` and `base` manifests was resolved against the sync databases in an empty root; none of the removed packages is pulled in. Two candidates were kept for that reason: `ppp` and `pcsclite` are needed by other packages.
- **Deliberately kept:** everything the installer, the boot menu and the live session need (`syslinux`, `memtest86+`, `edk2-shell`, `mkinitcpio-archiso`, `nbd`, `darkhttpd`, `nfs-utils`, filesystem tools for the Calamares partition page, `dmraid`, `mdadm`), plus `vim`, `tmux`, `screen`, `nano`, `less`. `heiss-cleanup.sh` is not touched: its removal list still covers the live-only packages.
- **Consequence:** Calamares no longer offers JFS, NILFS2 and bcachefs for new partitions (their tools are gone). nmap and tcpdump return with the Cyber profile.
- **Not verified:** ISO build, boot, installation. Needs a rebuild and the VM check from `docs/ISO-E2E-TEST.md`.

## 2026-11-10 (icon fixes)

- **No icon was changed or added.** Reading the packages showed no defect: every pinned desktop id exists in its package and every `Icon=` resolves in `hicolor`, `breeze` or `breeze-dark`. The only icon we ship for the installer lives under `hicolor/` (Tier A), so adding an SVG needs an approved item. I did not guess a fix without a screenshot.
- **Added a guard instead:** `scripts/check-launchers.py` (pins identical in Dark and Light, no comma-joined or duplicated pins, pins shipped by a Base package, installer desktop files carry `StartupWMClass=calamares` and a shipped icon, the `/usr/local` override stays hidden). CI runs it with the file database.
- **Open for the owner:** after the next ISO build, a screenshot of the dock (Dark and Light) and of the running installer decides whether there is a real problem left.

## 2026-11-10 (launcher menu)

- **Hide with `Hidden=true` stubs in `/usr/local/share/applications`, no `Exec`.** Why: the files belong to packages (cannot be edited in `airootfs`, pacstrap conflict), a stub cannot drift, and the same mechanism already hides the Calamares entry. Alternative rejected: removing packages (they are dependencies of Plasma, ffmpeg, sane).
- **Ten entries hidden:** KWrite, Vim, mpv (second editor/player), four Qt developer tools, two V4L2 tools, lstopo. List and reasons: `docs/apps/LAUNCHER.md`.
- **Guard `scripts/check-menu.py`:** stubs must be well formed, must not hide a dock pin or a default application, and (CI, file database) must still match a shipped entry.
- **Not read:** desktop files of firefox, spectacle, print-manager (package name with epoch / size); recorded in the doc as not verified.

## 2026-11-10 (keyboard shortcuts)

- **No custom shortcuts added.** The packages already declare `Meta+E` (Dolphin), `Ctrl+Alt+T` (Konsole), `Meta+I` (System Settings), `Meta+Esc` (System Monitor), `Meta+.` (emoji), `Calculator` (KCalc); these are read from the desktop files, not remembered. A `kglobalshortcutsrc` of our own would override Plasma defaults I cannot list on the build VM (KWin and KRunner register theirs in code) and is Tier B territory.
- **Guard instead:** `scripts/check-shortcuts.py` finds key collisions between desktop files and keeps `docs/design/SHORTCUTS.md` true (CI downloads the Base apps and compares).
- **Open:** the real list of Plasma/KWin shortcuts needs the VM (`docs/design/SHORTCUTS.md`, section "NOT verified").

## 2026-11-10 (open terminal here)

- **Nothing is configured; behaviour documented and guarded.** Dolphin 26.08.3 has "Open Terminal Here", "Open Terminal" and a terminal panel (strings in the binary); the panel needs `konsolepart.so` from `konsole`; KIO falls back to `konsole` when `TerminalService`/`TerminalApplication` is unset. So Base works with no file, and kitty installed next to it does not take over. Pinning the key would mean editing `/etc/xdg/kdeglobals` (Tier B).
- **Thunar add-on is the open question:** its action follows the Xfce preferred-terminal mechanism, which I could not verify. Recorded in `docs/apps/TERMINAL-HERE.md` with VM test steps.
- **Test `core/tests/test_terminal.py`:** Base has Konsole and Dolphin and no second terminal or file manager; add-ons are outside every profile closure; `inode/directory` stays Dolphin.

## 2026-11-10 (reviewer agent)

- **Project subagent `reviewer` (`.claude/agents/reviewer.md`), read-only (Read, Grep, Glob, Bash).** Why: the owner asked for a self-check of every PR against CLAUDE.md, DECISIONS.md, PLAN-STATE and the Tier A list, including unbacked "verified" claims. Run before each PR; its findings go into the PR text. It does not replace CI guards or the owner's review.
- **Path note:** the checksum file is `docs/design/protected.sha256` (the task text said `branding/tokens/`); the agent uses the real path.

## 2026-11-10 (heiss check)

- **`heiss check` lives in heiss-core, no new package.** `heiss` is already in `heiss-core` (ISO and Base); a separate `heiss-check` package would only add a dependency. `heiss-core` pkgrel 3 -> 4 so pacman sees the update.
- **Statuses:** FAIL = a defect the owner must look at; WARN = cannot be judged here (no desktop session, not root, tool missing, live session) or a possible false positive (duplicate visible menu names, a removed package present on a non-Base profile). Exit code 1 only on FAIL.
- **Removed packages:** a package that Heiss installed itself (listed in the state file) is expected on Cyber and is not reported. On Base or with no state file a present one is FAIL.
- **Root lock** needs `/etc/shadow`: without root the item is WARN, not OK. The report is only a file the user asks for; nothing is sent anywhere.
- **Duplicated knowledge:** the removed-package list, hide-stub ids and shortcut rows are constants in `check.py` (the installed system has no repository scripts). Tests compare the removed list to the ISO package list; the stub list and shortcuts follow docs/apps/LAUNCHER.md and docs/design/SHORTCUTS.md by hand.
- `state.parse(text)` split out of `state.load` so the check validates the state file with the same strict rules.

## 2026-11-10 (Welcome wizard, step 5a)

- **The wizard logic is a GUI-free module in heiss-core (`wizard.py`), the QML app only draws it.** Why: Back/Skip/resume/queue rules can be tested without a display; the VM has none.
- **Screen options without a key in the answers schema are `extras`, not answers.** Why: adding keys changes `profile.toml` (schema_version) and must come with something that applies them; documented as "not applied yet" in `docs/WELCOME.md`.
- **Pending queue accepts only `apply-profile` with profile and add-on ids.** Why: it is read later and runs with the user's own rights through the helper; free-form commands would be an escalation path.
- **Phase 5 split 5a-5e;** 5d/5e wait for the public package repository (`docs/infra/REPOSITORY.md` checklist; `heiss-os/heiss-repo` does not exist on GitHub as of 2026-11-10).
- heiss-core pkgrel 4 -> 5.

## 2026-11-11 (no tool attribution, owner's instruction)

- **No attribution to a tool or an AI in commits, PR descriptions, issues, comments or docs.** Why: explicit instruction of the project owner. Rule in CLAUDE.md; `.claude/settings.json` sets `attribution.commit = ""`, `attribution.pr = ""`, `attribution.sessionUrl = false` and the older `includeCoAuthoredBy = false` (all four keys exist in the installed Claude Code 2.1.316; the old one is marked deprecated there).
- **History is not rewritten** (main is protected, no force push): commits and PR texts merged before this keep their trailers.
- The self-review before each PR is called "automated review" in PR texts.

## 2026-11-11 (public package repository setup)

- **GitHub Pages URL:** `https://heiss-os.github.io/heiss-repo/` from branch `gh-pages` (the first commit was made through the contents API; Pages was enabled automatically by it).
- **Signing key:** RSA 4096, signing only, no expiry, no passphrase (used by CI only), ID `FEA84CEF8AEDF132`. Generated in a temporary `GNUPGHOME`; the private half was never written into the repository or a chat.
- **The setup token was used through a separate `GH_CONFIG_DIR`**, not `gh auth login` into the default config, so the owner's normal `gh` login (needed to push and open PRs) was not replaced. The setup token is still logged in there (`GH_CONFIG_DIR=/tmp/claude-1000/-home-heiss-os-heiss-iso/7623dd4a-f587-4ec1-a7d7-e7fc24df78c2/scratchpad/ghsetup` on the build VM) and the token file `~/share/heiss-token.txt` is still on disk: both are to be removed once the remaining steps are done (the owner must delete the host copy).
- **Not done, and why:** writing the repository secrets and shredding the token file were refused by the permission system, so the secrets are set by the owner. The unwiped private key lives in the temporary `GNUPGHOME` `/tmp/gnupg-heiss.8w26Jm` on the build VM until it is set as a secret and backed up (docs/infra/REPOSITORY.md, Status). The private key is NOT wiped and not backed up yet: wiping before the secrets exist would lose it.

## 2026-11-11 (Welcome front end, step 5b)

- Wizard screens are drawn from a Qt-free view-model (`welcome/heiss_welcome/viewmodel.py`), so everything except the QML is unit-tested in CI without a display or PySide6. Reason: no screenshots can be taken in the build VM.
- Plain QtQuick.Controls with hard-coded Heiss palette values instead of Kirigami for now: fewer dependencies for the first-run window; revisit when the Control Center (Phase 6) shares components. The palette duplicates the tokens; a generated QML palette is a follow-up.
- No Apply button until the package repository exists (5e); "save answers, apply later" queues an `apply-profile` item instead.
- The inline error colour `#E06C64` in `Main.qml` is the `negative` token of Heiss Dark, used in both themes for now (not checked for contrast on Light); a generated QML palette will replace it.

## 2026-11-11 (Welcome hardware and privacy screens, step 5c)

- Hardware toggles and privacy items are shown honestly as saved-only / "coming soon" rather than wired to partial behaviour; the apply path for hardware proposals comes with 5e through the resolver and helper.
- Detection reuses `heiss_core.hardware` unchanged (no new detection code, no new packages, no network).

## 2026-11-11 (CI publishing job)

- **Publish only from `main` and manual runs; pull requests do a dry run with a throwaway key.** Why: secrets must not be used by unreviewed code, yet the sign-and-verify path still gets tested on every relevant PR.
- **Pinned fingerprint in the workflow.** The job fails if the secret key or `docs/infra/heiss-public.asc` is not `DDD292CCC8613FD3324D3833FEA84CEF8AEDF132`, so a wrong secret can never publish under another key.
- **Published files are immutable; a new `pkgrel` publishes a new version.** Why: makepkg output differs run to run, replacing a file under the same version breaks checksums for existing users.
- **Real files instead of symlinks for `heiss.db`/`heiss.files`.** GitHub Pages behaviour with symlinks is not verified.
- **Push token passed as an HTTP header (masked), not in the URL.**

## 2026-11-11 (repository index pages)

- **`index.html` for `/` and `/x86_64/` is generated by `heiss-repo-assemble.sh`**, deterministic (sorted, no timestamps). Why: Pages has no directory listing; a plain page is friendlier than a 404. A changed page alone is published, but never rebuilds the signed database.
## 2026-11-11 (heiss-keyring)

- **The keyring package is built from `docs/infra/heiss-public.asc`** (added to the build archive) and refuses to build if that file is not the pinned key `DDD292CCC8613FD3324D3833FEA84CEF8AEDF132`. Why: one source of truth for the public key, no second copy to drift.
- **Trust level 4 (full) in `heiss-trusted`, same format as `archlinux-trusted`; no revoked keys.** The `.install` populates only when the pacman keyring is already initialised, otherwise it prints the two commands (the installed system initialises it in `heiss-cleanup.sh`).

## 2026-11-11 (repository in the installed system, owner-approved Tier A change)

- **Owner approved both items on 2026-11-11 ("yes, both items"): a `[heiss]` section via `heiss-cleanup.sh` and `heiss-keyring` in the ISO package list.**
- **The section is added only after `pacman-key --populate heiss` succeeded.** Why: with `SigLevel = Required` and an untrusted key every `pacman -Sy` on the installed system would fail. It is appended last, so official repositories keep priority. `HEISS_NO_REPO=1` skips it.

## 2026-11-11 (merge self-check rule, owner's instruction)

- **Before asking the owner to merge, the PR author verifies base, freshness, conflicts, CI, labels, PR text, notes and a clean pushed tree, and reports in a fixed format.** Why: PR 65 was based on a feature branch and its changes never reached `main`. Rule in CLAUDE.md. PRs are never stacked: always branch from fresh `main`.
- PR 65's content is re-applied on `main` by cherry-picking its squash commit (`987675a`), no conflicts.

## 2026-11-11 (Welcome applying, step 5e)

- **Apply runs `heiss profile apply` as a child process, not the helper client in-process.** Why: the Qt process on Linux iterates the default GLib context; the helper client runs its own GLib main loop and would fight it. A child process also keeps the window responsive and reuses the one tested apply path (preflight, ordering, error messages).
- **`--adopt` is used for the plan and the apply,** as the summary plan in `wizard.summary_plan` already did: a first-run wizard on an ISO-installed Base should claim the already-installed profile packages.
- **No "back to summary" after a failure;** only Try again and Save for later. A resumed interrupted apply already returns to the summary. Adding it needs a core change and a pkgrel bump, left for later.
- **No Cancel:** the helper has none yet (Phase 3 follow-up), so the UI does not pretend to stop the job.

## 2026-11-11 (Welcome package and autostart, step 5d, owner chose the defaults)

- **The autostart entry excludes the live session itself (`test -e /run/archiso ||`) instead of `heiss-cleanup.sh` placing it.** Why: no Tier A change, and the package works wherever it is installed. The owner confirmed this default on 2026-11-11.
- **`heiss-welcome` and its dependency `pyside6` go into the ISO package list.** Why: without them the installed system has no wizard. Cost per `pacman -Si`: pyside6 52 MiB installed, 9.2 MiB download, shiboken6 0.7 MiB; the real ISO size change is unmeasured (no build).
- `inter-font` is an optional dependency only: not added to the ISO by this change.

## 2026-11-11 (final VM test list, owner's instruction)

- **No ISO build and no VM check until the whole master plan is done.** Owner's rule. Why: the final test is a single run, so unverified items must not get lost between PRs. Every PR that adds an unverified claim also adds a line to "FINAL VM TEST LIST" in `docs/PLAN-STATE.md`, grouped by phase; that list is the script for the one final check.

## 2026-11-11 (applying the hardware choices, owner's item 3)

- **Hardware choices go through the existing path:** `--hardware ID` on `heiss profile apply|diff`, resolved by the engine, executed by the helper (hardware manifests were already trusted there). No new helper API.
- **Applied hardware profiles are kept by a "sticky" rule** (all their packages Heiss-owned, not already wanted by the profile). Why: the resolver removes owned packages that are no longer wanted, so without it the next profile change would propose removing a graphics driver. The cost: unticking later does not uninstall; removal is an explicit action in the Control Center.
- **Kernel parameters are reported, never applied.** Why: editing the boot loader cannot be verified here and a wrong value leaves the machine unbootable. NVIDIA open modules stay opt-in with their warning.
- heiss-core pkgrel 5 -> 6, heiss-welcome 1 -> 2.
- (review fix) The sticky rule compares only a profile's OWN packages (not those the profile already wants) and uses the machine's detection to tell siblings apart. Why: state records only installed and adopted packages, so a shared dependency like `mesa` is never owned; requiring all packages would drop the rule exactly for GPU profiles, and a package shared with another profile would pull in profiles the user never chose. No state schema change.

## 2026-11-11 (applying the theme choice, owner's item 3)

- **The theme is applied when the user picks it (live preview), not at the end.** Why: it is a user-level desktop setting, needs no privileges, and the wizard then shows the real result; Apply (packages) stays separate. Only Dark and Light act; Automatic leaves the desktop alone, because Plasma's automatic switching is not configured and cannot be verified here.
- **Uses `plasma-apply-lookandfeel` with the shipped LnF ids,** not direct writes to Plasma's config files (Tier B surface). heiss-welcome pkgrel 2 -> 3.

## 2026-11-11 (three more subagents, owner's instruction)

- **`security-reviewer`, `qa-verifier` and `docs-keeper` join `reviewer` in `.claude/agents/`.** Why: the reviewer reads one diff for everything; privilege code, running things in a clean checkout and keeping the notes consistent each need a narrower, stricter pass. All four have no Edit, Write or NotebookEdit tools (a test enforces that); writes through Bash (edit, commit, push) are prevented only by their instructions, not technically. `qa-verifier` also runs code under test without tokens and never from the owner's tree.
- **When each one is required** is written in `CLAUDE.md` ("Субагенты"); HIGH and MEDIUM findings of the security reviewer block opening the PR; the verdicts go into the report block as `агенты: ...`.

## 2026-11-11 (privacy level applied, step 3c)

- **Privacy levels are code constants in `heiss_core/privacy.py`, written through a new helper method `WritePrivacy(level)`**, not manifest drop-ins. Why: the helper takes drop-in content from installed manifests by path alone, and one path cannot hold three contents; a level name is the only thing a client can send, so the client still never supplies a path or content. Reuses polkit action `org.heiss.config.write` (no policy change).
- **Scope: Wi-Fi/Ethernet MAC address default and screen lock only.** Standard keeps NetworkManager's defaults explicitly (preserve) and KDE's 5-minute lock; Enhanced: stable per-network MAC, 3 minutes; Maximum: random Wi-Fi MAC, stable Ethernet MAC, 1 minute, no grace. DNS over TLS (needs systemd-resolved wiring), Bluetooth off (conflicts with Essentials), VPN and linux-hardened stay "Coming soon".
- **Opt-in in the engine:** privacy is planned only with `--privacy`, so existing `heiss profile apply` runs are unchanged. No NetworkManager restart: it could drop the user's connection mid-apply. heiss-core pkgrel 6 -> 7, heiss-helper 1 -> 2, heiss-welcome 3 -> 4.
- Defaults checked in the `kscreenlockersettings.kcfg` of the Arch `kscreenlocker` package: `Autolock` true, `Timeout` 5 (minutes), `LockGrace` 5 (seconds), so Standard equals KDE's defaults. `wifi.scan-rand-mac-address=yes` is written at every level on purpose: it is NetworkManager's own default (man page), made explicit so it stays on.

## 2026-11-13 (Control Center shell, Phase 6)

- **Plain QtQuick.Controls, not Kirigami, for the Control Center shell.** Why: the wizard already works this way and takes its colours from the Heiss tokens, so both apps look the same; Kirigami would add a dependency (7.2 MiB installed, `pacman -Si kirigami`) and a second look to keep in sync. `docs/ARCHITECTURE.md` named Kirigami as the default; this changes it for now. Revisit if a page needs a Kirigami component that is costly to rebuild.
- **The shell is read-only and not packaged yet.** Why: it keeps the first Control Center PR small and lets the model be tested without Qt; the package, desktop file and ISO entry come with the first page that needs the helper.
- **Search covers page titles and keywords only.** Why: there are no per-setting entries until the pages exist; each page PR adds its own entries.
- **The About page does not state a branding licence.** Why: the repository has only the GPL-3.0 `LICENSE`; no separate branding licence file exists, and none is invented. Owner question: which licence applies to `branding/`?

## 2026-11-13 (Control Center package)

- **`heiss-control` is a separate package in the ISO list (this supersedes "not packaged yet" in the shell entry above: it ships now, before the first helper page), with a visible launcher entry and no dock pin.** Why: the window is useful for the installed system now (Overview, About), and the dock is a Tier B surface that needs a separate "ok". The icon is the stock `preferences-system` until a Heiss icon exists. `heiss-control` pkgrel starts at 1.

## 2026-11-13 (Control Center: Profiles and Appearance pages)

- **The Profiles page is read-only; the Appearance page offers only Dark and Light.** Why: changing the profile or add-ons needs the helper and the removal rules (Heiss-owned packages only), which is its own PR with a security review; Appearance uses the same user-level `plasma-apply-lookandfeel` call as the wizard. "Automatic", accent colour, wallpapers, fonts, density and animations are not offered because nothing applies them yet (the page says so).
- **The current theme is read with `kreadconfig6` (`kdeglobals/General/ColorScheme`) and mapped through `heiss_core.themesync.THEME_OF`;** any other scheme shows as "unknown" and neither button is marked.
- **`kconfig` and `plasma-workspace` are optional dependencies, not hard ones:** every Plasma system has them, and the page shows "unknown" or an error text without them. A CI step checks that `kconfig` ships `kreadconfig6` (the same kind of check as for `plasma-apply-lookandfeel`). heiss-control pkgrel 1 -> 2.
- **Every `Text` in the Control Center QML is `Text.PlainText`, and error messages are flattened and cut to 300 characters** (a test enforces both). Why: `Text` defaults to AutoText, so a package name or error string from a file that looks like HTML would be rendered as rich text (a remote `<img>` would make the window contact the network on its own). Found by the security review of this PR. The wizard's QML has the same default; it is fixed in a separate PR (branch `fix/wizard-plain-text`), not here (see PLAN-STATE).

## 2026-11-13 (wizard QML shows strings as plain text)

- **Every `Text` in the wizard QML is `Text.PlainText`** (a test enforces it). Why: `Text` defaults to AutoText, so a string that looks like HTML would be drawn as rich text; the apply log, error lines and package names come from commands and files, and a remote `<img>` would make the window contact the network on its own. Found by the security review of the Control Center PR, which has the same rule. heiss-welcome pkgrel 4 -> 5.

## 2026-11-13 (Control Center: Advanced page)

- **The Advanced page does two things: open the stock KDE System Settings and run `heiss check`.** Why: the owner's decision is that the stock settings stay reachable under "Advanced"; `heiss check` already is the health check for an installed system and changes no settings (its theme item takes the short-lived theme-sync lock file in `$XDG_RUNTIME_DIR`, or `/tmp` when unset, and shows WARN while a sync holds it), so the page shows its result instead of a second implementation. Both use fixed argument lists, no shell, no helper, no privileges; the check runs in this process on a worker thread (its commands can take 30 s each); statuses outside OK/WARN/FAIL are shown as WARN and all texts are plain and cut to 300 characters.
- **Not in this page yet:** the journal, a list of services, Heiss logs and the bug-report bundle without personal data. Why: each needs a decision about what may leave the machine (the bundle) or a verified command line (journal access without root); they come in their own PRs.
- heiss-control pkgrel 2 -> 3, `systemsettings` as an optional dependency.

## 2026-11-13 (Control Center: Security Center page)

- **The Security Center is read-only and has no score and no Fix buttons in this step.** Why: the master plan asks for snapshot-first fixes and a score; both need the helper and the snapshot work (Btrfs is a separate Tier A item), and five unprivileged facts are too few for a number that would not mislead. Each fact comes with plain-language advice (a command to run yourself) only when it needs a look.
- **Own small checks, not `lynis`/`arch-audit` yet.** Why: neither is in the ISO and adding packages is a separate decision; the page does not write an audit engine, it shows five facts the system already knows. Wrapping the two tools stays on the list.
- **Not judged on purpose:** whether the root account is locked (reading `/etc/shadow` needs root; `heiss check` does it when run as root) and pending updates (Updates page). Secure Boot is display only; Heiss OS does not manage it.
- heiss-control pkgrel 3 -> 4.

## 2026-11-13 (Control Center: saved actions)

- **The Control Center runs the wizard's saved actions by starting `heiss profile apply` in a child process, like the wizard's Apply.** Why: that command is the one tested path to the helper and polkit; the window never links GLib or D-Bus and stays responsive. The runner is a small copy of the wizard's `CliApplier.run` (not imported, so the Control Center does not depend on `heiss-welcome`); moving it into `heiss_core` is a refactor for later.
- **Only on an explicit click, never offline, one run at a time, ids re-checked.** Why: the queue file is user-writable; `PendingQueue` validates items on every read, and the runner checks the ids again with `fullmatch` (the core pattern uses `match`, where `$` lets a trailing newline through; noted for a later core fix). A hand-edited item can therefore at most apply a profile or add-on that the helper's own allowlist already accepts.
- **The saved privacy level and hardware choices are not applied from the queue.** Why: the queue holds only `{profile, addons}` by design (see `docs/WELCOME.md`). Re-running the wizard or `heiss profile apply --privacy=...` applies them.
- heiss-control pkgrel 4 -> 5 (final: 4 -> 6, see the bullets below).
- (security review fixes, same PR) **The child of "Apply saved actions" runs isolated:** `python -I -m heiss_core`, cwd `/`, without `PYTHON*` and `LD_*`. Why: polkit's `auth_admin_keep` keeps the authorisation per calling process, so code imported into that process from the user's directory or environment would inherit the password the user typed. Cost: Apply from a source checkout does not work; the installed packages are what counts. The wizard's `CliApplier` has the same weakness (open item in PLAN-STATE).
- (same) **`PendingQueue` locks every load-modify-save and `run` merges its result into the file as it is after the run.** Why: a run takes minutes; the wizard or a second Control Center could add or remove an item meanwhile and the final write would undo it. The lock is never held while an action runs. heiss-core pkgrel 7 -> 8, heiss-control 5 -> 6.
- (same) **Ids are matched with `fullmatch` in the queue, the manifest loader and the manifest list entries and file names** (`$` lets a trailing newline through). The earlier note "for a later core fix" in this entry is done.
- (second security pass, same PR) **`PendingQueue.run` merges by content, not by id alone:** an item counts as "the one that ran" only if it is still exactly as it was when the run started, because ids are reused after the newest item is removed (a new item must not be dropped or marked failed with an old error). File errors of the queue (unwritable directory, unreadable file) are `HeissError`, and a failed merge never hides the error that stopped the run. The child's environment also loses `GCONV*`, `LOCPATH`, `NLSPATH`, `GIO_*` and `HEISS_*` (the HEISS_* overrides would let the client-side plan read other manifests; the helper does not trust them anyway).

## 2026-11-13 (wizard Apply runs isolated)

- **The wizard's `CliApplier` starts `python -I -m heiss_core` in `/` without `PYTHON*`, `LD_*`, `GCONV*`, `LOCPATH`, `NLSPATH`, `GIO_*` and `HEISS_*`, for the plan and for Apply.** Why: found by the security review of the Control Center's saved-actions PR (PR 80), which already does this: the child ends up calling the helper and polkit's `auth_admin_keep` keeps the authorisation per calling process, so code imported into that process from the user's directory or environment would inherit the password the user typed. Cost: Apply from a source checkout needs `heiss_core` installed; the `HEISS_PROFILES` override does not reach the child (the helper never trusted it). heiss-welcome pkgrel 5 -> 6. The duplicated environment filter in `heiss_welcome.applier` and `heiss_control.runner` is a candidate for `heiss_core` later.
- (security review of this PR) **The filter also drops `GI_*`, `G_*`, `GSETTINGS_*` and `DBUS_SYSTEM_BUS_ADDRESS`, in both places.** Why: the child imports `gi` (the helper client), so `GI_TYPELIB_PATH` names libraries that would be loaded into the process holding the polkit authorisation; a forged system bus address would show a forged result. The session bus, `XDG_RUNTIME_DIR` and the display variables stay (the polkit agent needs them). This closes the same gap in the Control Center runner from PR 80: heiss-control pkgrel 6 -> 7. (This supersedes the variable lists in the PR 80 entries above.)

## 2026-11-13 (Control Center: Network and privacy page)

- **The page is read-only: it compares what the privacy level wrote with the level the user chose, and does not change the level.** Why: changing the level is a privileged write through the helper (`WritePrivacy`) plus `kwriteconfig6`, and it needs the profile selection of `heiss profile apply`; that belongs with the profile-change PR and its security review. Until then the advice is the command (`heiss profile apply --privacy=LEVEL`) or the wizard.
- **It reads the drop-in file and the KDE keys, not NetworkManager's live state.** Why: the live value is only readable with `nmcli` per connection and changes after a restart anyway; the file is what Heiss wrote and what will apply. The page says so.
- **Unset KDE keys count as KDE's defaults (Autolock true, Timeout 5, LockGrace 5), which equal the Standard level.** Why: `kreadconfig6 --default`; the values are the ones recorded in the privacy-level decision above (checked there against the kcfg of the Arch `kscreenlocker` package; not re-read for this PR because the package is not installed on the build host). If they were wrong, every fresh install would show a false "Look at this" on the screen lock: the VM test list has a step for it.
- **Only the Wi-Fi MAC setting is compared, not the Ethernet MAC or `wifi.scan-rand-mac-address`.** Why: the page and its texts say "Wi-Fi MAC address"; someone who edits only the Ethernet line still sees OK. Extending the comparison is cheap and can follow.
- The fact-card QML is a shared component for the Security Center and this page. heiss-control pkgrel 7 -> 8.

## 2026-11-14 (Control Center: Updates and snapshots page)

- **The page is read-only: it shows facts and the command to run, and has no update, rollback or snapshot button.** Why: updating and rollback are privileged helper work (and rollback needs the Btrfs decision, which is a separate Tier A item); the installed system is ext4 today, so a snapshot page that did more would pretend.
- **Updates waiting come from `pacman -Qu`, not `checkupdates`.** Why: `checkupdates` (pacman-contrib, not in the ISO) syncs a temporary database over the network; `pacman -Qu` reads the local one, so the page never goes online by itself. The cost is that the count is only as fresh as the last refresh, and the page says so.
- **Snapshots are not counted.** Why: `snapper list` and `/.snapshots` need root. The page shows only whether the file system is Btrfs and whether the snapper root config exists.
- **"Restart needed" is the running kernel's module directory missing.** Why: cheap, needs no privileges; it does not detect a microcode, glibc or systemd update that also wants a restart.
- **When a value cannot be told, the page says "unknown", never "none" or "OK".** Why: `pacman -Qu` exit 1 with the database lock held, a last-upgrade line that is not in the last 256 KiB of `pacman.log`, and a last-upgrade date in the future could all read as "no updates" or "updated recently". A warning is shown only for a known date older than 30 days. Other pacman errors still cannot be told from "no updates" (`pacman -Qu` exits 1 for both): a known limit.
- heiss-control pkgrel 8 -> 9.

## 2026-11-14 (Control Center: Hardware and drivers page)

- **The page is read-only and installs nothing; it points to the wizard or `heiss profile apply --hardware=ID`.** Why: a driver install is a privileged helper job and needs the snapshot and safe-graphics work (rest of Phase 7) before it is offered with one click; NVIDIA in particular has a black-screen risk that was never tested on real hardware.
- **It reuses `heiss_core.hardware` detection and the shipped hardware profiles, not a second detector.** Why: one source of truth with the wizard and `heiss hw detect`.
- **The driver doctor report is plain text with an explicit list of what it leaves out** (hostname, user, serials, PCI slots, MAC addresses, DMI vendor and product). Why: it is meant to be pasted into a bug report. DMI strings are left out although they are not personal in themselves, because they identify a machine model closely enough to be unnecessary for a first diagnosis. A test covers the PCI slots and DMI strings of every fixture. The report is English only.
- **When `pacman -Qq` gives no list, every proposal reads "unknown", not "not installed".** Why: an empty answer would otherwise claim a missing driver.
- **The clipboard copy is the only thing the page writes, and only on a click.** heiss-control pkgrel 9 -> 10.

## 2026-11-14 (Phase 7: safe fallback design, proposal only)

- **`docs/hardware/SAFE-FALLBACK.md` records the proposal; nothing is decided or built.** Why: the safe-graphics boot entry and a second kernel change what the installed system boots, and the choice between a package file and a Tier A route (`heiss-cleanup.sh`) is the owner's. Four numbered questions are in the document.
- **Found: the NVIDIA profile warning refers to a safe graphics boot entry that does not exist, and says the LTS kernel needs DKMS although `nvidia-open-lts` is in the repositories.** To be corrected in a follow-up PR once the owner answers; the text is user-facing and the entry must exist first.

## 2026-11-15 (Phase 7: safe-graphics boot entry)

- **Owner's answers to `docs/hardware/SAFE-FALLBACK.md`: 1 A, 2 A, 3 A, 4 A.** The entry is a package file in `/etc/grub.d/`; `linux-lts` and `nvidia-open-lts` only together with the NVIDIA driver; NVIDIA stays never pre-ticked and needs a second confirmation, offered only when the entry is installed; work order as proposed.
- **The entry ships as its own package `heiss-safe-graphics` (depends on `grub`), in the ISO package list, not in `heiss-core`.** Why: it changes the boot menu of the installed system, so it is kept separate, easy to review and easy to remove; no Tier A file is touched (not the GRUB theme, Calamares config or `heiss-cleanup.sh`). Calamares copies ISO packages into the target and runs `grub-mkconfig`, which picks the script up.
- **The entry boots `nomodeset` with `modprobe.blacklist=nvidia,nvidia_modeset,nvidia_uvm,nvidia_drm`, keeps the user's own kernel parameters and drops `nvidia*`, `nomodeset` and `modprobe.blacklist=` words from `GRUB_CMDLINE_LINUX`.** Why: `nvidia-drm.modeset=1` from the NVIDIA profile would otherwise defeat the entry. `GRUB_CMDLINE_LINUX_DEFAULT` (for example `quiet`, `splash`) is deliberately not used, like the recovery entry of `10_linux`: a recovery path should show messages. Known risk, in the test list: the blacklist may not stop a module named in the initramfs `MODULES` (the NVIDIA profile adds them there).
- **One entry per installed kernel in a fixed list (`linux`, `linux-lts`), only if both the kernel and its initramfs exist.** The script has no environment override for `/boot` (it runs as root); the tests run a copy with the path replaced. Words containing `*` or `?` in `GRUB_CMDLINE_LINUX` are not glob-expanded (`set -f`). A user's own `modprobe.blacklist=` words are dropped from this entry (the entry sets its own).
- **The NVIDIA warning now names the entry "Heiss OS, safe graphics" and `nvidia-open-lts`; the "DKMS" sentence is gone.** A test ties the text to the title in the script. It does not claim that the LTS kernel is installed with the driver; that is a later step.

## 2026-11-15 (GUI check without a display)

- **`scripts/render-gui.py` renders the real QML offscreen on fixture data; it is a developer tool, not a CI step.** Why: no screenshots can be taken in the build VM, and the owner should not have to find layout bugs one by one. CI cannot run it without installing `pyside6` (a very large download); the new `qml-lint` job installs only `qt6-declarative` (about 20 MiB) and runs `qmllint` plus a check for `on<Capital>` property names, which are the two bug classes the render found. The script's bridge object is a synchronous copy of the glue in `app.py`; the QML is the shipped one (for the light theme a copy with the colour-scheme test replaced, because the offscreen platform has no colour scheme).
- **A QML property must never be named `on<Capital>`.** Why: QML reads it as a signal handler, the colour binding is never used and the text is drawn black. `onAccent` is now `textOnAccent` in both apps.

## 2026-11-15 (hardware pages polish)

- **One shared place for readable hardware names: `heiss_core.hardware` (`CPU_VENDORS`, `PCI_VENDORS`, `cpu_vendor_name`, `pci_vendor_name`, `gpu_vendor_names`).** Why: the wizard showed the raw `GenuineIntel` and `8086:9a49` while the Control Center showed "Intel". An unknown CPU string is never echoed (it shows as unknown/other). Hygon and Centaur are in the CPU map because those are the other `vendor_id` strings Linux reports on x86; not verified on such hardware.
- **A hardware profile may carry a short `recovery` text next to the full `warnings`.** Why: the wizard has no room for the PCI-threshold and kernel detail, and cutting a sentence in the middle (the old 300-character limit) hid the safe-graphics step. The wizard shows `recovery`, the Control Center shows `warnings` whole (limit 1200, a test checks every shipped text fits); a test requires the full text to start with the recovery text.
- **A driver that can be installed is shown as "Can be installed" in a neutral colour, and a driver warning uses the token `neutral_text` (amber), not the error red.** Why: neither is a failure; red stays for real problems. The colour literals in the QML are checked against `scripts/heiss_tokens.py` by a test.
- **`inter-font` is now in the ISO package list (reverses the 2026-11-11 line "optional dependency only").** Why: `kdeglobals` and the QML ask for Inter; without it the live system showed a fallback face. The owner's task text said it was added in PR 87, but PR 87 did not add it; this PR does. `pacman -Si inter-font`: extra, 4.1-1. ISO size change not measured.
- **QML `Text` and `TextField` do not take the `ApplicationWindow` font.** The search field now sets its family itself (Inter if present, else `sans-serif`). The other `Text` items still use the platform default font, which on a Heiss system is Inter through `kdeglobals`.

## 2026-11-15 (security-reviewer method)

- **The `security-reviewer` agent now has a written threat model, a method (risk ranking, source-to-sink tracing, variant search over the whole tree, insecure-defaults list, verify-before-report), 13 Heiss-specific checks and a severity rubric; every finding names file and line, the attacker kind, the exact attacker action and the fix.** Why: the first version was a flat checklist and could not say how serious a finding was or whether the same bug existed elsewhere. It also has an audit mode for code that already exists.
- **It was informed by the public Trail of Bits skills repository (CC-BY-SA-4.0), read-only through the GitHub API.** Nothing was cloned, installed, enabled or run, and no text was copied: the licence is share-alike, so the checklist is written in our own words. The statement and the link are in `docs/security/REVIEW-METHOD.md`.
- **Findings of an audit are fixed in separate small PRs, one at a time, after this PR is merged.** HIGH and MEDIUM first.

## 2026-11-15 (audit of the privileged code: fixes and one accepted risk)

- **Accepted risk, deferred by the owner: the publish secrets (`REPO_GPG_PRIVATE_KEY`, `REPO_GPG_KEY_ID`, `REPO_PUSH_TOKEN`) are plain repository secrets without a GitHub Environment.** The only guard is `if: github.ref == 'refs/heads/main'` in `.github/workflows/publish-repo.yml`, which sits in a file a branch can change. Attacker: someone who can push a branch (a collaborator with write access, or a stolen token with `contents: write`) removes the `if` in their branch and starts the workflow by hand; the branch's copy of the workflow then receives the signing key and the push token, and could sign and publish packages that every installed system trusts. Today the owner is the only person with write access, so the risk is accepted. **Trigger to fix it: before adding any collaborator with write access, and before the first public release.** The fix is a GitHub Environment (for example `publish`) that holds the three secrets and allows deployment from `main` only, with `environment: publish` on the job and the existing `if` kept as a second layer; it needs a setting in the GitHub repository, so the owner does it.
- **Every action in the workflows is pinned to a full commit SHA with a version comment** (`actions/checkout` v4.4.0, `11d5960a326750d5838078e36cf38b85af677262`, commit date 2026-07-16, found with `gh api`). Why: a tag can be moved or re-pointed by whoever controls the action, and in `publish-repo.yml` the job holds the signing key. A test fails if any `uses:` is not a 40-character SHA with a `# vX.Y.Z` comment. `guards.yml` (Tier A, no secrets, `contents: read`) was pinned afterwards in its own PR with the owner's explicit approval of that item (2026-11-15) and a regenerated `protected.sha256`. Raising the version is a manual change (check the new SHA, change both the SHA and the comment); nothing updates it automatically.

## 2026-11-15 (Calamares AUR recipe pinned)

- **`scripts/heiss-calamares-build.sh` takes the AUR recipe at one reviewed commit and checks the PKGBUILD hash; the checking is in the new `scripts/heiss-aur-fetch.sh`.** Why (audit MEDIUM 3): the script cloned the AUR head and ran `makepkg -s --noconfirm` straight away, so a taken-over maintainer account or a later push would run its code on the build host and put it into the ISO that every user installs; the earlier approval of Calamares from the AUR (recorded in CLAUDE.md, "Решения", not as its own entry here) covered the package, not an unpinned recipe. This entry is also the per-item AUR record for Calamares that the rule at the top of this file asks for. Pins: AUR commit `167151beb537c06cb75c8dbfd409799ba308bb66` (version 3.4.2-2) and PKGBUILD sha256 `8ea0869d8f366ef043693815000aabf7caefedb52cf53a9150f46194cb2bd9c2`. Reviewed by reading the PKGBUILD as data (nothing from it was run): one source, the release tarball from `codeberg.org/Calamares/calamares` with a sha256 in the PKGBUILD, no install script, a plain cmake build. makepkg checks the tarball against that sha256, so the pins cover the source too. The Heiss layout patch is applied after the check. The fetch script clones with `--no-checkout` and no git hooks or templates, refuses a target that is not a clean absolute path three levels deep or that goes through a symlink, and deletes the target again if any check fails, so a failed fetch leaves nothing that could be built by hand.
- **`makepkg` is no longer run with `--noconfirm` by default.** Dependencies come from the signed official repositories and pacman asks before installing them; `HEISS_NONINTERACTIVE=1` restores `--noconfirm` for an unattended build in a throwaway VM.
- **Moving to a new Calamares version is a manual review:** read `git diff OLD..NEW` of the AUR repository, then change both pins. Nothing updates them automatically. `heiss-calamares-build.sh` is Tier A (this change was approved by the owner as audit item MEDIUM 3 and needs the `design-approved` label); the new `heiss-aur-fetch.sh` is not on the protected list.

## 2026-11-15 (audit LOW: trailing newline in validators)

- **Every anchored validator in the helper and the manifest code uses `fullmatch`.** Why: `re.match(r"^...$")` accepts a trailing newline (`"abc\n"`), and `SNAPSHOT_DESC_RE` did let one through to `snapper --description` (not exploitable: argv is a list and the audit log replaces control characters; the package and unit checks were also stopped by the allowlist). Changed: `policy.py` (3), `hardware.py` (4), `hardware_view.py` (2), `updates_view.py` (1). A source scan test (`core/tests/test_regex_anchors.py`) finds every `NAME = re.compile(...)` (any name) in `core`, `helper`, `welcome` and `control` and fails when that name is used with `.match(` in the same file, or when `re.match(r"^...` is called with a literal. It does not follow a pattern used through another module (`mf.PKG_RE.match`); `STEP_RE` (progress lines from a child process) is the one named exception. Tests: a trailing-newline case in `helper/tests/test_helper.py` and `core/tests/test_hardware.py`.

## 2026-11-15 (audit LOW: mode of /var/lib/heiss/state.json)

- **The state file is written 0644 (world-readable, root-writable) and its directory 0755; every other file written by `atomic_write` stays 0600 unless the caller asks for another mode.** Why: `mkstemp` created the file 0600 and nothing changed it, so after the helper's first write an ordinary user could not read it: `heiss profile apply|diff` (which reads it for the plan) failed with a traceback and the Control Center cards for profiles and packages showed an error. The file lists only package, service and flatpak names (the same names the manifests publish), so reading it gives an attacker nothing; writing it is still root-only (and the helper, not a client, writes it, see SECURITY-MODEL section 4). `atomic_write` now sets the mode on the open descriptor (`fchmod`), so the umask of the service no longer matters. A file written by an earlier version stays 0600 until the next successful helper step rewrites it. Note for later: when the helper gets a method that writes `/etc/heiss/profile.toml` (read by the Control Center and `heiss check` as the user), it must pass `mode=0o644`; the default 0600 would break those readers the same way. The helper audit log (`/var/log/heiss/audit.log`, 0640 in a 0750 directory) is deliberately not readable by users. pkgrel raised for the packages changed by this and the previous fix (heiss-core 11, heiss-helper 3, heiss-control 13): pacman offers an update only when the version changes. `heiss` now prints `heiss: ...Permission denied` and exits 1 for an unreadable state or answers file instead of a traceback.

## 2026-11-15 (audit LOW: the helper's command time limit)

- **The 3600 s limit of a helper command is enforced by the loop that reads its output (`poll` with a deadline; not `select`, which fails for descriptors above 1023 in a long-running service); the command's process group gets SIGTERM, then (after the leader exited or 10 s passed) SIGKILL, so a group member that ignores SIGTERM does not survive the leader; the exit code is 124.** Why: the limit was only checked by `p.wait(timeout)` after the loop that reads the output had ended, so a pacman that hung without printing anything and without exiting kept the single job slot (the `_busy` lock) until the helper was restarted. Reading with a deadline instead of a watchdog thread also covers a grandchild that left the process group (`setsid`) and keeps the pipe open: the reader stops at the limit, and earlier when the command itself has exited. SIGTERM first because pacman then removes its `db.lck`; a plain SIGKILL would leave a stale lock that blocks every later pacman call. `start_new_session` lets the group kill reach scriptlets and download helpers. If the reader fails (the emit callback raises) the command is stopped instead of left running. All waits after a kill are bounded. A command that closes its output but keeps working is waited for until the limit (an early version stopped it at once; found by the QA run and covered by a test); a `None` limit means no limit. Known and left alone: a process in uninterruptible sleep cannot be killed and is abandoned after the grace period; a quiet grandchild that called `setsid` is outside the group and outlives the command (the reader no longer waits for it); a missing binary raises `FileNotFoundError` out of `run`, which `execute` turns into a failed job; the single-job lock in `dispatch.py` is not released if `audit.record` or `Thread.start()` raises right after it is taken (older, separate LOW). Tests run real processes (`helper/tests/test_runner.py`, 16 tests); the old runner hangs them. heiss-helper pkgrel 4.

## 2026-11-15 (audit LOW: workflow credentials)

- **Every `actions/checkout` in `core.yml` has `persist-credentials: false`, and the publish step passes the push header to its one `git push` through the environment (`GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0`, `GIT_CONFIG_VALUE_0`), not as `git -c ...` on the command line, and the key is scoped to `https://github.com/` (`http.https://github.com/.extraheader`), so git sends the header to no other host.** Why: with `persist-credentials` left on, the job token stays in `.git/config` for every later step (read-only here, `contents: read`, so low); and an argument is visible in `ps` to every process on the runner, an environment variable of a single process is not (the value was already masked in the log). `publish-repo.yml` already had `persist-credentials: false`. A test (`core/tests/test_workflows.py`) fails when a checkout lacks the option or when the header is put back on a command line. Not done: `guards.yml` is a Tier A file and still checks out with the default; it needs a `design-approved` PR (the test lists it as a pending exception). The environment form needs git 2.31 or newer; the Arch container has 2.5x.

## 2026-11-15 (audit LOW: guards.yml persist-credentials)

- **Both checkouts in `.github/workflows/guards.yml` (Tier A) have `persist-credentials: false`.** Why: the job token should not stay in `.git/config` for later steps; this was the last checkout without the option (the entry "audit LOW: workflow credentials" above lists it as pending). The owner approved this item by name on 2026-11-15; the PR carries the `design-approved` label and a regenerated `protected.sha256` (one line). The pending-exception set in `core/tests/test_workflows.py` is now empty. The guards jobs only run local scripts (`git ls-files`, generators, unit tests), so they need no token after the checkout.

## 2026-11-15 (audit LOW: the environment of the apply child is an allowlist)

- **The child that runs `heiss profile apply` (wizard `heiss_welcome.applier`, Control Center `heiss_control.runner`) gets only a list of named variables and a fixed `PATH=/usr/bin:/bin`, not the user's environment minus a list of bad names.** Allowed: `HOME`, `USER`, `LOGNAME`, `LANG`, `LANGUAGE`, `TZ`, `TERM`, `LC_*`, `XDG_RUNTIME_DIR`, `XDG_SESSION_ID`, `XDG_SESSION_TYPE`, `XDG_CURRENT_DESKTOP`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `DBUS_SESSION_BUS_ADDRESS`, `DISPLAY`, `WAYLAND_DISPLAY`, `XAUTHORITY`. Why: the denylist worked (`-I` and `cwd=/` already neutralised the Python variables) but it is fragile: the next variable that changes loading or behaviour (a new `GIT_*`, `BASH_ENV`, a `*_PATH` of some library) would pass. The fixed `PATH` also stops a user `PATH` entry from replacing `pacman`, `systemctl` or `flatpak`, which the child runs by name before it reaches the helper. The helper itself never takes its environment from a client (it runs with its own fixed one). Two copies, kept equal by `core/tests/test_child_env.py`. Not needed in the child and therefore not passed: `DBUS_SYSTEM_BUS_ADDRESS` (the system bus is the default socket), `XDG_DATA_DIRS`, `XDG_CONFIG_DIRS`, `SHELL`, `SSH_AUTH_SOCK`, `EDITOR`. pkgrel raised (heiss-welcome 9, heiss-control 14).

