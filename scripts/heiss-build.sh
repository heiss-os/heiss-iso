#!/usr/bin/env bash
# Heiss OS: чистая сборка ISO и копирование в общую папку VirtualBox.
set -euo pipefail

cd ~/heiss-iso

echo "==> Очистка старой сборки"
sudo rm -rf ~/archiso-work
sudo rm -f out/*.iso

echo "==> Сборка образа (15-40 минут). На вопрос [Y/n] нажмите Enter."
sudo mkarchiso -v -w ~/archiso-work -o out profile 2>&1 | tee ~/build.log

echo "==> Копирование в общую папку"
mkdir -p ~/share
mountpoint -q ~/share || sudo mount -t vboxsf share ~/share -o uid="$(id -u)",gid="$(id -g)"
rm -f ~/share/heiss-*.iso
cp out/heiss-*.iso ~/share/

echo
ls -lh out ~/share
echo "Готово. Образ лежит в папке vbox-share на вашем компьютере."
