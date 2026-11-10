# Launcher menu

Goal: one menu entry per job, no developer or diagnostic leftovers in Base.

## How entries are hidden

A file with the same desktop id in `/usr/local/share/applications` wins over the one in `/usr/share/applications` (XDG data directories: `/usr/local/share` comes first). Our stubs in `profile/airootfs/usr/local/share/applications/` contain only `Type`, `Name`, `NoDisplay=true`, `Hidden=true` and no `Exec`, so they cannot drift from the package. `Hidden=true` means "treat as not installed" in the desktop entry specification. `/usr/local` is part of the squashfs, so the installed system gets the stubs too, and no package file is touched (no pacstrap conflict). Guard: `scripts/check-menu.py` (CI with the file database fails a stub whose entry no longer exists, and refuses to hide a dock pin or a default application).

## What is hidden and why

Found by reading the `.desktop` files of the dependency closure of the ISO list plus the `essentials` and `base` manifests (51 packages with entries, 154 files).

| Entry | Package | Why hidden | Pulled in by |
|---|---|---|---|
| KWrite | kate | second text editor; Kate is the default | same package |
| Vim | vim | terminal editor with a menu entry; Kate is the default | ISO list (releng) |
| mpv Media Player | mpv | second video player; Haruna is the default | mpvqt (Haruna) |
| Qt Assistant, Qt Widgets Designer, Qt Linguist, Qt D-Bus Viewer | qt6-tools | developer tools | kwin, plasma-workspace, aurorae |
| Qt V4L2 test Utility, Qt V4L2 video capture utility | v4l-utils | diagnostic tools | ffmpeg, sane |
| Hardware Locality lstopo | hwloc | diagnostic tool | onetbb |

These tools are not removed: other packages need them. The Developer profile can show them again by deleting the stub in `/usr/local/share/applications` (not automated yet).

## Checked and left alone

- `kdesystemsettings.desktop` has `NotShowIn=KDE`, so Plasma already shows only "System Settings".
- Okular's 15 `okularApplication_*` files, the `kcm_*` files, Discover's helper entries and the portal entries are `NoDisplay` or MIME handlers; they do not appear in the menu.
- Visible and kept: Ark, Discover, Dolphin, Filelight, Gwenview, Haruna, Kate, KCalc, KeePassXC, Info Center, Menu Editor, Konsole, Okular, KDE Partition Manager, Emoji Selector, System Monitor, System Settings, Spectacle (Spectacle from its package name; not downloaded for inspection).

## Not verified

- The result in the running menu (needs a screenshot of Kickoff, Dark and Light). Name collisions after translation (ru) were not checked.
- Entries of packages outside the closure I inspected (print-manager, cups, firefox, spectacle were not opened: epoch in the file name or size). Their `NoDisplay` state is from memory of the packages, not read.
- Whether hiding `mpv`/`vim` changes the "Open With" lists in Dolphin as expected.
