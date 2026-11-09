"""Guards for the design tokens. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import heiss_tokens as h  # noqa: E402

SCHEMES = os.path.join(ROOT, "profile", "airootfs", "usr", "share", "color-schemes")


class GeneratorMatchesExistingSchemes(unittest.TestCase):
    """Generated schemes may ADD keys but must never alter an existing one."""

    def check(self, theme):
        tokens = h.load()
        sid = tokens["themes"][theme]["scheme_id"]
        with open(os.path.join(SCHEMES, sid + ".colors"), encoding="utf-8") as f:
            existing = h.parse_ini(f.read())
        generated = h.parse_ini(h.render_kde_scheme(tokens, theme))
        self.assertTrue(existing, "existing scheme parsed empty")
        for section, keys in existing.items():
            self.assertIn(section, generated, "missing section [%s]" % section)
            for key, value in keys.items():
                self.assertIn(key, generated[section], "missing [%s] %s" % (section, key))
                self.assertEqual(generated[section][key], value, "[%s] %s differs" % (section, key))

    def test_dark(self):
        self.check("dark")

    def test_light(self):
        self.check("light")


class TokenSanity(unittest.TestCase):
    def test_frozen_accents_and_surfaces(self):
        t = h.load()["themes"]
        self.assertEqual(t["dark"]["base"]["accent"], "#C9B28A")
        self.assertEqual(t["light"]["base"]["accent"], "#8C7448")
        for key, dark, light in (("window", "#26282B", "#F5F3EF"), ("panel", "#1E1F21", "#ECE9E3"),
                                 ("button", "#34373B", "#DEDAD2"), ("text", "#ECEAE5", "#26282B"),
                                 ("text_secondary", "#A9A7A1", "#6B6963"), ("view", "#1E1F21", "#FAF9F6")):
            self.assertEqual(t["dark"]["base"][key], dark, key)
            self.assertEqual(t["light"]["base"][key], light, key)

    def test_terminal_has_16_colors(self):
        for th in h.THEMES:
            self.assertEqual(len(h.terminal(h.load(), th)["ansi"]), 16)

    def test_mix_is_deterministic(self):
        self.assertEqual(h.mix("#000000", "#FFFFFF", 0.5), "#808080")

    def test_semantic_colors_match_scheme(self):
        # ansi 1,2,3 reuse the existing negative/positive/neutral in dark
        t = h.load()
        d = t["themes"]["dark"]
        self.assertEqual(d["terminal"]["ansi"][1], d["base"]["negative"])
        self.assertEqual(d["terminal"]["ansi"][2], d["base"]["positive"])
        self.assertEqual(d["terminal"]["ansi"][3], d["base"]["neutral"])


class DerivedTextColors(unittest.TestCase):
    def test_text_variants_meet_aa_on_all_backgrounds(self):
        tokens = h.load()
        for th in h.THEMES:
            p = h.palette(tokens, th)
            for name in ("accent", "negative", "neutral", "positive", "info"):
                for bg in h.TEXT_BACKGROUNDS:
                    self.assertGreaterEqual(h.contrast(p[name + "_text"], p[bg]), 4.5, "%s %s_text on %s" % (th, name, bg))

    def test_frozen_colors_not_altered_by_derivation(self):
        tokens = h.load()
        for th in h.THEMES:
            p = h.palette(tokens, th)
            for k, v in tokens["themes"][th]["base"].items():
                self.assertEqual(p[k], v, k)

    def test_light_accent_text_is_darker_than_accent(self):
        p = h.palette(h.load(), "light")
        self.assertLess(h.luminance(p["accent_text"]), h.luminance(p["accent"]))


class Contrast(unittest.TestCase):
    def test_pairs_meet_minimum_or_are_known(self):
        tokens = h.load()
        for th in h.THEMES:
            known = set(tokens["known_exceptions"].get(th, []))
            for label, fg, bg, minimum in h.text_pairs(tokens, th):
                if label in known:
                    continue
                self.assertGreaterEqual(h.contrast(fg, bg), minimum, "%s %s" % (th, label))

    def test_known_exceptions_still_fail(self):
        tokens = h.load()
        for th in h.THEMES:
            failing = {l for l, f, b, m in h.text_pairs(tokens, th) if h.contrast(f, b) < m}
            self.assertEqual(set(tokens["known_exceptions"].get(th, [])), failing, th)


class GeneratedFilesFresh(unittest.TestCase):
    def test_committed_outputs_match_regeneration(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("gen_theme", os.path.join(ROOT, "scripts", "gen-theme.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for rel, text in mod.outputs(h.load()).items():
            with open(os.path.join(mod.OUT, rel), encoding="utf-8") as f:
                self.assertEqual(f.read(), text, rel)


if __name__ == "__main__":
    unittest.main()
