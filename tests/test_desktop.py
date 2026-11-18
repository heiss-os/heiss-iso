"""The default Hyprland session files (desktop/): bind descriptions, theme colours only from tokens, first-login sources."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.join(ROOT, "desktop")
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|rgba?\([0-9, ]+\)")


def read(*p):
    with open(os.path.join(DESKTOP, *p), encoding="utf-8") as f:
        return f.read()


class HyprlandConfig(unittest.TestCase):
    def test_every_bind_line_has_a_description_comment_directly_above(self):
        lines = read("hypr", "hyprland.conf").splitlines()
        binds = [i for i, l in enumerate(lines) if re.match(r"bind[a-z]*\s*=", l)]
        self.assertGreater(len(binds), 30)
        for i in binds:
            above = lines[i - 1].strip()
            self.assertTrue(above.startswith("# ") and len(above) > 3, "no description above: " + lines[i])

    def test_binds_have_no_duplicate_key_combination(self):
        seen = {}
        for l in read("hypr", "hyprland.conf").splitlines():
            m = re.match(r"bind[a-z]*\s*=\s*([^,]*),\s*([^,]+),", l)
            if m:
                key = (m.group(1).strip(), m.group(2).strip())
                self.assertNotIn(key, seen, "key bound twice: %r" % (key,))
                seen[key] = l

    def test_the_user_include_is_the_last_line(self):
        last = [l for l in read("hypr", "hyprland.conf").splitlines() if l.strip()][-1]
        self.assertEqual(last, "source = ~/.config/hypr/heiss-user.conf")

    def test_colours_come_from_the_generated_theme_only(self):
        for rel in (("hypr", "hyprland.conf"), ("hypr", "hyprlock.conf"), ("hypr", "hypridle.conf"),
                    ("waybar", "style.css"), ("waybar", "config.jsonc"), ("sddm", "heiss", "Main.qml")):
            self.assertIsNone(HEX.search(read(*rel)), "literal colour in %s" % "/".join(rel))

    def test_sourced_theme_file_is_the_one_first_login_creates(self):
        first = read("bin", "heiss-first-login")
        for rel in (("hypr", "hyprland.conf"), ("hypr", "hyprlock.conf")):
            self.assertIn("source = ~/.config/heiss/theme/hypr-colors.conf", read(*rel))
        self.assertIn("hypr-colors.conf", first)
        self.assertIn('@import "../heiss/theme/waybar-colors.css";', read("waybar", "style.css"))


class FirstLogin(unittest.TestCase):
    def test_every_copied_file_exists_in_the_source_tree(self):
        for src in re.findall(r"^copy (\S+) ", read("bin", "heiss-first-login"), re.M):
            self.assertTrue(os.path.isfile(os.path.join(DESKTOP, src)), src)

    def test_never_overwrites_and_writes_only_below_the_users_directories(self):
        text = read("bin", "heiss-first-login")
        self.assertNotRegex(text, r"\bcp -f|\bmv |\brm |sudo|\bln -sf\b(?!n)")
        self.assertNotIn("/etc/", text.replace("/etc/xdg", ""))

    def test_session_logs_and_retries_with_software_rendering(self):
        text = read("bin", "heiss-session")
        self.assertIn("WLR_RENDERER_ALLOW_SOFTWARE=1", text)
        self.assertIn("nomodeset", text)
        self.assertIn("/usr/bin/heiss-first-login", text)

    def test_session_entry_runs_the_session_script(self):
        text = read("session", "heiss.desktop")
        self.assertIn("Exec=/usr/bin/heiss-session", text)
        self.assertIn("DesktopNames=Hyprland", text)


class SddmTheme(unittest.TestCase):
    def test_theme_has_no_plasma_or_kde_import(self):
        self.assertNotRegex(read("sddm", "heiss", "Main.qml"), r"import\s+org\.kde|Kirigami|plasma")

    def test_main_script_and_config_names(self):
        meta = read("sddm", "heiss", "metadata.desktop")
        self.assertIn("MainScript=Main.qml", meta)
        self.assertIn("ConfigFile=theme.conf", meta)

    def test_every_config_key_the_theme_reads_is_generated(self):
        qml = read("sddm", "heiss", "Main.qml")
        used = set(re.findall(r"config\.(\w+)", qml))
        with open(os.path.join(ROOT, "branding", "tokens", "generated", "desktop", "dark", "sddm-theme.conf"), encoding="utf-8") as f:
            have = {l.split("=")[0] for l in f if "=" in l}
        self.assertEqual(used - have, set())

    def test_system_configs_name_the_theme_and_session(self):
        air = os.path.join(ROOT, "profile", "airootfs", "etc", "sddm.conf.d")
        with open(os.path.join(air, "heiss-theme.conf"), encoding="utf-8") as f:
            self.assertIn("Current=heiss", f.read())
        with open(os.path.join(air, "autologin.conf"), encoding="utf-8") as f:
            self.assertIn("Session=heiss.desktop", f.read())


class NoPlasmaLeft(unittest.TestCase):
    def test_iso_list_and_manifests_have_no_kde_packages(self):
        names = ("plasma-desktop", "plasma-workspace", "kwin", "konsole", "dolphin", "kate", "ark", "gwenview", "okular",
                 "spectacle", "kscreen", "plasma-nm", "plasma-pa", "polkit-kde-agent", "xdg-desktop-portal-kde",
                 "kde-gtk-config", "breeze-gtk", "bluedevil", "powerdevil", "plasma-firewall")
        for rel in ("profile/packages.x86_64",) + tuple("profiles/%s.toml" % n for n in ("essentials", "base", "custom", "cyber", "developer")):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                text = f.read()
            for n in names:
                self.assertNotRegex(text, r'(^|")%s("|$)' % re.escape(n), "%s mentions %s" % (rel, n))

    def test_plasma_files_are_gone(self):
        air = os.path.join(ROOT, "profile", "airootfs")
        for rel in ("usr/share/plasma", "usr/share/color-schemes", "etc/xdg/kdeglobals", "etc/xdg/kwinrc",
                    "etc/xdg/kscreenlockerrc", "etc/xdg/ksplashrc", "usr/local/bin/heiss-setup-dock.sh",
                    "usr/local/bin/heiss-theme-sync.sh", "usr/local/bin/heiss-set-wallpaper.sh"):
            self.assertFalse(os.path.exists(os.path.join(air, rel)), rel)


if __name__ == "__main__":
    unittest.main()
