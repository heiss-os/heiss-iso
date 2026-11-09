# Default applications and file associations

File: `profile/airootfs/etc/xdg/mimeapps.list` (XDG system-wide defaults). It reaches the live session and, through the squashfs copy, every installed system; new users inherit it, and a user's own `~/.config/mimeapps.list` wins. One default per job, only applications of the Base profile.

| Job | Default | Package | What it opens |
|---|---|---|---|
| Folders | `org.kde.dolphin.desktop` | dolphin | `inode/directory` |
| Web | `firefox.desktop` | firefox | `http`, `https`, `about` links, HTML, XHTML |
| Text and code | `org.kde.kate.desktop` | kate | plain text, Markdown, CSV, logs, JSON, XML, YAML, TOML, patches, shell, C/C++/Python/Java/Go/Lua/CSS/JS sources, desktop files |
| Images | `org.kde.gwenview.desktop` | gwenview | PNG, JPEG, GIF, WebP, BMP, TIFF, SVG, AVIF, HEIF/HEIC, JXL, icons |
| Documents | `org.kde.okular.desktop` | okular | PDF, EPUB, DjVu, comic books, XPS, PostScript |
| Video and audio | `org.kde.haruna.desktop` | haruna | common video and audio containers and codecs |
| Archives | `org.kde.ark.desktop` | ark | zip, tar and compressed tars, 7z, rar, gz, bz2, xz, zstd, lz4, cpio, deb |
| Password databases | `org.keepassxc.KeePassXC.desktop` | keepassxc | KeePass 2 databases |

Deliberately NOT set: `mailto:` (Base has no mail client; the mail add-on can set it later), terminal and file-manager alternatives (kitty and Thunar are add-ons and never the default), Office formats (the office suite is an add-on).

Where tools disagree on a type's name, both the alias and the canonical name are listed (for example `video/x-matroska` and `video/matroska`). Four candidate types do not exist in shared-mime-info and were dropped.

## How it is checked

`scripts/check-mimeapps.py` (also a unit test, `tests/test_mimeapps.py`): syntax, one application per type, MIME type names against shared-mime-info, and, in CI after `pacman -Fy`, that every desktop file is shipped by a package of the Base profile. The Base set is the closure of the `base` manifest.

## Not verified

- That a running Plasma session, Dolphin and `xdg-open` really pick these defaults from `/etc/xdg/mimeapps.list` (the XDG specification and KDE's mime handling say they should; no VM run yet).
- That the `.desktop` names match the installed versions in every case: CI checks the file names in the package database, not the behaviour.
- "Open terminal here", Dolphin's embedded terminal and context-menu coherence are separate Phase 4 items.
- Existing installations keep their own per-user choices.

Test in the VM: `xdg-mime query default application/pdf` (expect `org.kde.okular.desktop`), `xdg-mime query default x-scheme-handler/https`, double-click a PDF, an image, a zip and a video in Dolphin, and open a link from a terminal with `xdg-open https://example.org`. Send the results.
