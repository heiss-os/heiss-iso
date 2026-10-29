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

echo "==> Сборка (10-30 минут). Пароль sudo понадобится для установки зависимостей."
makepkg -s --noconfirm 2>&1 | tee ~/calamares-build.log

echo "==> Добавляю пакеты в локальный репозиторий"
cp -v ./*.pkg.tar.zst ~/localrepo/
cd ~/localrepo
repo-add heiss-local.db.tar.zst ./*.pkg.tar.zst

echo
ls -lh ~/localrepo
echo "Готово. Пакет Calamares собран."
