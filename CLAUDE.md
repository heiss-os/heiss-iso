# Heiss OS: контекст проекта для Claude Code

Heiß OS (ASCII-вариант: Heiss, техническое имя: `heiss`, читается «Хайсс») это независимый дистрибутив на базе Arch Linux с KDE Plasma. Это не официальный продукт Arch Linux. Цель: красивый, удобный и безопасный дистрибутив для обычных людей и для специалистов по кибербезопасности.

Язык общения с пользователем: русский. Код, комментарии в коде, сообщения коммитов и описания Pull Request: английский.

## Решения, которые уже приняты

- База Arch Linux, образ собирается через `archiso` (профиль основан на `releng`).
- Первая версия только с KDE Plasma (SDDM как менеджер входа). Профили называются **Base, Cyber, Developer, Custom** (раньше: Everyday, Security, Developer, Universal; соответствие Everyday → Base, Security → Cyber, Universal → Custom). Внутренние идентификаторы в готовых ресурсах не переименовываются: пакеты обоев `Heiss-Everyday` и `Heiss-Everyday-Light` остаются как есть. Состав профилей: `profiles/*.toml`, описание: `docs/PROFILES.md`.
- Установщик графический: Calamares 3.4.x (Qt6). В репозиториях Arch его нет, пакет собирается из AUR скриптом `scripts/heiss-calamares-build.sh` в локальный репозиторий `~/localrepo`.
- Без телеметрии. Безопасность по умолчанию: root заблокирован после установки, live-настройки не попадают в установленную систему.
- Единый стиль пока один: **Heiss Dark** (по умолчанию) и **Heiss Light**, нейтральная палитра с песочным акцентом (тёмная `#C9B28A`, светлая `#8C7448`). Шрифты: Inter (интерфейс), JetBrains Mono (код).
- Палитра тёмной темы: окна `#26282B`, панели `#1E1F21`, кнопки `#34373B`, текст `#ECEAE5`, вторичный текст `#A9A7A1`, акцент `#C9B28A`.
- Палитра светлой темы: окна `#F5F3EF`, панели `#ECE9E3`, кнопки `#DEDAD2`, текст `#26282B`, вторичный текст `#6B6963`, акцент `#8C7448`.
- Старые зелёные обои пока остаются, новые нейтральные добавятся отдельным PR.

## Структура репозитория

- `profile/` профиль archiso: `packages.x86_64`, `pacman.conf`, `profiledef.sh`, `syslinux/`, `efiboot/`, `grub/`.
- `profile/airootfs/` файлы, попадающие в образ: настройки Calamares (`etc/calamares/`), тема KDE (`usr/share/color-schemes/`, `usr/share/plasma/look-and-feel/`), автозапуск (`etc/xdg/autostart/`), скрипты (`usr/local/bin/`), брендинг установщика (`usr/share/calamares/branding/heiss/`).
- `profile/hooks/` pacman-хуки только для сборки (не попадают в образ), см. ниже про os-release.
- `scripts/` вспомогательные скрипты сборки и генераторы (`gen-theme.py`, `gen-profile-packages.py`, `check-*.py`).
- `branding/` исходники бренда: логотипы (`logo/`), обои (`wallpapers/`), токены дизайна (`tokens/`, источник правды для цветов и генерируемых тем).
- `core/` движок профилей `heiss-core` (Python, без GUI), `profiles/` манифесты профилей и дополнений, `hardware/` профили железа, `packages/` PKGBUILD (метапакеты генерируются).
- `docs/` документация: `PLAN-STATE.md` (читать в начале каждой сессии), `ARCHITECTURE.md`, `PROFILES.md`, `design/`, `hardware/`, `infra/`. Решения и причины: `DECISIONS.md`.
- Мастер-план: `~/share/heiss-master-prompt.md` (вне репозитория).

## Как собрать образ

```bash
sudo mkarchiso -v -w ~/archiso-work -o out profile
```

Каталоги `out/` и рабочий каталог не коммитятся. Перед сборкой пакет Calamares должен лежать в `~/localrepo` (создаётся `scripts/heiss-calamares-build.sh`). Пакеты Heiss (`heiss-core`, `heiss-helper`, `heiss-profile-*`) собираются в тот же репозиторий скриптом `scripts/heiss-packages-build.sh` (из git HEAD, без незакоммиченных изменений); без этого сборка ISO не найдёт их. Проверка движка и помощника в виртуальной машине: `docs/ISO-E2E-TEST.md`.

Путь локального репозитория: в `profile/pacman.conf` стоит `file://@LOCALREPO@`, `scripts/heiss-build.sh` подставляет `$LOCALREPO` (по умолчанию `$HOME/localrepo`) в отрендеренной копии профиля. Старая проблема с абсолютным путём решена.

## os-release и конфликты с пакетами

