"""What the Heiss settings window shows. No Qt here: the QML only draws this and calls it.

A page is a list of blocks (heading, text, rows, choice, field, action, items, report); the QML draws any page from
them. Every source is injected through `Env`, so tests run on fixtures. A failing source never stops the window: it
shows the error on its own page. Anything slow (the theme switch, hardware detection, `heiss check`, `hyprctl`)
runs in a worker thread: `begin(job, arg)` accepts it on the GUI thread, `finish(job, arg)` does it on the worker.
"""
import os
import re
from dataclasses import dataclass, field

from heiss_core import hyprcfg
from heiss_core import manifest as mf
from heiss_core import state as st
from heiss_core.errors import HeissError

from . import hardware_view
from . import system_tools as sysx
from . import theme as th
from . import tools
from .strings import t

PAGES = ("appearance", "display", "keyboard", "network", "audio", "packages", "hardware", "system")
LANGUAGES = ("en", "ru")
SCALES = ("1", "1.25", "1.5", "2")
LAYOUT = re.compile(r"[a-z]{2,3}(,[a-z]{2,3}){0,3}")
SCALE_LINE = re.compile(r"scale\s*=\s*([0-9.]+)")
LAYOUT_LINE = re.compile(r'kb_layout\s*=\s*"([^"]*)"')
MAX_MESSAGE = 300
MAX_REPORT = 8000
MAX_LIST = 200


def parse_os_release(text):
    out = {}
    for line in text.splitlines():
        k, sep, v = line.partition("=")
        if sep and k.strip() and not k.startswith("#"):
            out[k.strip()] = v.strip().strip('"')
    return out


@dataclass
class Env:
    cfg_dir: str = field(default_factory=hyprcfg.config_dir)
    os_release: str = "/usr/lib/os-release"
    system_answers: str = "/etc/heiss/profile.toml"
    state_file: str = "/var/lib/heiss/state.json"
    profiles_dir: str = field(default_factory=lambda: os.environ.get("HEISS_PROFILES", "/usr/share/heiss/profiles"))
    theme_get: callable = field(default_factory=lambda: th.read_current)
    apply_theme: callable = field(default_factory=lambda: th.apply_theme)
    run: callable = field(default_factory=lambda: sysx.run)
    launch: callable = field(default_factory=lambda: sysx.launch)
    monitors: callable = field(default_factory=lambda: sysx.monitors)
    layouts: callable = field(default_factory=lambda: sysx.known_layouts)
    hardware_data: callable = field(default_factory=lambda: hardware_view.collect)
    run_check: callable = field(default_factory=lambda: tools.run_check)
    kernel: callable = field(default_factory=lambda: lambda: os.uname().release)


