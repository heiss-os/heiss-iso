"""Reads the key bindings of the active Hyprland Lua configuration, and the main modifier (ALT or SUPER).

Hyprland 0.57 reads `~/.config/hypr/hyprland.lua`. A binding is a call `hl.bind(KEYS, ACTION, OPTIONS)`; KEYS is a
string such as "ALT + SHIFT + E", usually built with the variable `mainMod`. This module does not run the Lua: it
tokenises the file and understands exactly what the Heiss configuration (and a hand-written one in the same style)
uses:

  * `local name = "text" .. other` and `name = ...` with strings, numbers and earlier variables;
  * `for i = 1, 5 do ... end` loops (the body is read once per value of `i`);
  * `hl.bind(KEYS, ACTION [, { description = "..." }])`, also over several lines;
  * the description of a binding: the `description` option, else the comment lines directly above the call, else a
    comment after it on the same line;
  * a `function ... end` body is skipped (a binding inside a callback is not a fixed one).

What it does not understand it says so: such a binding is listed with `keys_text` as written and `resolved` False.
Nothing is executed, nothing is written except the small modifier file.

The modifier: `~/.config/heiss/modifier` holds `ALT` or `SUPER`. The shipped hyprland.lua reads that file (the line
`heiss/modifier` in it is what makes the setting "managed"); a configuration of the user's own that does not read the
file keeps its own `mainMod`, and the settings window says so.
"""
import os
import re
from dataclasses import dataclass, field

MODIFIERS = ("ALT", "SUPER")
DEFAULT_MODIFIER = "ALT"
MODIFIER_FILE = os.path.join("heiss", "modifier")   # below the configuration directory
MANAGED_MARK = "heiss/modifier"                      # present in a configuration that reads the file
MAX_BYTES = 1 << 20                                  # a configuration larger than this is not read


@dataclass
class Binding:
    keys: list            # ["ALT", "SHIFT", "E"] (empty when unresolved)
    keys_text: str        # as a person reads it: "ALT + SHIFT + E"
    description: str
    line: int
    resolved: bool = True


@dataclass
class Config:
    path: str
    bindings: list = field(default_factory=list)
    main_mod: str = DEFAULT_MODIFIER   # the modifier the bindings were read with
    managed: bool = False              # the file reads ~/.config/heiss/modifier
    error: str = ""


# ------------------------------------------------------------------ tokens

_SYMS = ("...", "..", "==", "~=", "<=", ">=", "::", "//", "<<", ">>")


def tokenize(text):
    """[(kind, value, line)]; kind is name, str, num, sym or comment. Block comments and long strings are skipped."""
    toks, i, n, line = [], 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif text.startswith("--", i):
            m = re.match(r"--\[(=*)\[", text[i:])
            if m:
                close = "]" + m.group(1) + "]"
                j = text.find(close, i)
                j = n if j < 0 else j + len(close)
                line += text.count("\n", i, j)
                i = j
            else:
                j = text.find("\n", i)
                j = n if j < 0 else j
                toks.append(("comment", text[i + 2:j].strip(), line))
                i = j
        elif c in "\"'":
            j, buf = i + 1, []
            while j < n and text[j] != c and text[j] != "\n":
                if text[j] == "\\" and j + 1 < n:
                    j += 1
                    buf.append({"n": "\n", "t": "\t"}.get(text[j], text[j]))
                else:
                    buf.append(text[j])
                j += 1
            toks.append(("str", "".join(buf), line))
            i = j + 1
        elif text.startswith("[[", i) or re.match(r"\[=+\[", text[i:i + 8]):
            m = re.match(r"\[(=*)\[", text[i:])
            close = "]" + m.group(1) + "]"
            j = text.find(close, i)
            j = n if j < 0 else j + len(close)
            toks.append(("str", "", line))
            line += text.count("\n", i, j)
            i = j
        elif c.isascii() and c.isdigit():
            m = re.match(r"0[xX][0-9a-fA-F]+|\d+(\.\d+)?", text[i:])
            toks.append(("num", m.group(0), line))
            i += len(m.group(0))
        elif c.isascii() and (c.isalpha() or c == "_"):
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[i:])
            toks.append(("name", m.group(0), line))
            i += len(m.group(0))
        else:
            sym = next((s for s in _SYMS if text.startswith(s, i)), c)
            toks.append(("sym", sym, line))
            i += len(sym)
    return toks


# ------------------------------------------------------------------ reading

