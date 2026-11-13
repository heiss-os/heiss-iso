"""What the Control Center shows. No Qt here: the QML only draws this and calls it.

Read-only in this version: every value is read from a file or a command that cannot change the system. All
sources are injected through `Env`, so tests run on fixtures. A failing source never stops the window; it
shows the error on its own card.
"""
import os
import subprocess
from dataclasses import dataclass, field

from heiss_core import answers as ans
from heiss_core import state as st
from heiss_core import wizard as wz
from heiss_core.errors import HeissError

from .strings import t

# (id, built). Pages that are not built show the "coming soon" text, so the sidebar is the final one from day one.
PAGES = (("overview", True), ("profiles", False), ("appearance", False), ("security", False), ("updates", False),
         ("hardware", False), ("network", False), ("power", False), ("backups", False), ("advanced", False),
         ("about", True))
PAGE_IDS = tuple(p for p, _ in PAGES)
LANGUAGES = ("en", "ru")


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

    def tr(self, key):
        return t(self.language, key)

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
                    "error": self.tr("error.read") % e}

    def overview(self):
        def profile():
            a = self._answers()
            return (a["profile"], "") if a else (self.tr("not_set"), "")

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
        elif self.page == "about":
            out["about"] = self.about()
        return out
