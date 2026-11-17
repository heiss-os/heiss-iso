"""Boot look: GRUB theme fonts and layout, the installed-menu switches, the live menu entries."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(REPO, "profile/airootfs/usr/share/heiss/grub-theme")
PROFILE = os.path.join(REPO, "profile")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def pf2_name(path):
    """The font's full name as GRUB sees it (NAME section of the .pf2 file)."""
    with open(path, "rb") as f:
        data = f.read(400)
    i = data.index(b"NAME")
    n = int.from_bytes(data[i + 4:i + 8], "big")
    return data[i + 8:i + 8 + n].rstrip(b"\0").decode()


class Theme(unittest.TestCase):
    def test_every_font_the_theme_names_exists_with_that_exact_name(self):
        theme = "\n".join(l for l in read(THEME, "theme.txt").splitlines() if not l.lstrip().startswith("#"))
        used = set(re.findall(r'(?:font|terminal-font|item_font|selected_item_font)\s*[:=]\s*"([^"]+)"', theme))
        self.assertTrue(used)
        have = {pf2_name(os.path.join(THEME, f)) for f in os.listdir(THEME) if f.endswith(".pf2")}
        self.assertEqual(used - have, set(), "theme names a font that no .pf2 file provides")
        self.assertEqual(have, {"Inter Medium Regular %d" % s for s in (16, 24)})   # no Regular-weight leftovers

    def test_layout_is_one_centred_block_that_fits_640x480_and_larger(self):
        theme = read(THEME, "theme.txt")

        def expr(name, block):
            m = re.search(r"\+ %s \{(.*?)\n\}" % block, theme, re.S)
            v = re.search(r"\b%s = (\S+)" % name, m.group(1)).group(1)
            m = re.fullmatch(r"(?:(\d+)%)?(?:([+-]\d+))?(\d+)?", v)
            pct, off, plain = m.groups()
            return int(pct or 0), int(off or 0) + int(plain or 0)

        logo_top, menu_top = expr("top", "image"), expr("top", "boot_menu")
        logo_h = int(re.search(r"height = (\d+)", re.search(r"\+ image \{(.*?)\n\}", theme, re.S).group(1)).group(1))
        menu_h = int(re.search(r"height = (\d+)", re.search(r"\+ boot_menu \{(.*?)\n\}", theme, re.S).group(1)).group(1))
        self.assertEqual(logo_top[0], 50)
        self.assertEqual(menu_top[0], 50)
        gap = menu_top[1] - (logo_top[1] + logo_h)
        self.assertGreaterEqual(gap, 24)
        total = logo_h + gap + menu_h
        self.assertLessEqual(abs(logo_top[1] + total // 2), 2, "block is not centred on the middle of the screen")
        for h in (480, 600, 768, 1080, 1440, 2160):
            top, bottom = h // 2 + logo_top[1], h // 2 + logo_top[1] + total
            self.assertGreaterEqual(top, 0, "block starts above the screen at height %d" % h)
            self.assertLessEqual(bottom, h - 24, "block runs into the footer at height %d" % h)
        logo_w = int(re.search(r"width = (\d+)", re.search(r"\+ image \{(.*?)\n\}", theme, re.S).group(1)).group(1))
        with open(os.path.join(THEME, "logo.png"), "rb") as f:        # GRUB does not scale: the PNG must be that size
            head = f.read(24)
        self.assertEqual((int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")), (logo_w, logo_h))
        self.assertEqual(expr("left", "image"), (50, -logo_w // 2))

    def test_installed_menu_switches(self):
        sh = read(PROFILE, "airootfs/usr/local/bin/heiss-boot-branding.sh")
        self.assertIn("setvar GRUB_DISABLE_BOOTNEXT true", sh)       # 31_efi_bootnext entries
        self.assertIn('HEISS_GRUB_GFXMODE:-auto}', sh)
        self.assertIn("setvar GRUB_GFXPAYLOAD_LINUX keep", sh)
        self.assertIn("setvar GRUB_TERMINAL_OUTPUT gfxterm", sh)


class LiveMenu(unittest.TestCase):
    def test_systemd_boot_has_normal_safe_and_speech_entries_in_order(self):
        d = os.path.join(PROFILE, "efiboot/loader/entries")
        names = sorted(os.listdir(d))
        self.assertEqual([n.split("-")[0] for n in names], ["01", "02", "03", "04"])
        keys = [re.search(r"sort-key (\d+)", read(d, n)).group(1) for n in names]
        self.assertEqual(keys, ["01", "02", "03", "04"])
        safe = read(d, "02-archiso-safe-graphics-linux.conf")
        self.assertIn("nomodeset", safe)
        self.assertIn("safe graphics", safe)
        self.assertNotIn("nomodeset", read(d, "01-archiso-linux.conf"))
        self.assertIn("default 01-archiso-linux.conf", read(PROFILE, "efiboot/loader/loader.conf"))

    def test_no_uefi_shell_anywhere(self):
        pk = read(PROFILE, "packages.x86_64").split()
        self.assertNotIn("edk2-shell", pk)          # systemd-boot lists a shell as "EFI Shell" when it is in the image
        self.assertNotIn("UEFI Shell", read(PROFILE, "grub/grub.cfg"))

    def test_the_three_boot_menus_offer_the_same_choices(self):
        grub = read(PROFILE, "grub/grub.cfg")
        sys_ = read(PROFILE, "syslinux/archiso_sys-linux.cfg")
        loop = read(PROFILE, "grub/loopback.cfg")
        self.assertIn("safe graphics", loop)
        self.assertNotIn("UEFI Shell", loop)
        self.assertIn("safe graphics", grub)
        self.assertIn("safe graphics", sys_)
        for text in (grub, sys_, loop):
            self.assertEqual(len(re.findall(r"^\s*(?:APPEND|linux)\b[^\n]*nomodeset", text, re.M)), 1)


if __name__ == "__main__":
    unittest.main()
