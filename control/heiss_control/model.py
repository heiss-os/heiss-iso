"""What the Control Center shows. No Qt here: the QML only draws this and calls it.

Read-only in this version: every value is read from a file or a command that cannot change the system. All
sources are injected through `Env`, so tests run on fixtures. A failing source never stops the window; it
shows the error on its own card.
"""
import os
import subprocess
from dataclasses import dataclass, field

from heiss_core import answers as ans
from heiss_core import manifest as mf
from heiss_core import state as st
from heiss_core import wizard as wz
from heiss_core.errors import HeissError

from . import security
from . import theme as th
from . import tools
from .strings import t

# (id, built). Pages that are not built show the "coming soon" text, so the sidebar is the final one from day one.
PAGES = (("overview", True), ("profiles", True), ("appearance", True), ("security", True), ("updates", False),
         ("hardware", False), ("network", False), ("power", False), ("backups", False), ("advanced", True),
         ("about", True))
PAGE_IDS = tuple(p for p, _ in PAGES)
LANGUAGES = ("en", "ru")
MAX_MESSAGE = 300   # longest error text shown; messages can echo file content
MAX_LIST = 200   # longest list of package names drawn on the page


def _plasma_version():
    r = subprocess.run(["plasmashell", "--version"], capture_output=True, text=True, timeout=3)
    return r.stdout.strip().removeprefix("plasmashell").strip() if r.returncode == 0 else ""


@dataclass
class Env:
    os_release: str = "/usr/lib/os-release"
    system_answers: str = "/etc/heiss/profile.toml"
    user_dir: str = field(default_factory=lambda: os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "heiss"))
    state_file: str = "/var/lib/heiss/state.json"
    profiles_dir: str = field(default_factory=lambda: os.environ.get("HEISS_PROFILES", "/usr/share/heiss/profiles"))
    kde_value: callable = field(default_factory=lambda: th.kreadconfig)
    apply_theme: callable = field(default_factory=lambda: th.apply_theme)
    security_facts: callable = field(default_factory=lambda: security.collect)
    run_check: callable = field(default_factory=lambda: tools.run_check)
    open_settings: callable = field(default_factory=lambda: tools.open_settings)
    # default_factory: a plain lambda as a class default would be bound as a method
    kernel: callable = field(default_factory=lambda: lambda: os.uname().release)
    plasma: callable = field(default_factory=lambda: _plasma_version)


def parse_os_release(text):
    out = {}
    for line in text.splitlines():
        k, sep, v = line.partition("=")
        if sep and k.strip() and not k.startswith("#"):
            out[k.strip()] = v.strip().strip('"')
    return out


