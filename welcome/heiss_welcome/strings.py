"""Interface strings (en/ru) of the welcome window. Key names are shown in the language of the interface."""

S = {
    "en": {
        "app": "Heiss Welcome",
        "title": "Welcome to Heiss OS",
        "intro": "These are the key bindings of your desktop. The list is read from your Hyprland configuration, so it is always the one in use.",
        "mainkey": "Main key: %s",
        "mainkey_managed": "You can switch it between Alt and Super in the Heiss settings.",
        "mainkey_own": "Your configuration sets it itself (mainMod in hyprland.lua); the settings window does not change it.",
        "search": "Search the key bindings",
        "none": "No key bindings found.",
        "nomatch": "Nothing matches.",
        "unreadable": "The configuration could not be read: %s",
        "undescribed": "(no description in the configuration)",
        "unresolved": "(key written in a form this list cannot read)",
        "close": "Close",
        "lang_en": "English", "lang_ru": "Русский",
        "key.Alt": "Alt", "key.Super": "Super", "key.Shift": "Shift", "key.Ctrl": "Ctrl",
        "key.Enter": "Enter", "key.Print": "Print Screen", "key.Space": "Space", "key.Tab": "Tab", "key.Escape": "Esc",
        "key.left": "Left arrow", "key.right": "Right arrow", "key.up": "Up arrow", "key.down": "Down arrow",
        "key.mouse:272": "left mouse button", "key.mouse:273": "right mouse button", "key.mouse:274": "middle mouse button",
        "key.XF86AudioRaiseVolume": "Volume up", "key.XF86AudioLowerVolume": "Volume down", "key.XF86AudioMute": "Mute",
        "key.XF86MonBrightnessUp": "Brightness up", "key.XF86MonBrightnessDown": "Brightness down",
    },
    "ru": {
        "app": "Добро пожаловать",
        "title": "Добро пожаловать в Heiss OS",
        "intro": "Это сочетания клавиш вашего рабочего стола. Список читается из конфигурации Hyprland, поэтому он всегда совпадает с действующим.",
        "mainkey": "Главная клавиша: %s",
        "mainkey_managed": "Её можно переключить между Alt и Super в настройках Heiss.",
        "mainkey_own": "Ваша конфигурация задаёт её сама (mainMod в hyprland.lua); окно настроек её не меняет.",
        "search": "Поиск по сочетаниям",
        "none": "Сочетаний клавиш не найдено.",
        "nomatch": "Ничего не найдено.",
        "unreadable": "Не удалось прочитать конфигурацию: %s",
        "undescribed": "(в конфигурации нет описания)",
        "unresolved": "(клавиши записаны в форме, которую этот список не умеет читать)",
        "close": "Закрыть",
        "lang_en": "English", "lang_ru": "Русский",
        "key.Alt": "Alt", "key.Super": "Super", "key.Shift": "Shift", "key.Ctrl": "Ctrl",
        "key.Enter": "Enter", "key.Print": "Print Screen", "key.Space": "Пробел", "key.Tab": "Tab", "key.Escape": "Esc",
        "key.left": "стрелка влево", "key.right": "стрелка вправо", "key.up": "стрелка вверх", "key.down": "стрелка вниз",
        "key.mouse:272": "левая кнопка мыши", "key.mouse:273": "правая кнопка мыши", "key.mouse:274": "средняя кнопка мыши",
        "key.XF86AudioRaiseVolume": "Громкость выше", "key.XF86AudioLowerVolume": "Громкость ниже", "key.XF86AudioMute": "Без звука",
        "key.XF86MonBrightnessUp": "Яркость выше", "key.XF86MonBrightnessDown": "Яркость ниже",
    },
}


def t(lang, key):
    return S.get(lang, S["en"]).get(key) or S["en"][key]
