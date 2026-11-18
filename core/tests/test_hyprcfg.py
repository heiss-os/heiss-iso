"""heiss_core.hyprcfg: the key bindings and the main modifier of a Hyprland Lua configuration."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "core"))
from heiss_core import hyprcfg as hc  # noqa: E402

SHIPPED = os.path.join(REPO, "desktop", "hypr", "hyprland.lua")

# A stand-in for Hyprland's `hl` table: it records every hl.bind(keys, action, options) call and ignores the rest.
LUA_STUB = r'''
local function any() return setmetatable({}, {__call = function() return any() end, __index = function() return any() end}) end
hl = setmetatable({}, {__index = function() return function() return any() end end})
hl.dsp = any()
hl.on = function() end   -- callbacks run at runtime, not while the file loads
hl.bind = function(keys, action, opts)
    print(keys .. "\t" .. ((opts and opts.description) or ""))
end
dofile(arg[1])
'''


def shipped_text():
    with open(SHIPPED, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Parse(unittest.TestCase):
    def test_description_from_the_comment_above(self):
        b, _ = hc.parse_text('local mainMod = "ALT"\n-- Open the terminal\nhl.bind(mainMod .. " + Return", hl.dsp.exec_cmd("kitty"))\n')
        self.assertEqual([(x.keys, x.description) for x in b], [(["ALT", "Return"], "Open the terminal")])

    def test_two_comment_lines_are_joined_and_a_blank_line_detaches_the_comment(self):
        b, _ = hc.parse_text('-- one\n-- two\nhl.bind("A", f())\n\n-- lonely\n\nhl.bind("B", f())\n')
        self.assertEqual([x.description for x in b], ["one two", ""])

    def test_description_option_wins_over_the_comment_and_may_use_a_variable(self):
        b, _ = hc.parse_text('-- comment\nhl.bind("A", f(), { description = "from option " .. "x" })\n')
        self.assertEqual(b[0].description, "from option x")

    def test_a_comment_after_the_call_on_the_same_line(self):
        b, _ = hc.parse_text('hl.bind("A", f()) -- same line\n')
        self.assertEqual(b[0].description, "same line")

    def test_a_call_over_several_lines_and_nested_tables(self):
        text = '''-- Big one
hl.bind("SUPER + SHIFT + B",
        hl.dsp.window.move({ workspace = 3, extra = { 1, 2 } }),
        { repeating = true, description = "ignored by comment" })
'''
        b, _ = hc.parse_text(text)
        self.assertEqual((b[0].keys, b[0].description), (["SUPER", "SHIFT", "B"], "ignored by comment"))

    def test_for_loop_is_expanded_and_the_variable_is_known_inside_only(self):
        text = 'local m = "ALT"\nfor i = 1, 3 do\n  hl.bind(m .. " + " .. i, f(), { description = "Go " .. i })\nend\nhl.bind("X" .. i, f())\n'
        b, _ = hc.parse_text(text)
        self.assertEqual([(x.keys_text, x.description) for x in b[:3]], [("ALT + 1", "Go 1"), ("ALT + 2", "Go 2"), ("ALT + 3", "Go 3")])
        self.assertFalse(b[3].resolved)

    def test_unresolved_keys_are_listed_as_written_not_dropped_or_guessed(self):
        b, _ = hc.parse_text('hl.bind(some_function("a"), f())\n')
        self.assertEqual(len(b), 1)
        self.assertFalse(b[0].resolved)
        self.assertEqual(b[0].keys, [])

    def test_binds_inside_functions_comments_and_strings_are_not_bindings(self):
        text = '''hl.on("x", function()
    hl.bind("INSIDE", f())
end)
--[[ hl.bind("BLOCK", f()) ]]
-- hl.bind("LINE", f())
local s = "hl.bind('STRING', f())"
hl.bind("REAL", f())
'''
        b, _ = hc.parse_text(text)
        self.assertEqual([x.keys_text for x in b], ["REAL"])

    def test_an_unknown_assignment_does_not_erase_a_known_value(self):
        b, env = hc.parse_text('local m = "ALT"\nm = compute()\nhl.bind(m .. " + A", f())\n')
        self.assertEqual(b[0].keys_text, "ALT + A")

    def test_garbage_does_not_raise(self):
        for text in ('hl.bind(', 'for i = 1, 3 do hl.bind("A"', '"unterminated', 'function', "--[[ never closed", "hl.bind()", "\x00\xff"):
            hc.parse_text(text)


class Shipped(unittest.TestCase):
    def test_every_bind_of_the_shipped_configuration_is_resolved_and_described(self):
        b, _ = hc.parse_text(shipped_text())
        self.assertGreaterEqual(len(b), 30)
        for x in b:
            self.assertTrue(x.resolved, x.keys_text)
            self.assertTrue(x.description, x.keys_text)

    @unittest.skipUnless(shutil.which("lua"), "lua is needed")
    def test_the_parser_gives_the_same_bindings_as_running_the_real_file(self):
        """Ground truth: run hyprland.lua under Lua with a stub `hl` and compare keys and descriptions that Lua computed."""
        for modifier in (None, "SUPER", "ALT"):
            with tempfile.TemporaryDirectory() as d:
                if modifier:
                    write(os.path.join(d, "heiss", "modifier"), modifier + "\n")
                stub = os.path.join(d, "stub.lua")
                write(stub, LUA_STUB)
                env = {"PATH": os.environ["PATH"], "HOME": d, "XDG_CONFIG_HOME": d}
                r = subprocess.run(["lua", stub, SHIPPED], capture_output=True, text=True, env=env, cwd=d, timeout=30)
                self.assertEqual(r.returncode, 0, r.stderr)
                truth = [tuple(l.split("\t", 1)) for l in r.stdout.splitlines()]
                write(os.path.join(d, "hypr", "hyprland.lua"), shipped_text())
                cfg = hc.load(d)
                got = [(x.keys_text, x.description) for x in cfg.bindings]
                # Lua's description option exists only for the loops; for the others the comment is the description
                self.assertEqual([k for k, _ in got], [k for k, _ in truth], modifier)
                for (_, gd), (_, td) in zip(got, truth):
                    if td:
                        self.assertEqual(gd, td)
                self.assertEqual(cfg.main_mod, modifier or "ALT")

    @unittest.skipUnless(shutil.which("lua"), "lua is needed")
    def test_the_modifier_block_ignores_anything_but_alt_or_super(self):
        for content, expect in (("SUPER\n", "SUPER"), ("ALT", "ALT"), ("CTRL\n", "ALT"), ("super\n", "ALT"), ("", "ALT"),
                                ("SUPER\nALT\n", "SUPER"), ("../../x\n", "ALT")):
            with tempfile.TemporaryDirectory() as d:
                write(os.path.join(d, "heiss", "modifier"), content)
                stub = os.path.join(d, "stub.lua")
                write(stub, LUA_STUB)
                env = {"PATH": os.environ["PATH"], "HOME": d, "XDG_CONFIG_HOME": d}
                r = subprocess.run(["lua", stub, SHIPPED], capture_output=True, text=True, env=env, cwd=d, timeout=30)
                self.assertEqual(r.stdout.splitlines()[0].split("\t")[0], expect + " + Return", repr(content))


class Load(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)

    def shipped(self):
        write(os.path.join(self.d, "hypr", "hyprland.lua"), shipped_text())

    def test_modifier_file_switches_the_modifier_of_a_managed_configuration(self):
        self.shipped()
        self.assertEqual((hc.load(self.d).main_mod, hc.load(self.d).managed), ("ALT", True))
        hc.write_modifier(self.d, "SUPER")
        cfg = hc.load(self.d)
        self.assertEqual(cfg.main_mod, "SUPER")
        self.assertTrue(all(b.keys[0] == "SUPER" for b in cfg.bindings if b.keys_text.startswith(("ALT", "SUPER"))))
        self.assertNotIn("ALT", [k for b in cfg.bindings for k in b.keys])
        hc.write_modifier(self.d, "ALT")
        self.assertEqual(hc.load(self.d).main_mod, "ALT")

    def test_an_own_configuration_keeps_its_modifier_and_is_not_managed(self):
        write(os.path.join(self.d, "hypr", "hyprland.lua"), 'local mainMod = "SUPER"\n-- Terminal\nhl.bind(mainMod .. " + T", f())\n')
        hc.write_modifier(self.d, "ALT")   # has no effect on a file that does not read it
        cfg = hc.load(self.d)
        self.assertFalse(cfg.managed)
        self.assertEqual((cfg.main_mod, cfg.bindings[0].keys), ("SUPER", ["SUPER", "T"]))

    def test_user_file_is_read_after_the_main_file(self):
        self.shipped()
        write(os.path.join(self.d, "hypr", "heiss-user.lua"), '-- Mine\nhl.bind(mainMod .. " + M", f())\n')
        cfg = hc.load(self.d)
        self.assertEqual((cfg.bindings[-1].keys_text, cfg.bindings[-1].description), ("ALT + M", "Mine"))

    def test_missing_or_huge_file_is_an_error_not_an_exception(self):
        self.assertTrue(hc.load(self.d).error)
        write(os.path.join(self.d, "hypr", "hyprland.lua"), "-" * (hc.MAX_BYTES + 5))
        cfg = hc.load(self.d)
        self.assertTrue(cfg.error)
        self.assertEqual(cfg.bindings, [])

    def test_write_modifier_refuses_other_values_and_leaves_no_temp_file(self):
        for bad in ("CTRL", "alt", "ALT\nSUPER", "", None):
            with self.assertRaises(ValueError):
                hc.write_modifier(self.d, bad)
        self.assertFalse(os.path.exists(os.path.join(self.d, "heiss", "modifier")))
        hc.write_modifier(self.d, "SUPER")
        self.assertEqual(sorted(os.listdir(os.path.join(self.d, "heiss"))), ["modifier"])
        self.assertEqual(hc.read_modifier(self.d), "SUPER")

    def test_read_modifier_ignores_a_file_with_anything_else(self):
        write(os.path.join(self.d, "heiss", "modifier"), "SUPER; rm -rf /\n")
        self.assertEqual(hc.read_modifier(self.d), "")


if __name__ == "__main__":
    unittest.main()
