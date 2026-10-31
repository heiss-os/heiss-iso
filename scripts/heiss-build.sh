#!/usr/bin/env bash
# Heiss OS: чистая сборка ISO и копирование в общую папку VirtualBox.
# Usage: [HEISS_FAST=1] heiss-build.sh [--dry-run]
#   HEISS_FAST=1  fast test build: zstd squashfs (bigger ISO, much quicker). Default is xz.
#   --dry-run  only render the profile (substitute @LOCALREPO@ in pacman.conf) and exit.
set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCALREPO="${LOCALREPO:-$HOME/localrepo}"
cd "$REPO_DIR"

echo "==> Подготовка профиля (локальный репозиторий: $LOCALREPO)"
[[ -d "$LOCALREPO" ]] || { echo "Нет $LOCALREPO: сначала запустите scripts/heiss-calamares-build.sh" >&2; [[ $DRY_RUN -eq 1 ]] || exit 1; }
RENDERED="$(mktemp -d)"
trap 'rm -rf "$RENDERED"' EXIT
cp -a profile/. "$RENDERED/"
sed -i "s#@LOCALREPO@#$LOCALREPO#g" "$RENDERED/pacman.conf"
if grep -q '@LOCALREPO@' "$RENDERED/pacman.conf"; then echo "Плейсхолдер не заменён" >&2; exit 1; fi

if [[ "${HEISS_FAST:-0}" == "1" ]]; then
    echo "==> HEISS_FAST=1: zstd для squashfs (тестовая сборка, ISO больше)"
    sed -i "s#^airootfs_image_tool_options=.*#airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '3' '-b' '1M')#" "$RENDERED/profiledef.sh"
    if ! grep -q "'zstd'" "$RENDERED/profiledef.sh"; then echo "Не удалось применить zstd в profiledef.sh" >&2; exit 1; fi
fi

if [[ $DRY_RUN -eq 1 ]]; then
    echo "==> Dry run: итоговая секция [heiss-local]"
    grep -A2 '^\[heiss-local\]' "$RENDERED/pacman.conf"
    grep '^airootfs_image_tool_options' "$RENDERED/profiledef.sh"
    exit 0
fi

echo "==> Очистка старой сборки"
sudo rm -rf ~/archiso-work
sudo rm -f out/*.iso

echo "==> Сборка образа (15-40 минут). На вопрос [Y/n] нажмите Enter."
sudo mkarchiso -v -w ~/archiso-work -o out "$RENDERED" 2>&1 | tee ~/build.log

echo "==> Копирование в общую папку"
mkdir -p ~/share
mountpoint -q ~/share || sudo mount -t vboxsf share ~/share -o uid="$(id -u)",gid="$(id -g)"
rm -f ~/share/heiss-*.iso
cp out/heiss-*.iso ~/share/

echo
ls -lh out ~/share
echo "Готово. Образ лежит в папке vbox-share на вашем компьютере."
