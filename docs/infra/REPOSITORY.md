# Hosted package repository and signing (design, Phase 0)

## Problem

Profiles are metapackages. `[heiss-local]` is a `file://` directory on the build machine; `heiss-cleanup.sh` deletes it from the installed system's `pacman.conf`. After installation nothing could install a profile or receive Heiss updates.

## Design

- **Hosting:** a separate GitHub repository `heiss-os/heiss-repo`, served by GitHub Pages at a stable URL, layout `https://<pages-url>/$arch/` with `heiss.db`, `heiss.files` and package files. Alternative: release assets. Packages are binary files, so keep them out of `heiss-iso` (rule: no files over 20 MB in the repo). Note: GitHub Pages has a size and bandwidth limit; NOT VERIFIED for our package volume.
- **Build:** a GitHub Actions job in `heiss-iso` builds each `packages/*/PKGBUILD` in a clean Arch container (`archlinux:base-devel`), signs packages and the database, runs `repo-add --sign`, and pushes the result to `heiss-repo`.
- **Signing:** a dedicated GPG key. The private key exists only as a CI secret. It is never in a repository and never in an assistant session. The owner creates it.
- **Keyring:** package `heiss-keyring` ships the public key and a `*-trusted` file with the pinned key ID. Installed systems trust it via `pacman-key --populate heiss`, appended to `heiss-cleanup.sh` after the existing `pacman-key --init --populate archlinux` step (append only, behind a switch).
- **pacman.conf on the installed system:** add
  ```
  [heiss]
  SigLevel = Required DatabaseRequired
  Server = https://<pages-url>/$arch
  ```
  in addition to the official mirrors. The ISO build keeps using `[heiss-local]` offline.
- **Order of trust at install time:** the keyring package must be in the ISO, otherwise the first `pacman -Sy` against `[heiss]` fails. Bootstrapping risk: the key ID must also be printed in the docs so users can compare.

## Behavior offline and on network loss

- Offline: official and Heiss packages already installed keep working. Profile changes are queued in "Pending actions" and run later. Nothing is half-installed because pacman transactions are atomic per transaction.
- Network drops during a profile install: pacman aborts the transaction before applying it when a download fails (packages are fetched first). The helper reports the failure and the plan stays resumable. NOT VERIFIED for every failure mode.

## Checklist for the owner (in Russian, simple)

1. Создайте на GitHub в организации `heiss-os` новый пустой репозиторий `heiss-repo` (Public). Ничего в него не добавляйте.
2. В `heiss-repo` откройте Settings -> Pages. Source: «Deploy from a branch», ветка `gh-pages`, папка `/ (root)`. Сохраните. Запишите адрес сайта.
3. На своём компьютере (не в виртуалке Claude) создайте ключ подписи. Выполните и ответьте на вопросы (имя «Heiss OS Repo», почту любую рабочую, срок 2 года):
   `gpg --full-generate-key`
4. Посмотрите номер ключа: `gpg --list-secret-keys --keyid-format LONG`. Запишите длинный номер (после `rsa4096/`).
5. Экспортируйте закрытый ключ в текстовый файл: `gpg --armor --export-secret-keys НОМЕР > heiss-private.asc`. Этот файл никому не показывайте и не кладите в репозиторий.
6. В репозитории `heiss-iso` откройте Settings -> Secrets and variables -> Actions -> New repository secret. Создайте секрет `REPO_GPG_PRIVATE_KEY` и вставьте туда содержимое `heiss-private.asc`. Создайте секрет `REPO_GPG_KEY_ID` с номером ключа. Если ключ с паролем: секрет `REPO_GPG_PASSPHRASE`.
7. Экспортируйте открытый ключ: `gpg --armor --export НОМЕР > heiss-public.asc`. Этот файл можно показать мне и добавить в репозиторий.
8. Удалите `heiss-private.asc` с диска после того, как положили его в секрет, и сделайте резервную копию ключа в надёжном месте (иначе его потеря = смена ключа для всех).
9. Создайте токен для публикации в `heiss-repo`: Settings -> Developer settings -> Fine-grained tokens, доступ только к `heiss-repo`, право Contents: Read and write. Добавьте как секрет `REPO_PUSH_TOKEN` в `heiss-iso`.
10. Напишите мне «готово» и пришлите номер ключа, адрес Pages и файл `heiss-public.asc`.

Не присылайте мне закрытый ключ и токены.
