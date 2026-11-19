-- Heiss OS: Hyprland configuration (placeholder, replace it with your own). Hyprland 0.57 reads Lua.
--
-- Where this file lives: /usr/share/heiss/desktop/hypr/hyprland.lua is copied to ~/.config/hypr/hyprland.lua
-- at the first login and never overwritten afterwards. To use your own configuration, replace that file. The only
-- part Heiss needs is the last block: it loads ~/.config/hypr/heiss-user.lua, where Heiss settings write.
--
-- Convention for key bindings: every bind has a comment line with its description directly above it.
-- The welcome window reads those pairs, so the list it shows is always the one in this file.
--
-- Check this file without starting the compositor: Hyprland --verify-config -c hyprland.lua

local home = os.getenv("HOME") or ""
local config_dir = os.getenv("XDG_CONFIG_HOME") or (home .. "/.config")

---------------------
---- HEISS COLORS ---
---------------------

-- ~/.config/heiss/theme/hypr-colors.conf is written by `heiss theme` (Heiss Dark or Heiss Light). It holds lines
-- like `$heiss_accent = rgb(c9b28a)`; hyprlock reads the same file, so it is read here instead of copied.
local colors = {}   -- empty if the file is missing: Hyprland's own colours apply until the first login has written it
do
    local f = io.open(config_dir .. "/heiss/theme/hypr-colors.conf", "r")
    if f then
        for line in f:lines() do
            local name, value = line:match("^%$heiss_([%w_]+)%s*=%s*(%S+)%s*$")
            if name then colors[name] = value end
        end
        f:close()
    end
end

------------------
---- MONITORS ----
------------------

-- Every monitor at its preferred mode, scale 1, placed from left to right.
-- In a virtual machine the preferred mode follows the window size (guest tools resize it).
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = 1,
})

---------------------
---- MY PROGRAMS ----
---------------------

local terminal    = "kitty"
local fileManager = "thunar"
local menu        = "fuzzel"

-- The main modifier of every key binding below. ALT keeps Hyprland usable inside a virtual machine whose host
-- uses SUPER. The Heiss settings window switches it between ALT and SUPER by writing ~/.config/heiss/modifier
-- (one word); you can also change the default on the next line.
local mainMod = "ALT"
do
    local f = io.open(config_dir .. "/heiss/modifier", "r")
    if f then
        local v = (f:read("*l") or ""):match("^%s*(%u+)%s*$")
        f:close()
        if v == "ALT" or v == "SUPER" then mainMod = v end
    end
end

-------------------
---- AUTOSTART ----
-------------------

hl.on("hyprland.start", function()
    hl.exec_cmd("heiss-wallpaper")
    -- the welcome window with the key bindings: it shows itself once per user and never in the live session
    hl.exec_cmd("heiss-welcome --first-run")
    hl.exec_cmd("waybar")
    hl.exec_cmd("mako")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("hyprpolkitagent")
    hl.exec_cmd("nm-applet --indicator")
    hl.exec_cmd("blueman-applet")
    -- VirtualBox guest: clipboard and the rest of the user part of the guest tools (it does nothing elsewhere)
    hl.exec_cmd("command -v VBoxClient-all >/dev/null && VBoxClient-all")
end)

-----------------------
---- LOOK AND FEEL ----
-----------------------

hl.config({
    general = {
        gaps_in  = 5,
        gaps_out = 10,

        border_size = 2,

        col = {
            active_border   = colors.accent,
            inactive_border = colors.border,
        },

        layout = "dwindle",
    },

    decoration = {
        rounding = 10,

        blur = {
            enabled = true,
            size    = 6,
            passes  = 2,
        },
    },

    animations = {
        enabled = true,
    },

    dwindle = {
        preserve_split = true,
    },

    -- No built-in wallpaper and no logo: the wallpaper is ours (heiss-wallpaper, swaybg)
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo   = true,
        disable_splash_rendering = true,
    },
})

---------------
---- INPUT ----
---------------

-- The keyboard layout of the installed system comes in through XKB_DEFAULT_* (heiss-session reads it from the
-- system keyboard file); the Heiss settings window and the installer override it in heiss-user.lua.
hl.config({
    input = {
        kb_layout  = os.getenv("XKB_DEFAULT_LAYOUT") or "us",
        kb_variant = os.getenv("XKB_DEFAULT_VARIANT") or "",
        kb_options = os.getenv("XKB_DEFAULT_OPTIONS") or "",

        follow_mouse = 1,

        touchpad = {
            natural_scroll = true,
        },
    },
})

---------------------
---- KEYBINDINGS ----
---------------------

-- Open the terminal
hl.bind(mainMod .. " + Return", hl.dsp.exec_cmd(terminal))
-- Open the file manager
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager))
-- Open the application launcher
hl.bind(mainMod .. " + D", hl.dsp.exec_cmd("pkill fuzzel || " .. menu))
-- Close the active window
hl.bind(mainMod .. " + Q", hl.dsp.window.close())
-- Toggle fullscreen for the active window
hl.bind(mainMod .. " + F", hl.dsp.window.fullscreen())
-- Toggle floating for the active window
hl.bind(mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
-- Show the list of key bindings (the welcome window)
hl.bind(mainMod .. " + F1", hl.dsp.exec_cmd("heiss-welcome --force"))
-- Open the Heiss settings
hl.bind(mainMod .. " + I", hl.dsp.exec_cmd("heiss-control"))
-- Lock the screen
hl.bind(mainMod .. " + L", hl.dsp.exec_cmd("hyprlock"))
-- Leave the session
hl.bind(mainMod .. " + SHIFT + E", hl.dsp.exit())

-- Focus the window on the left
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
-- Focus the window on the right
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
-- Focus the window above
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
-- Focus the window below
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Go to workspace 1 to 5 (the key is the number)
-- Move the active window to workspace 1 to 5 (hold SHIFT with the number)
for i = 1, 5 do
    hl.bind(mainMod .. " + " .. i,           hl.dsp.focus({ workspace = i }),
            { description = "Go to workspace " .. i })
    hl.bind(mainMod .. " + SHIFT + " .. i,   hl.dsp.window.move({ workspace = i }),
            { description = "Move the window to workspace " .. i })
end

-- Move a window with the mouse (hold the key and drag with the left button)
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
-- Resize a window with the mouse (hold the key and drag with the right button)
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Screenshot of a selected area to the clipboard
hl.bind("Print", hl.dsp.exec_cmd('grim -g "$(slurp)" - | wl-copy'))
-- Screenshot of a selected area saved to the Pictures folder
hl.bind("SHIFT + Print", hl.dsp.exec_cmd('mkdir -p ~/Pictures && grim -g "$(slurp)" ~/Pictures/screenshot-$(date +%Y%m%d-%H%M%S).png'))

-- Raise the volume
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
-- Lower the volume
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),       { locked = true, repeating = true })
-- Mute or unmute the sound
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),      { locked = true })
-- Raise the screen brightness
hl.bind("XF86MonBrightnessUp",  hl.dsp.exec_cmd("brightnessctl set 5%+"),                           { locked = true, repeating = true })
-- Lower the screen brightness
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"),                          { locked = true, repeating = true })

----------------------------------------
---- HEISS USER SETTINGS (keep last) ----
----------------------------------------

-- Written by Heiss settings, loaded last so that it overrides the defaults above.
-- With your own configuration, keep these lines (or load your own file the same way).
local user_file = config_dir .. "/hypr/heiss-user.lua"
local uf = io.open(user_file, "r")
if uf then
    uf:close()
    dofile(user_file)
end