В `profile/airootfs/` нельзя держать файлы, которыми владеют пакеты (например `usr/lib/os-release` принадлежит `filesystem`): pacstrap падает с «exists in filesystem», а `NoExtract` проверку конфликтов не отключает. Вместо этого `profile/hooks/90-heiss-os-release.hook` (PostTransaction на `filesystem`) копирует `/usr/share/heiss/os-release` в `/usr/lib/os-release`. mkarchiso вырезает `HookDir` из pacman.conf профиля и всегда использует `<airootfs>/etc/pacman.d/hooks/`, поэтому `scripts/heiss-build.sh` кладёт хук туда в отрендеренной копии профиля (releng сам удаляет его из образа после pacstrap). Для установленной системы работает такой же хук в `usr/share/libalpm/hooks/`.

## Как проверять

Тест в VirtualBox: режим BIOS, 4 ГБ ОЗУ, Video Memory 128 МБ, чистый диск 20-40 ГБ. Ожидается:
1. В меню загрузки Heiss OS, без логотипа Arch.
2. Рабочий стол KDE в нейтральной теме с песочным акцентом, обои Heiss-Everyday, внизу плавающий док.
3. Установщик Calamares открывается сам, в стиле Heiss.
4. После установки на пустой диск и загрузки с диска: сеть работает (`nmcli general status`), `systemctl --failed` пуст, `sudo passwd -S root` показывает `L`, пользователя `liveuser` нет.

## Правила работы с Git

- Ветка `main` защищена: только через Pull Request, прямые коммиты и force push запрещены. Pull Request вливает владелец проекта сам (второго одобряющего нет).
- Название веток: `feat/...`, `fix/...`, `docs/...`, `build/...`. Коммиты: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `build:`, `refactor:`, `test:`.
- Каждый PR небольшой (ориентир до 600 строк без генерируемых файлов) и содержит: что и зачем, «Protected files touched», «Not verified», откат одной строкой.
- В репозиторий не попадают секреты, ключи, образы и файлы больше 20 МБ.
- Организация на GitHub: `heiss-os`, репозиторий `heiss-iso`.

## Защищённые файлы (Tier A)

Утверждённый вид и загрузочная цепочка защищены: список путей в `docs/design/protected-paths.txt`, контрольные суммы в `docs/design/protected.sha256`, проверка `scripts/check-protected.py verify` и задача CI `protected-paths`. Менять такие файлы можно только по явному пункту, одобренному владельцем (метка PR `design-approved`). Подробности: `docs/design/PROTECTION.md`. Существующие значения палитры, шрифты, песочный акцент и последовательность модулей Calamares не менять. Tier B (панель, док, настройки Plasma) только после «ok» по конкретному пункту, Tier C свободен.

## Рабочие правила

- Не выдумывать. Каждый пакет проверять через `pacman -Si`. Что нельзя проверить (UEFI, Secure Boot, реальное железо, поведение в VirtualBox), так и писать.
- Не писать «выглядит хорошо» или «проверено» без скриншота, записи или измерения. Скриншотов в ВМ сборки сделать нельзя: просить владельца и считать непроверенным.
- Только официальные репозитории Arch и свой репозиторий. AUR, KDE Store, GitHub-проекты только с явного одобрения по каждому пункту и записью в `DECISIONS.md`.
- Без телеметрии. Ничего нового не должно обращаться в сеть само, кроме pacman и flatpak.
- Секреты и закрытый ключ подписи никогда не попадают в репозиторий и в сессии ассистента.
- Вопросы владельцу: нумерованным списком с вариантами и рекомендованным ответом, коротко. Команды давать файлом или готовыми строками.
- После каждой фазы обновлять `docs/PLAN-STATE.md` и `DECISIONS.md`.
- Commit messages, PR descriptions, issue and comment texts must not contain any attribution to a tool or an AI: no `Co-Authored-By` trailer for an assistant, no `Generated with ...` line, no session or tool links, no 'Claude' or 'AI' signature. Write them as the project owner's own work. Already merged commits keep what they have (no history rewrite). `.claude/settings.json` switches the tool's own attribution off.

## Агент-ревьюер

Перед каждым PR запускай субагента `reviewer` (`.claude/agents/reviewer.md`): передай ему diff ветки (`git diff origin/main...HEAD`) и черновик текста PR. Он только читает и проверяет diff по этому файлу, `DECISIONS.md`, `docs/PLAN-STATE.md` и защищённым путям Tier A: затронутые защищённые файлы без одобрения, нет записей в DECISIONS/PLAN-STATE, нет тестов для новой логики, утверждения «проверено» в тексте PR без реального запуска, пакеты вне репозиториев (`pacman -Si`), строки интерфейса с Arch или следами телеметрии. Результат (список находок с важностью) вставляй в текст PR под названием «automated review» (без упоминания ассистента); находки HIGH исправляй до открытия PR.