class Model:
    def __init__(self, env=None, language="en"):
        self.env, self.language, self.page = env or Env(), language if language in LANGUAGES else "en", "appearance"
        self.busy = ""                       # the job that runs now, or ""
        self.msg = {}                        # block id -> (tone, text): the result of the last action
        self.hw_state, self.hw_data, self.hw_copied = "idle", None, False
        self.check_state, self.check_items = "idle", []

    def tr(self, key):
        return t(self.language, key)

    @staticmethod
    def _clip(text):
        text = " ".join(str(text).split())
        return text if len(text) <= MAX_MESSAGE else text[:MAX_MESSAGE - 3] + "..."

    def _err(self, e):
        return self._clip(self.tr("error.read") % e)

    def set_language(self, language):
        if language in LANGUAGES:
            self.language = language

    def open(self, page):
        if page in PAGES:
            self.page = page

    # ------------------------------------------------------------------ jobs
    JOBS = ("theme", "modifier", "layout", "scale", "launch", "detect", "check")

    def begin(self, job, arg=""):
        """Accept a job (True) or refuse it: unknown job or value, or another job is running."""
        if self.busy or job not in self.JOBS or not isinstance(arg, str):
            return False
        self._arg = arg
        valid = {"theme": lambda: arg in ("dark", "light"), "modifier": lambda: arg in hyprcfg.MODIFIERS,
                 "layout": self._layout_ok, "scale": lambda: arg in SCALES,
                 "launch": lambda: arg in sysx.PROGRAMS, "detect": lambda: True, "check": lambda: True}[job]
        ok = valid()
        if not ok:
            if job == "layout" and ok is False:
                self.msg["layout"] = ("error", self.tr("keyboard.layout.bad"))
            return False
        if job == "check":
            self.check_state, self.check_items = "running", []
        if job == "detect":
            self.hw_state, self.hw_copied = "running", False
        self.busy = job
        return True

    def _layout_ok(self):
        arg = self._arg
        if not LAYOUT.fullmatch(arg):
            return False
        known = self.env.layouts()
        if known and not all(x in known for x in arg.split(",")):
            self.msg["layout"] = ("error", self.tr("keyboard.layout.unknown"))
            return None
        return True

    def finish(self, job, arg=""):
        """Run an accepted job; called from the worker thread, the glue refreshes the screen afterwards."""
        try:
            getattr(self, "_do_" + job)(arg)
        except Exception as e:  # noqa: BLE001 - a job must never take the window down
            self.msg[job] = ("error", self._clip(str(e)))
        finally:
            self.busy = ""

    def _do_theme(self, arg):
        ok, msg = self.env.apply_theme(arg)
        self.msg["theme"] = ("ok", self.tr("appearance.done")) if ok else ("error", self._clip(self.tr("appearance.failed") % msg))

    def _reload(self, key_ok, ok_text):
        """After a write: ask the running Hyprland to read its files again."""
        rc, out = self.env.run(["hyprctl", "reload"])
        if rc == 0:
            self.msg[key_ok] = ("ok", ok_text)
        else:
            self.msg[key_ok] = ("warn", self._clip(self.tr("keyboard.reload_failed") % (out.strip() or "hyprctl")))

    def _do_modifier(self, arg):
        try:
            hyprcfg.write_modifier(self.env.cfg_dir, arg)
        except (OSError, ValueError) as e:
            self.msg["modifier"] = ("error", self._clip(self.tr("keyboard.failed") % e))
            return
        self._reload("modifier", self.tr("keyboard.mainkey.done") % self.tr("keyboard." + arg.lower()))

    def _do_layout(self, arg):
        if not LAYOUT.fullmatch(arg):   # the text becomes Lua: never trust the caller to have checked
            raise ValueError(self.tr("keyboard.layout.bad"))
        body = 'hl.config({ input = { kb_layout = "%s"%s } })' % (arg, ', kb_options = "grp:ctrl_shift_toggle"' if "," in arg else "")
        try:
            hyprcfg.set_block(self.env.cfg_dir, "keyboard", body)
        except (OSError, ValueError) as e:
            self.msg["layout"] = ("error", self._clip(self.tr("keyboard.failed") % e))
            return
        self._reload("layout", self.tr("keyboard.layout.done"))

    def _do_scale(self, arg):
        if arg not in SCALES:
            raise ValueError("scale")
        body = 'hl.monitor({ output = "", mode = "preferred", position = "auto", scale = %s })' % arg
        try:
            hyprcfg.set_block(self.env.cfg_dir, "display", body)
        except (OSError, ValueError) as e:
            self.msg["scale"] = ("error", self._clip(self.tr("display.failed") % e))
            return
        self._reload("scale", self.tr("display.done"))

    def _do_launch(self, arg):
        ok, name = self.env.launch(arg)
        if ok:
            self.msg["launch." + arg] = ("ok", "")
        else:
            self.msg["launch." + arg] = ("error", self._clip(self.tr("missing") % name))

    def _do_detect(self, arg):
        try:
            raw = self.env.hardware_data()
            drivers = [{"title": self._localized(d["name"]) or str(d["id"])[:40], "detail": self._localized(d["description"]),
                        "warning": self._localized(d["warning"], 1200),
                        "state": d["state"] if d["state"] in hardware_view.DRIVER_STATES else "unknown"} for d in raw["drivers"]]
            self.hw_data = {"facts": self._facts(raw["facts"]), "drivers": drivers, "report": self._report(raw["report"])}
            self.hw_state = "done"
        except Exception as e:  # noqa: BLE001
            self.hw_data, self.hw_state = None, "failed"
            self.msg["hardware"] = ("error", self._err(e))

    def _do_check(self, arg):
        try:
            self.check_items = [{"name": self._clip(i["name"]), "status": i["status"] if i["status"] in tools.STATUSES else "WARN",
                                 "detail": self._clip(i["detail"])} for i in self.env.run_check()]
            self.check_state = "done"
        except Exception as e:  # noqa: BLE001
            self.check_items, self.check_state = [], "failed"
            self.msg["check"] = ("error", self._err(e))

    def copy_report(self, put):
        if self.hw_data:
            put(self.hw_data["report"])
            self.hw_copied = True

    def _localized(self, d, limit=MAX_MESSAGE):
        text = " ".join(str(d.get(self.language) or d.get("en") or "").split())
        return text if len(text) <= limit else text[:limit - 3] + "..."

    @staticmethod
    def _report(text):
        text = str(text)
        return text if len(text) <= MAX_REPORT else text[:MAX_REPORT] + "\n[truncated]\n"

    def _facts(self, raw):
        out = []
        for f in raw:
            key = "fact.%s.%s" % (f["id"], f["code"])
            try:
                text = self.tr(key) % f["data"] if "%s" in self.tr(key) else self.tr(key)
            except (KeyError, TypeError):
                continue
            out.append(self._clip(text))
        return out

    # ------------------------------------------------------------------ blocks
    def _msg(self, key):
        tone, text = self.msg.get(key, ("", ""))
        return {"type": "message", "tone": tone, "text": text} if text else None

    @staticmethod
    def _choice(cid, title, options, current, note="", enabled=True):
        return {"type": "choice", "id": cid, "title": title, "note": note, "enabled": enabled,
                "options": [{"value": v, "label": label, "selected": v == current} for v, label in options]}

    def _page_appearance(self):
        try:
            cur = self.env.theme_get()
        except Exception:  # noqa: BLE001
            cur = ""
        cur = cur if cur in ("dark", "light") else ""
        return [{"type": "text", "text": self.tr("appearance.what")},
                self._choice("theme", self.tr("appearance.theme"), [(c, self.tr("theme." + c)) for c in ("dark", "light")], cur),
                self._msg("theme")]

    def _current_scale(self):
        body = hyprcfg.get_block(self.env.cfg_dir, "display") or ""
        m = SCALE_LINE.search(body)
        return m.group(1) if m and m.group(1) in SCALES else "1"

    def _page_display(self):
        blocks = [{"type": "text", "text": self.tr("display.what")}]
        try:
            rows = [{"label": m["name"], "value": "%dx%d, %s Hz, %s%%" % (m["width"], m["height"], ("%g" % m["refresh"]), "%g" % (m["scale"] * 100))}
                    for m in self.env.monitors()]
        except Exception:  # noqa: BLE001
            rows = []
        blocks.append({"type": "rows", "title": self.tr("display.monitors"), "rows": rows,
                       "empty": self.tr("display.none") if not rows else ""})
        blocks.append(self._choice("scale", self.tr("display.scale"), [(s, "%g%%" % (float(s) * 100)) for s in SCALES],
                                   self._current_scale(), self.tr("display.scale.note")))
        blocks.append(self._msg("scale"))
        return blocks

    def _page_keyboard(self):
        cfg = hyprcfg.load(self.env.cfg_dir)
        main = cfg.main_mod if cfg.main_mod in hyprcfg.MODIFIERS else hyprcfg.DEFAULT_MODIFIER
        body = hyprcfg.get_block(self.env.cfg_dir, "keyboard") or ""
        m = LAYOUT_LINE.search(body)
        blocks = [{"type": "text", "text": self.tr("keyboard.what")},
                  self._choice("modifier", self.tr("keyboard.mainkey"), [(v, self.tr("keyboard." + v.lower())) for v in hyprcfg.MODIFIERS],
                               main, self.tr("keyboard.mainkey.note"), enabled=cfg.managed)]
        if cfg.error:
            blocks.append({"type": "message", "tone": "error", "text": self._err(cfg.error)})
        elif not cfg.managed:
            blocks.append({"type": "message", "tone": "warn", "text": self.tr("keyboard.own")})
        blocks.append(self._msg("modifier"))
        blocks.append({"type": "field", "id": "layout", "title": self.tr("keyboard.layout"), "value": m.group(1) if m else "",
                       "hint": self.tr("keyboard.layout.hint"), "apply": self.tr("keyboard.layout.apply"),
                       "note": self.tr("keyboard.layout.note")})
        blocks.append(self._msg("layout"))
        return blocks

    def _action(self, key, label):
        res = self.msg.get("launch." + key)
        return {"type": "action", "id": "launch:" + key, "label": label,
                "message": res[1] if res and res[0] == "error" else ""}

    def _page_network(self):
        rc, out = self.env.run(["nmcli", "-t", "-f", "STATE,CONNECTIVITY", "general"])
        state = out.strip().replace(":", ", ") if rc == 0 and out.strip() else self.tr("network.state.none")
        return [{"type": "text", "text": self.tr("network.what")},
                {"type": "rows", "title": "", "rows": [{"label": self.tr("network.state"), "value": self._clip(state)}], "empty": ""},
                self._action("network", self.tr("network.open")), self._action("bluetooth", self.tr("bluetooth.open"))]

    def _page_audio(self):
        return [{"type": "text", "text": self.tr("audio.what")}, self._action("audio", self.tr("audio.open"))]

    def _pname(self, manifests, item_id):
        m = manifests.get(item_id)
        return (m.name.get(self.language) or m.name.get("en") or item_id) if m else item_id

    def _page_packages(self):
        rows, errors = [], []
        try:
            manifests = mf.load_dir(self.env.profiles_dir)
        except (OSError, ValueError, HeissError):
            manifests = {}
        try:
            from heiss_core import answers as ans
            a = ans.load(self.env.system_answers) if os.path.exists(self.env.system_answers) else None
            rows.append({"label": self.tr("packages.chosen"), "value": self._pname(manifests, a["profile"]) if a else self.tr("not_set")})
            rows.append({"label": self.tr("packages.addons"), "value": ", ".join(self._pname(manifests, x) for x in a["addons"]) if a and a["addons"] else self.tr("none")})
        except Exception as e:  # noqa: BLE001
            errors.append(self._err(e))
        try:
            doc = st.load(self.env.state_file)
            applied = doc["applied"]["profile"]
            rows.append({"label": self.tr("packages.applied"), "value": self._pname(manifests, applied) if applied else self.tr("not_set")})
            rows.append({"label": self.tr("packages.packages"), "value": str(min(len(doc["packages"]), 10 ** 6))})
            rows.append({"label": self.tr("packages.services"), "value": str(min(len(doc["services"]), 10 ** 6))})
        except Exception as e:  # noqa: BLE001
            errors.append(self._err(e))
        blocks = [{"type": "text", "text": self.tr("packages.what")}, {"type": "rows", "title": "", "rows": rows, "empty": ""}]
        blocks += [{"type": "message", "tone": "error", "text": e} for e in errors]
        return blocks

    def _page_hardware(self):
        blocks = [{"type": "text", "text": self.tr("hardware.what")}]
        if self.hw_state == "running":
            blocks.append({"type": "message", "tone": "", "text": self.tr("busy")})
        data = self.hw_data
        if data:
            blocks.append({"type": "rows", "title": self.tr("hardware.facts"), "rows": [{"label": "", "value": f} for f in data["facts"]], "empty": ""})
            blocks.append({"type": "rows", "title": self.tr("hardware.drivers"),
                           "rows": [{"label": d["title"], "value": self.tr("hardware.state." + d["state"]) + (" " + d["warning"] if d["warning"] else "")}
                                    for d in data["drivers"]],
                           "empty": self.tr("hardware.drivers.none") if not data["drivers"] else ""})
            blocks.append({"type": "report", "title": self.tr("hardware.report"), "text": data["report"], "copy": self.tr("hardware.copy"),
                           "copied": self.tr("hardware.copied") if self.hw_copied else ""})
        blocks.append(self._msg("hardware"))
        blocks.append({"type": "action", "id": "detect", "label": self.tr("hardware.detect"), "message": ""})
        return blocks

    def _page_system(self):
        try:
            with open(self.env.os_release, encoding="utf-8", errors="replace") as f:
                rel = parse_os_release(f.read())
        except (OSError, ValueError):
            rel = {}
        try:
            kernel = self.env.kernel()
        except Exception:  # noqa: BLE001
            kernel = ""
        un = self.tr("unknown")
        blocks = [{"type": "text", "text": self.tr("system.what")},
                  {"type": "rows", "title": "", "empty": "", "rows": [
                      {"label": self.tr("system.system"), "value": rel.get("PRETTY_NAME") or un},
                      {"label": self.tr("system.build"), "value": rel.get("BUILD_ID") or un},
                      {"label": self.tr("system.kernel"), "value": kernel or un}]},
                  {"type": "links", "links": [{"label": self.tr(k), "url": rel[v]} for k, v in (
                      ("system.home", "HOME_URL"), ("system.docs", "DOCUMENTATION_URL"), ("system.bugs", "BUG_REPORT_URL"),
                      ("system.support", "SUPPORT_URL")) if rel.get(v, "").startswith("https://")]},
                  {"type": "heading", "text": self.tr("system.check")},
                  {"type": "text", "text": self.tr("system.check.note")}]
        if self.check_state == "running":
            blocks.append({"type": "message", "tone": "", "text": self.tr("system.check.running")})
        if self.check_items:
            blocks.append({"type": "items", "items": self.check_items})
        blocks.append(self._msg("check"))
        blocks.append({"type": "action", "id": "check", "label": self.tr("system.check.run"), "message": ""})
        blocks += [{"type": "text", "text": self.tr("system.note.license")}, {"type": "text", "text": self.tr("system.note.telemetry")}]
        return blocks

    def screen(self):
        try:
            blocks = getattr(self, "_page_" + self.page)()
        except Exception as e:  # noqa: BLE001 - a page must never take the window down
            blocks = [{"type": "message", "tone": "error", "text": self._err(e)}]
        return {"page": self.page, "title": self.tr("page." + self.page), "appTitle": self.tr("app"), "busy": self.busy != "",
                "sidebar": [{"id": p, "title": self.tr("page." + p), "current": p == self.page} for p in PAGES],
                "blocks": [b for b in blocks if b]}
