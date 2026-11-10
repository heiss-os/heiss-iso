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

## 2026-11-10 (apply wiring, made by the assistant)

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

## 2026-11-10 (file associations, made by the assistant)

- **Defaults live in `/etc/xdg/mimeapps.list`** (system-wide XDG file): reaches the live session, the installed system and new users, and per-user choices still win. New file, no existing config edited.
- **One app per job, only Base apps:** Dolphin, Firefox, Kate, Gwenview, Okular, Haruna (video and audio), Ark, KeePassXC. No `mailto:` handler because Base has no mail client.
- **Aliases listed next to canonical MIME names** where tools disagree; unknown types were dropped by checking against shared-mime-info.
- **Guard in CI:** every desktop file must exist in a Base package (`pacman -F`), so a renamed desktop file or a package removed from Base fails the build instead of silently breaking a default.

## 2026-11-10 (GTK, made by the assistant)

- **No GTK configuration is shipped yet; Plasma's `kde-gtk-config` stays the single owner of GTK settings.** Why: the package database shows it already ships the kded `gtkconfig` module, a GTK3 color-reload module, Breeze window-decoration CSS and depends on `xsettingsd` and `xdg-desktop-portal-gtk`. Writing the same files from Heiss would race with it, and I cannot run GTK here to see the actual files.
- **`heiss-gtk-audit` (read-only, in `heiss-core`) collects the facts in the VM.** The next GTK step is chosen from its output (decision table in `docs/design/GTK.md`). Generated token CSS for GTK stays staged in `branding/tokens/generated/`.
- **GTK prerequisites are guarded by a test:** kde-gtk-config, breeze-gtk and both portal backends must stay in every profile.

## 2026-11-10 (theme sync, made by the assistant)

- **`heiss theme sync` replaces the shell logic** (the entry point `heiss-theme-sync.sh`, the path unit and the autostart entry stay). Python in heiss-core so it can be unit tested against a scripted desktop; one log line per target; failures are visible; exit code 1 only on failure.
- **Set only what nothing else sets** (launcher icon, Konsole default profile and running sessions); **check the rest** (Plasma consistency against the Look-and-Feel defaults, kde-gtk-config module, GSettings, portal) and report differences instead of writing Plasma-owned files (Tier B).
- **kitty follows the portal** through `*-theme.auto.conf` files; no sync target writes kitty config.
- **New package `heiss-theme`** (generated from the tokens: Konsole schemes and profiles, `/etc/xdg/konsolerc`, kitty files) and it is in the ISO list. Terminal font size token `terminal` = 11 pt.
- **CI guard against file conflicts:** no file of our packages may also be shipped by an official package (`pacman -F`), because pacstrap would fail the ISO build.
- **Stacked on PR 47** (the GTK audit) because both bump the pkgrel of heiss-core.

## 2026-11-10 (releng leftovers, made by the assistant on the owner's instruction)

- **37 packages removed from `profile/packages.x86_64`** (about 118 MiB installed, before squashfs compression; real ISO size NOT measured). Groups: Cyber tools (`nmap`, `tcpdump`, `ddrescue`, `testdisk`, `tpm2-tools`, `sequoia-sq`, `openpgp-card-tools`, `bind`, `ldns`, `ndisc6`), imaging and rescue (`clonezilla`, `partimage`, `partclone`, `fsarchiver`), terminal curiosities (`lynx`, `irssi`, `mc`, `lftp`), legacy dial-up and VPN clients (`pptpclient`, `wvdial`, `xl2tpd`, `vpnc`, `openconnect`, `openvpn`, `linux-atm`, `wireless_tools`), unused storage tools (`bcachefs-tools`, `jfsutils`, `nilfs-utils`, `open-iscsi`, `mmc-utils`, `sdparm`, `sg3_utils`, `lsscsi`, `b43-fwcutter`), `dnsmasq`, `usbmuxd`.
- **Checked, not assumed:** the dependency closure of the remaining list plus the `essentials` and `base` manifests was resolved against the sync databases in an empty root; none of the removed packages is pulled in. Two candidates were kept for that reason: `ppp` and `pcsclite` are needed by other packages.
- **Deliberately kept:** everything the installer, the boot menu and the live session need (`syslinux`, `memtest86+`, `edk2-shell`, `mkinitcpio-archiso`, `nbd`, `darkhttpd`, `nfs-utils`, filesystem tools for the Calamares partition page, `dmraid`, `mdadm`), plus `vim`, `tmux`, `screen`, `nano`, `less`. `heiss-cleanup.sh` is not touched: its removal list still covers the live-only packages.
- **Consequence:** Calamares no longer offers JFS, NILFS2 and bcachefs for new partitions (their tools are gone). nmap and tcpdump return with the Cyber profile.
- **Not verified:** ISO build, boot, installation. Needs a rebuild and the VM check from `docs/ISO-E2E-TEST.md`.

## 2026-11-10 (keyboard shortcuts, made by the assistant)

- **No custom shortcuts added.** The packages already declare `Meta+E` (Dolphin), `Ctrl+Alt+T` (Konsole), `Meta+I` (System Settings), `Meta+Esc` (System Monitor), `Meta+.` (emoji), `Calculator` (KCalc); these are read from the desktop files, not remembered. A `kglobalshortcutsrc` of our own would override Plasma defaults I cannot list on the build VM (KWin and KRunner register theirs in code) and is Tier B territory.
- **Guard instead:** `scripts/check-shortcuts.py` finds key collisions between desktop files and keeps `docs/design/SHORTCUTS.md` true (CI downloads the Base apps and compares).
- **Open:** the real list of Plasma/KWin shortcuts needs the VM (`docs/design/SHORTCUTS.md`, section "NOT verified").
