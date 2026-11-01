#!/usr/bin/env bash
# Heiss OS: собирает пакет Calamares из AUR и кладёт его в локальный репозиторий ~/localrepo.
# Запускать в виртуалке heiss-build под обычным пользователем (не root).
set -euo pipefail

export MAKEFLAGS="-j$(nproc)"
mkdir -p ~/aur ~/localrepo
cd ~/aur
rm -rf calamares

echo "==> Скачиваю рецепт сборки (PKGBUILD) из AUR"
git clone https://aur.archlinux.org/calamares.git
cd calamares

echo
echo "==> Что будет собираться (проверьте глазами: версия и источники):"
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

echo "==> Сборка (10-30 минут). Пароль sudo понадобится для установки зависимостей."
makepkg -s --noconfirm 2>&1 | tee ~/calamares-build.log

echo "==> Добавляю пакеты в локальный репозиторий"
cp -v ./*.pkg.tar.zst ~/localrepo/
cd ~/localrepo
repo-add heiss-local.db.tar.zst ./*.pkg.tar.zst

echo
ls -lh ~/localrepo
echo "Готово. Пакет Calamares собран."