class _Reader:
    def __init__(self, forced=None):
        self.env = {}
        self.forced = forced or {}
        self.out = []

    # a value is a str, or None when it cannot be known
    def value_of(self, name):
        return self.forced[name] if name in self.forced else self.env.get(name)

    def eval_terms(self, toks):
        """toks: term (.. term)* -> str, or None. A term is a string, a number, a variable or tostring(variable)."""
        parts, i, want_term = [], 0, True
        while i < len(toks):
            kind, val, _ = toks[i]
            if want_term:
                if kind == "str":
                    parts.append(val)
                elif kind == "num":
                    parts.append(val)
                elif kind == "name" and val == "tostring" and i + 3 < len(toks) and toks[i + 1][1] == "(" \
                        and toks[i + 3][1] == ")":
                    v = self.value_of(toks[i + 2][1])
                    if v is None:
                        return None
                    parts.append(v)
                    i += 3
                elif kind == "name":
                    v = self.value_of(val)
                    if v is None:
                        return None
                    parts.append(v)
                else:
                    return None
                want_term = False
            else:
                if (kind, val) != ("sym", ".."):
                    return None
                want_term = True
            i += 1
        return None if want_term else "".join(parts)

    def run(self, toks, lo, hi, comments=None):
        i = lo
        pending = []   # [(text, line)] comment lines that directly follow each other
        while i < hi:
            kind, val, line = toks[i]
            if kind == "comment":
                if pending and pending[-1][1] == line - 1:
                    pending.append((val, line))
                else:
                    pending = [(val, line)]
                i += 1
                continue
            attached = pending and pending[-1][1] == line - 1
            desc_above = " ".join(t for t, _ in pending) if attached else ""
            pending = []
            if kind == "name" and val == "function":
                i = self._end_of(toks, i + 1, hi)
                continue
            if kind == "name" and val == "for":
                i = self._for(toks, i, hi)
                continue
            if kind == "name" and val == "local" and i + 1 < hi and toks[i + 1][0] == "name":
                i += 1
                kind, val, line = toks[i]
            if kind == "name" and i + 1 < hi and toks[i + 1][:2] == ("sym", "=") and val not in ("hl",):
                j = i + 2
                while j < hi and not self._statement_end(toks, j, i + 2):
                    j += 1
                v = self.eval_terms([t for t in toks[i + 2:j] if t[0] != "comment"])
                if v is not None or val not in self.env:   # an unknown value never erases a known one
                    self.env[val] = v
                i = j
                continue
            if kind == "name" and val == "hl" and i + 3 < hi and toks[i + 1][1] == "." and toks[i + 2][1] == "bind" \
                    and toks[i + 3][1] == "(":
                i = self._bind(toks, i + 3, hi, desc_above)
                continue
            i += 1

    @staticmethod
    def _statement_end(toks, j, first):
        """Is toks[j] the start of the next statement? (a new line that does not continue an expression)"""
        if j == first:
            return False
        prev, cur = toks[j - 1], toks[j]
        if cur[2] == prev[2]:
            return cur[:2] == ("sym", ";")
        return not (prev[:2] == ("sym", "..") or cur[:2] == ("sym", ".."))

    @staticmethod
    def _end_of(toks, i, hi):
        """Index just after the `end` that closes a block opened right before toks[i]."""
        depth = 1
        while i < hi:
            kind, val, _ = toks[i]
            if kind == "name":
                if val in ("function", "if", "do"):
                    depth += 1
                elif val == "end":
                    depth -= 1
                    if depth == 0:
                        return i + 1
            i += 1
        return hi

    def _for(self, toks, i, hi):
        # for NAME = A, B do BODY end  (a numeric loop with literal bounds; anything else is read once, unresolved)
        m = toks[i + 1:i + 7]
        if len(m) == 6 and m[0][0] == "name" and m[1][:2] == ("sym", "=") and m[2][0] == "num" and m[3][:2] == ("sym", ",") \
                and m[4][0] == "num" and m[5][:2] == ("name", "do") and m[2][1].isdigit() and m[4][1].isdigit():
            body_lo = i + 7
            end = self._end_of(toks, body_lo, hi)
            a, b = int(m[2][1]), int(m[4][1])
            if b - a > 1000:
                return end
            old = self.env.get(m[0][1])
            for v in range(a, b + 1):
                self.env[m[0][1]] = str(v)
                self.run(toks, body_lo, end - 1)
            if old is None:
                self.env.pop(m[0][1], None)
            else:
                self.env[m[0][1]] = old
            return end
        return i + 1   # unknown loop form: its body is read as ordinary statements, variables unresolved

    def _bind(self, toks, open_at, hi, desc_above):
        depth, i, args, cur = 0, open_at, [], []
        close = hi
        while i < hi:
            kind, val, _ = toks[i]
            if kind == "sym" and val in "([{":
                depth += 1
                if depth > 1:
                    cur.append(toks[i])
            elif kind == "sym" and val in ")]}":
                depth -= 1
                if depth == 0:
                    args.append(cur)
                    close = i
                    break
                cur.append(toks[i])
            elif kind == "sym" and val == "," and depth == 1:
                args.append(cur)
                cur = []
            elif kind != "comment":
                cur.append(toks[i])
            i += 1
        line = toks[open_at][2]
        if not args or not args[0]:
            return close + 1
        keys_text = self.eval_terms(args[0])
        resolved = keys_text is not None
        if not resolved:
            keys_text = " ".join(str(t[1]) for t in args[0])
        desc = ""
        for a in args[2:]:
            desc = self._option(a, "description") or desc
        if not desc:
            desc = desc_above
        if not desc and close + 1 < hi and toks[close + 1][0] == "comment" and toks[close + 1][2] == toks[close][2]:
            desc = toks[close + 1][1]
        keys = [k.strip() for k in keys_text.split("+")] if resolved else []
        self.out.append(Binding([k for k in keys if k], keys_text.strip(), desc, line, resolved))
        return close + 1

    def _option(self, toks, name):
        """The value of `name = expr` at the top level of an option table {...}, as a string, or ''."""
        if not toks or toks[0][:2] != ("sym", "{"):
            return ""
        depth, i = 0, 0
        while i < len(toks) - 1:
            t = toks[i]
            if t[0] == "sym" and t[1] in "([{":
                depth += 1
            elif t[0] == "sym" and t[1] in ")]}":
                depth -= 1
            elif depth == 1 and t[:2] == ("name", name) and toks[i + 1][:2] == ("sym", "="):
                j, d = i + 2, 1
                while j < len(toks):
                    u = toks[j]
                    if u[0] == "sym" and u[1] in "([{":
                        d += 1
                    elif u[0] == "sym" and u[1] in ")]}":
                        d -= 1
                        if d == 0:
                            break
                    elif u[:2] == ("sym", ",") and d == 1:
                        break
                    j += 1
                return self.eval_terms(toks[i + 2:j]) or ""
            i += 1
        return ""