class Model:
    def __init__(self, env=None, language="en"):
        self.env, self.language, self.page = env or Env(), language if language in LANGUAGES else "en", "overview"
        self.theme_state, self.theme_message = "idle", ""   # idle | running | ok | failed
        self.check_state, self.check_items, self.check_message = "idle", [], ""   # idle | running | done | failed
        self.settings_message = ""
        self.sec_state, self.sec_facts, self.sec_message = "idle", [], ""   # idle | running | done | failed

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

    def open(self, page_id):
        if page_id in PAGE_IDS:
            self.page = page_id

    def sidebar(self):
        return [{"id": p, "title": self.tr("page." + p), "built": built, "current": p == self.page} for p, built in PAGES]

    # --- search: page titles and keywords only (no per-setting entries exist yet) ---
    def search(self, query):
        words = query.casefold().split()
        if not words:
            return []
        hits = []
        for p, built in PAGES:
            title = self.tr("page." + p).casefold()
            keys = self.tr("kw." + p).casefold()
            if all(w in title or w in keys for w in words):
                hits.append((0 if all(w in title for w in words) else 1, p, built))
        return [{"id": p, "title": self.tr("page." + p), "built": built} for _, p, built in sorted(hits, key=lambda h: h[0])]

    # --- overview ---
    def _answers(self):
        for path in (self.env.system_answers, os.path.join(self.env.user_dir, "answers.toml")):
            if os.path.exists(path):
                return ans.load(path)
        return None

    def _card(self, cid, fn):
        try:
            value, detail = fn()
            return {"id": cid, "title": self.tr("card." + cid), "value": value, "detail": detail, "error": ""}
        except Exception as e:  # a source must never stop the window, whatever it raises
            return {"id": cid, "title": self.tr("card." + cid), "value": self.tr("unknown"), "detail": "",
                    "error": self._err(e)}

    def overview(self):
        def profile():
            a = self._answers()
            return (self._pname(a["profile"]), "") if a else (self.tr("not_set"), "")

        def privacy():
            a = self._answers()
            return (self.tr("lvl." + a["privacy"]["level"]), "") if a else (self.tr("not_set"), "")

        def managed():
            s = st.load(self.env.state_file)
            return str(len(s["packages"])), ""

        def pending():
            items = wz.PendingQueue(os.path.join(self.env.user_dir, "pending.json")).list()
            failed = sum(1 for i in items if i["status"] == "failed")
            waiting = sum(1 for i in items if i["status"] == "pending")
            return str(len(items)), ", ".join(x for x in (self.tr("pending.waiting") % waiting if waiting else "",
                                                          self.tr("pending.failed") % failed if failed else "") if x)

        return {"what": self.tr("overview.what"),
                "cards": [self._card("profile", profile), self._card("privacy", privacy),
                          self._card("managed", managed), self._card("pending", pending),
                          self._card("kernel", lambda: (self.env.kernel(), ""))]}

    # --- profiles and software (read-only) ---
    def _manifests(self):
        try:
            return mf.load_dir(self.env.profiles_dir)
        except (OSError, ValueError, HeissError):
            return {}

    def _pname(self, item_id, manifests=None):
        m = (self._manifests() if manifests is None else manifests).get(item_id)
        return (m.name.get(self.language) or m.name.get("en") or item_id) if m else item_id

    def profiles(self):
        manifests, errors = self._manifests(), []
        if not manifests:
            errors.append(self._err(self.env.profiles_dir))
        rows, sections, pending = [], [], []
        try:
            a = self._answers()
            chosen = [self._pname(a["profile"], manifests)] if a else [self.tr("not_set")]
            addons = ", ".join(self._pname(x, manifests) for x in a["addons"]) if a and a["addons"] else self.tr("none")
            rows += [("profiles.chosen", chosen[0]), ("profiles.addons", addons)]
        except Exception as e:  # noqa: BLE001
            errors.append(self._err(e))
        try:
            doc = st.load(self.env.state_file)
            applied = doc["applied"]["profile"]
            rows.append(("profiles.applied", self._pname(applied, manifests) if applied else self.tr("not_set")))
            for key in ("packages", "services", "flatpaks"):
                items = sorted(doc[key])
                shown = items[:MAX_LIST] + (["... +%d" % (len(items) - MAX_LIST)] if len(items) > MAX_LIST else [])
                sections.append({"title": "%s (%d)" % (self.tr("profiles." + key), len(items)), "items": shown})
        except Exception as e:  # noqa: BLE001
            errors.append(self._err(e))
        try:
            for i in wz.PendingQueue(os.path.join(self.env.user_dir, "pending.json")).list():
                text = self.tr("profiles.pending_apply") % self._pname(i["payload"]["profile"], manifests)
                pending.append({"text": text, "status": self.tr("pstatus." + i["status"]), "error": self._clip(i["error"])})
        except Exception as e:  # noqa: BLE001
            errors.append(self._err(e))
        return {"what": self.tr("profiles.what"), "rows": [{"label": self.tr(k), "value": v} for k, v in rows],
                "sections": sections, "pendingTitle": self.tr("card.pending"), "pending": pending,
                "errors": errors, "note": self.tr("profiles.note")}

    # --- appearance: Dark and Light only ---
    def appearance(self):
        cur = th.read_current(self.env.kde_value)
        return {"what": self.tr("appearance.what"), "currentLabel": self.tr("appearance.current"),
                "current": self.tr("theme." + cur) if cur else self.tr("unknown"),
                "choices": [{"id": c, "label": self.tr("theme." + c), "selected": c == cur} for c in ("dark", "light")],
                "state": self.theme_state, "message": self.theme_message, "running": self.tr("appearance.running"),
                "note": self.tr("appearance.note")}

    def begin_theme(self, theme):
        """Accept a theme change (True) or ignore it: unknown value, or one is already running."""
        if theme not in ("dark", "light") or self.theme_state == "running":
            return False
        self.theme_state, self.theme_message = "running", ""
        return True

    def finish_theme(self, theme):
        """Runs the switch; called from a worker thread, the glue refreshes the screen afterwards."""
        try:
            ok, msg = self.env.apply_theme(theme)
        except Exception as e:  # noqa: BLE001
            ok, msg = False, str(e)
        self.theme_state, self.theme_message = ("ok", "") if ok else ("failed", self._clip(msg))

    # --- security center: read-only facts, no fixes yet ---
    def begin_security(self):
        if self.sec_state == "running":
            return False
        self.sec_state, self.sec_message = "running", ""
        return True

    def finish_security(self):
        """Collects the facts; called from a worker thread, the glue refreshes the screen afterwards."""
        try:
            facts = []
            for f in self.env.security_facts():
                status = f["status"] if f["status"] in ("ok", "warn", "info") else "info"
                facts.append({"id": str(f["id"])[:20], "status": status, "code": str(f["code"])[:30],
                              "data": self._clip(f.get("data", ""))})
            self.sec_facts, self.sec_state = facts, "done"
        except Exception as e:  # noqa: BLE001
            self.sec_facts, self.sec_state, self.sec_message = [], "failed", self._err(e)

    def _sec_text(self, key, default=""):
        try:
            return t(self.language, key)
        except KeyError:
            return default

    def security_page(self):
        items = []
        for f in self.sec_facts:
            base = "sec.%s" % f["id"]
            detail = self._sec_text("%s.%s" % (base, f["code"]), self.tr("sec.unknown_code"))
            detail = detail.replace("%s", f["data"])   # not %-formatting: the data comes from the system
            items.append({"id": f["id"], "title": self._sec_text(base, f["id"]), "status": f["status"],
                          "statusLabel": self.tr("sec.status." + f["status"]), "detail": detail,
                          "advice": self._sec_text(base + ".advice") if f["status"] == "warn" else ""})
        n = {k: sum(1 for f in self.sec_facts if f["status"] == k) for k in ("ok", "warn", "info")}
        summary = self.tr("sec.summary") % (n["ok"], len(self.sec_facts), n["warn"]) if self.sec_facts else ""
        return {"what": self.tr("sec.what"), "runLabel": self.tr("sec.run"), "running": self.tr("sec.running"),
                "state": self.sec_state, "message": self.sec_message, "items": items, "summary": summary,
                "note": self.tr("sec.note")}

    # --- advanced: stock KDE settings and the system check ---
    def advanced(self):
        return {"what": self.tr("advanced.what"), "stockTitle": self.tr("advanced.stock"),
                "openLabel": self.tr("advanced.open_settings"), "settingsMessage": self.settings_message,
                "checkTitle": self.tr("advanced.check"), "runLabel": self.tr("advanced.run_check"),
                "running": self.tr("advanced.running"), "state": self.check_state, "items": self.check_items,
                "message": self.check_message, "note": self.tr("advanced.note")}

    def open_stock_settings(self):
        try:
            ok, msg = self.env.open_settings()
        except Exception as e:  # noqa: BLE001
            ok, msg = False, str(e)
        self.settings_message = "" if ok else self._clip(msg)

    def begin_check(self):
        if self.check_state == "running":
            return False
        self.check_state, self.check_message = "running", ""
        return True

    def finish_check(self):
        """Runs `heiss check`; called from a worker thread, the glue refreshes the screen afterwards."""
        try:
            items = [{"name": self._clip(i["name"]), "status": i["status"] if i["status"] in tools.STATUSES else "WARN",
                      "detail": self._clip(i["detail"])} for i in self.env.run_check()]
            self.check_items, self.check_state = items, "done"
        except Exception as e:  # noqa: BLE001
            self.check_items, self.check_state, self.check_message = [], "failed", self._err(e)

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - same rule as the cards
            return ""

    # --- about ---
    def about(self):
        try:
            with open(self.env.os_release, encoding="utf-8", errors="replace") as f:
                rel = parse_os_release(f.read())
        except (OSError, ValueError):
            rel = {}
        plasma, kernel = self._safe(self.env.plasma), self._safe(self.env.kernel)
        un = self.tr("unknown")
        rows = [("about.system", rel.get("PRETTY_NAME") or un), ("about.build", rel.get("BUILD_ID") or un),
                ("about.kernel", kernel or un), ("about.plasma", plasma or un)]
        links = [(k, rel[v]) for k, v in (("about.home", "HOME_URL"), ("about.docs", "DOCUMENTATION_URL"),
                                          ("about.bugs", "BUG_REPORT_URL"), ("about.support", "SUPPORT_URL")) if rel.get(v)]
        return {"what": self.tr("about.what"),
                "rows": [{"label": self.tr(k), "value": v} for k, v in rows],
                "links": [{"label": self.tr(k), "url": v} for k, v in links],
                "notes": [self.tr("about.license_text"), self.tr("about.affil"), self.tr("about.telemetry")]}

    def screen(self):
        built = dict(PAGES)[self.page]
        out = {"page": self.page, "title": self.tr("page." + self.page), "built": built, "sidebar": self.sidebar(),
               "searchLabel": self.tr("search"), "noResults": self.tr("search.none"), "appTitle": self.tr("app"),
               "soonTitle": self.tr("soon"), "soonWhat": self.tr("soon.what"), "language": self.language}
        if self.page == "overview":
            out["overview"] = self.overview()
        elif self.page == "profiles":
            out["profiles"] = self.profiles()
        elif self.page == "appearance":
            out["appearance"] = self.appearance()
        elif self.page == "security":
            out["security"] = self.security_page()
        elif self.page == "advanced":
            out["advanced"] = self.advanced()
        elif self.page == "about":
            out["about"] = self.about()
        return out