## Перед просьбой о слиянии (Before asking the owner to merge)

Владелец только нажимает кнопку слияния. Перед фразой «PR готов» ассистент сам проверяет и показывает по одной строке OK или FAIL:

1. Основа PR: `main` (`gh pr view N --json baseRefName`). Ветку всегда создавать от свежего `main`, не от другой ветки функции и не делать PR на неё. Если PR зависит от незавершённого, не открывать его: ждать слияния первого. Открытый PR один, если только они не по-настоящему независимы.
2. Ветка не отстаёт от `main`: если `main` ушёл вперёд, слить `main` в ветку самому (в `DECISIONS.md`, `docs/PLAN-STATE.md` и файлах workflow оставлять обе версии, сначала записи `main`) и запушить.
3. Конфликтов нет: `mergeable` = MERGEABLE, `mergeStateStatus` = CLEAN (UNSTABLE только пока обязательные проверки ещё идут).
4. Все проверки CI зелёные: ждать `gh pr checks N --watch` (опрос раз в 30-60 с, до 10 минут), назвать, какие проверки шли. Упавшую проверку читать по логу и чинить самому. Если проверка ещё идёт, не просить слияния.
5. Метки: если diff трогает защищённый путь, на PR есть `design-approved` и `protected-paths` зелёная.
6. Текст PR: без упоминания инструмента или ИИ, раздел «Not verified» честный, находки ревьюера включены.
7. Заметки: `DECISIONS.md` и `docs/PLAN-STATE.md` обновлены (каждое новое «Not verified» добавлено строкой в «FINAL VM TEST LIST» в `docs/PLAN-STATE.md`, в раздел своей фазы); `scripts/check-protected.py verify` и локальные тесты запущены на финальном коммите.
8. Дерево чистое (`git status`), ветка запушена, локальный HEAD равен удалённому.

Итоговый отчёт по каждому PR, коротко по-русски: `ГОТОВ К СЛИЯНИЮ: #N название`, строка «основа: main | конфликтов нет | CI: X/X зелёные | метки: ok | тесты: ok», «Не проверено: ...», «Что нажать: Squash and merge», либо `НЕ ГОТОВ: причина и что делаю`.

После слова владельца «слит» проверить самому: `git fetch`, squash-коммит есть в `origin/main`, PR в состоянии MERGED с основой `main`, push-workflow на `main` (core, guards, publish-repo) зелёные; доложить одной строкой. Если что-то не так (например PR ушёл в другую ветку), сказать сразу и предложить исправление.

## Осторожно с командами

- Не запускай разрушительные команды (`dd`, `mkfs`, `rm -rf /`, `parted`, `wipefs`) на хост-системе. Диски трогаем только внутри виртуальных машин.
- Команды с `sudo` объясняй до запуска.

## Известные проблемы и ближайшие задачи

- Стиль установщика в духе макета: своя боковая панель на QML (ссылки Telegram `https://t.me/heiss_os` и X `https://x.com/heiss_OS`, позже Reddit), без кнопки «О приложении», без кнопок «Пожертвовать/Поддержка/Известные проблемы».
- Док: раскладка из LnF-скрипта (`contents/layouts/org.kde.plasma.desktop-layout.js`), `heiss-setup-dock.sh` только запасной вариант. Порядок закреплённых: Dolphin, Konsole, Параметры системы, Firefox; установщик в доке не закреплён (ярлык на рабочем столе). Позже сделать панель полупрозрачнее.
- Пакет `heiss-branding` вместо россыпи файлов; собственный репозиторий пакетов с подписью GPG; автосборка в GitHub Actions.
- Не проверялись: UEFI и Secure Boot. В VirtualBox замечена проблема с выделением мышью на рабочем столе (возможно, особенность Wayland и VirtualBox).
- Анимация слайдшоу (бегущий огонёк по логотипу, `show.qml`) готова и требует проверки в виртуальной машине (свечение через QtQuick.Effects не проверено; переключатели `animated`, `glow`, `glowUsesEffects`).
- Страница пользователя (`usersq.qml`): фоновый логотип «дышит» (4.6 с, масштаб 1.0 → 1.035, прозрачность 0.65-1.0, переключатель `animated`), язык берётся из `Qt.locale()` через таймер 500 мс (никогда не подключать обработчик к `Global.changed()`: взаимная блокировка). Проверка в виртуальной машине ещё не проведена.
- Из live-образа в установленную систему попадают лишние службы (`cloud-init` и др.): убрать в `heiss-cleanup.sh`.
- KDE visual polish pass pending (panel, widgets, fonts).
- Дальше по дорожной карте: Welcome-приложение с выбором профиля, Btrfs и снапшоты, Security Center, Security Labs.