def parse_text(text, forced=None):
    """(bindings, env) of one Lua source text. `forced` fixes variables (the modifier)."""
    r = _Reader(forced)
    toks = tokenize(text)
    r.run(toks, 0, len(toks))
    return r.out, r.env


def _read(path):
    with open(path, "rb") as f:
        data = f.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("configuration file is too large")
    return data.decode("utf-8", errors="replace")


def config_dir(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get("XDG_CONFIG_HOME") or os.path.join(environ.get("HOME") or os.path.expanduser("~"), ".config")


def read_modifier(cfg_dir):
    """'ALT', 'SUPER', or '' when the file is missing or holds anything else."""
    try:
        v = _read(os.path.join(cfg_dir, MODIFIER_FILE)).strip()
    except (OSError, ValueError):
        return ""
    return v if v in MODIFIERS else ""


def write_modifier(cfg_dir, value):
    """Store the choice (atomically). Raises ValueError for anything but ALT or SUPER."""
    if value not in MODIFIERS:
        raise ValueError("the modifier is ALT or SUPER")
    path = os.path.join(cfg_dir, MODIFIER_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(value + "\n")
    os.replace(tmp, path)


def load(cfg_dir=None):
    """The bindings of ~/.config/hypr/hyprland.lua, then those of heiss-user.lua (loaded last by the configuration),
    read with the modifier the shipped configuration would use."""
    cfg_dir = cfg_dir or config_dir()
    main = os.path.join(cfg_dir, "hypr", "hyprland.lua")
    cfg = Config(main)
    try:
        text = _read(main)
    except (OSError, ValueError) as e:
        cfg.error = str(e)
        return cfg
    cfg.managed = MANAGED_MARK in text
    forced = {}
    chosen = read_modifier(cfg_dir) if cfg.managed else ""
    if chosen:
        forced["mainMod"] = chosen
    r = _Reader(forced)
    toks = tokenize(text)
    r.run(toks, 0, len(toks))
    try:
        user = _read(os.path.join(cfg_dir, "hypr", "heiss-user.lua"))
    except (OSError, ValueError):
        user = ""
    if user:
        toks = tokenize(user)
        r.run(toks, 0, len(toks))
    cfg.bindings = r.out
    cfg.main_mod = r.value_of("mainMod") or DEFAULT_MODIFIER
    return cfg
