#!/usr/bin/env bash
# Heiss OS: собирает пакет Calamares из AUR и кладёт его в локальный репозиторий ~/localrepo.
# Запускать в виртуалке heiss-build под обычным пользователем (не root).
set -euo pipefail

MAKEFLAGS="-j$(nproc)"
export MAKEFLAGS
mkdir -p ~/aur ~/localrepo
cd ~/aur

# The recipe is taken from the AUR at ONE reviewed commit and its PKGBUILD must match the pinned sha256
# (see scripts/heiss-aur-fetch.sh). Reviewed 2026-11-15: version 3.4.2-2, one source (the release tarball from
# codeberg.org/Calamares/calamares with a sha256 in the PKGBUILD), no install script, a plain cmake build.
# To update: read the diff of the AUR repository between this commit and the new one, then change both values.
CALAMARES_AUR_COMMIT=167151beb537c06cb75c8dbfd409799ba308bb66
CALAMARES_PKGBUILD_SHA256=8ea0869d8f366ef043693815000aabf7caefedb52cf53a9150f46194cb2bd9c2

echo "==> Скачиваю рецепт сборки (PKGBUILD) из AUR на проверенном коммите"
"$(dirname "$(readlink -f "$0")")/heiss-aur-fetch.sh" \
    https://aur.archlinux.org/calamares.git "$HOME/aur/calamares" \
    "$CALAMARES_AUR_COMMIT" "$CALAMARES_PKGBUILD_SHA256"
cd calamares

echo
echo "==> Что будет собираться:"
grep -nE '^(pkgver|pkgrel|url|source)' PKGBUILD || true
echo

# [switch] HEISS_PATCH_LAYOUT=1 (default): narrow sidebar (56 px) and even Back/Next/Cancel spacing.
# Set HEISS_PATCH_LAYOUT=0 to build stock Calamares.
if [ "${HEISS_PATCH_LAYOUT:-1}" = "1" ]; then
    echo "==> Применяю патч раскладки Heiss (узкая боковая панель, ровные кнопки)"
    cp "$(dirname "$(readlink -f "$0")")/patches/calamares-heiss-layout.patch" "$PWD/heiss-layout.patch"
    # apply inside build(), right after the source directory is known
    sed -i '/local _pkgsrc_dir=/a\  patch -d "$_pkgsrc_dir" -p1 < "$startdir/heiss-layout.patch"' PKGBUILD
    grep -n 'heiss-layout.patch' PKGBUILD
fi

echo "==> Сборка (10-30 минут). Понадобятся пароль sudo и подтверждение pacman для установки зависимостей."
# dependencies come from the signed official repositories; pacman asks before installing them.
# HEISS_NONINTERACTIVE=1 passes --noconfirm (for an unattended build in a throwaway VM).
makepkg_opts=()
[ "${HEISS_NONINTERACTIVE:-0}" = "1" ] && makepkg_opts+=(--noconfirm)
makepkg -s "${makepkg_opts[@]}" 2>&1 | tee ~/calamares-build.log

echo "==> Добавляю пакеты в локальный репозиторий"
cp -v ./*.pkg.tar.zst ~/localrepo/
cd ~/localrepo
repo-add heiss-local.db.tar.zst ./*.pkg.tar.zst

echo
ls -lh ~/localrepo
echo "Готово. Пакет Calamares собран."
