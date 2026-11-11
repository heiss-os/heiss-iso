"""What the screens show, and what the buttons do. No Qt here: the QML only draws this and calls it.

Every action returns the new screen dict, and saves the resume state after a step change. The wizard
rules (validation, order, skip, defaults) stay in heiss_core.wizard.
"""
import threading

from heiss_core import wizard as wz
from heiss_core.errors import HeissError

from .strings import t

LEVELS = ("beginner", "confident", "advanced")
# step -> [(path, label key prefix, label key of the question or None, values)]
CHOICES = {
    "welcome": [("language", None, "language", ("en", "ru"))],
    "level": [("level", "level.", None, LEVELS)],
    "appearance": [("appearance.theme", "theme.", "theme", ("dark", "light", "auto")),
                   ("appearance.animations", "anim.", "animations", ("full", "reduced", "off"))],
    "privacy": [("privacy.level", "privacy.", None, ("standard", "enhanced", "maximum"))],
    "software": [("software.flathub", "", "flathub", (True, False)),
                 ("software.update_policy", "upd.", "update_policy", ("notify", "download", "weekly"))],
}


# privacy items: (string key, implemented today, only for Confident/Advanced). Only the firewall is real:
# Essentials ships and enables firewalld at every level. Everything else is not applied by anything yet.
PRIVACY_ITEMS = (("pv.firewall", True, False), ("pv.dns", False, False), ("pv.mac", False, False),
                 ("pv.vpn", False, False), ("pv.bt", False, False), ("pv.lock", False, False),
                 ("pv.hardened", False, True))


def _get(answers, path):
    node = answers
    for p in path.split("."):
        node = node[p]
    return node


class ViewModel:
    def __init__(self, wizard, manifests, store=None, queue=None, detector=None, applier=None, spawn=None):
        """detector: callable returning a heiss_core.hardware.Report (may raise); None means no detection.
        applier: object with plan(answers) -> dict and run(answers, on_line, on_step); None means Apply is not
        offered. spawn(fn) runs fn on a worker thread (tests pass a synchronous one); on_update() is called from
        that thread whenever the job changes (the Qt glue refreshes the screen from it)."""
        self.w, self.manifests, self.store, self.queue = wizard, manifests, store, queue
        self.detector, self._report, self._detected = detector, None, False
        self.applier, self.on_update = applier, None
        self._spawn = spawn or (lambda fn: threading.Thread(target=fn, daemon=True).start())
        self._lock = threading.Lock()
        self._job = {"status": "idle", "step": "", "log": [], "error": ""}   # idle | running | failed | ok
        self._plan = None
        self.error = ""

    def _status(self):
        with self._lock:
            return self._job["status"]

    def _plan_facts(self, lang):
        """(lines, ok): what Apply would change. Computed on a worker thread, once per selection; a failure is
        shown but not kept when the user leaves the summary, so it is tried again on return."""
        a = self.w.final_answers()
        hwids = self.hardware_ids()
        key = (a["profile"], tuple(a["addons"]), tuple(hwids))
        with self._lock:
            cur = self._plan
            start = cur is None or cur["key"] != key
            if start:
                self._plan = cur = {"key": key, "state": "computing", "plan": None, "err": ""}
        if start:
            self._spawn(lambda: self._plan_job(key, a, hwids))
            with self._lock:
                cur = self._plan
        if cur["state"] == "computing":
            return [t(lang, "plan.computing")], False
        if cur["state"] == "failed":
            return ["%s %s" % (t(lang, "plan.failed"), cur["err"])], False
        plan = cur["plan"]
        rows = [("plan.install", "install_packages"), ("plan.remove", "remove_packages"),
                ("plan.enable", "enable_services"), ("plan.disable", "disable_services")]
        lines = ["%s: %d" % (t(lang, k), len(plan.get(f) or [])) for k, f in rows if plan.get(f)]
        return lines or [t(lang, "plan.nothing")], True

    def _plan_job(self, key, answers, hardware):
        """Worker thread body (never raises)."""
        try:
            res = {"state": "ok", "plan": self.applier.plan(answers, hardware), "err": ""}
        except HeissError as e:
            res = {"state": "failed", "plan": None, "err": str(e)}
        except Exception as e:
            res = {"state": "failed", "plan": None, "err": "unexpected error: %s" % e}
        with self._lock:
            if self._plan and self._plan["key"] == key:
                self._plan.update(res)
        if self.on_update:
            self.on_update()

    def report(self):
        """Detection runs once, when the hardware screen is first shown. A failure means no proposals."""
        if not self._detected:
            self._detected = True
            try:
                self._report = self.detector() if self.detector else None
            except Exception:  # detection is advisory: never block the wizard
                self._report = None
        return self._report

    def hardware_ids(self):
        """Hardware profiles the user left ticked (what Apply installs). Detection failed: none."""
        r = self.report()
        return sorted(p.id for p in r.proposals if self._hw_selected(p)) if r else []

    def _hw_selected(self, p):
        return self.w.extras.get("hardware_toggles", {}).get(p.id, p.safe_by_default)

    def _hardware(self, lang):
        r, facts, opts = self.report(), [], []
        if r is None:
            return [{"text": t(lang, "hw.failed"), "badge": ""}], opts
        form = {"desktop": "hw.desktop", "laptop": "hw.laptop", "vm": "hw.vm"}.get(r.form_factor, "hw.unknown")
        facts = [{"text": "%s: %s" % (t(lang, "hw.form"), t(lang, form)), "badge": ""},
                 {"text": "%s: %s" % (t(lang, "hw.cpu"), r.cpu_vendor or t(lang, "hw.unknown")), "badge": ""}]
        if r.virt != "none":
            facts.append({"text": "%s: %s" % (t(lang, "hw.virt"), r.virt), "badge": ""})
        facts += [{"text": "%s: %s:%s" % (t(lang, "hw.gpu"), g["vendor"], g["device"]), "badge": ""} for g in r.gpus]
        if r.hybrid_graphics:
            facts.append({"text": t(lang, "hw.hybrid"), "badge": ""})
        if not r.proposals:
            facts.append({"text": t(lang, "hw.none"), "badge": ""})
        for p in r.proposals:
            hint = p.description.get(lang, "") + ("  %s: %s" % (t(lang, "hw.warning"), p.warnings[lang])
                                                  if p.warnings.get(lang) else "")
            opts.append({"path": "hardware", "value": p.id, "hint": hint, "selected": self._hw_selected(p),
                         "label": "%s (%s)" % (p.name.get(lang, p.id),
                                               t(lang, "hw.safe" if p.safe_by_default else "hw.confirm"))})
        return facts, opts

    def _privacy_facts(self, lang):
        adv = self.w.advanced_visible()
        return [{"text": t(lang, k), "badge": t(lang, "pv.done" if done else "pv.soon")}
                for k, done, only_adv in PRIVACY_ITEMS if adv or not only_adv]

    @property
    def lang(self):
        return self.w.answers["language"]

    def _name(self, mid):
        return self.manifests[mid].name.get(self.lang) or self.manifests[mid].name["en"]

    def _label(self, prefix, v):
        if isinstance(v, bool):
            return t(self.lang, "yes" if v else "no")
        if prefix is None:
            return t(self.lang, "lang_" + v)
        return t(self.lang, prefix + v)

    def _opt(self, path, value, label, hint=""):
        return {"path": path, "value": value, "label": label, "hint": hint,
                "selected": _get(self.w.answers, path) == value}

    def _cards(self, tier_not):
        return sorted((m for m in self.manifests.values() if m.kind == "profile" and m.tier != tier_not),
                      key=lambda m: m.id)

    def screen(self):
        w, lang, sid = self.w, self.lang, self.w.step_id
        pos, total = w.progress()
        questions = []
        for path, prefix, qkey, values in CHOICES.get(sid, []):
            questions.append({"title": t(lang, qkey) if qkey else "", "kind": "choice", "path": path,
                              "options": [self._opt(path, v, self._label(prefix, v)) for v in values]})
        if sid == "profile":
            questions.append({"title": "", "kind": "choice", "path": "profile", "options": [
                self._opt("profile", m.id, self._name(m.id), m.description.get(lang, "")) for m in self._cards("essential")]})
        if sid == "addons":
            have = set(w.answers["addons"])
            questions.append({"title": "", "kind": "multi", "path": "addons", "options": [
                {"path": "addons", "value": m.id, "label": self._name(m.id), "hint": m.description.get(lang, ""),
                 "selected": m.id in have} for m in sorted(self.manifests.values(), key=lambda m: m.id)
                if m.kind == "addon"]})
        facts = []
        if sid == "hardware":
            facts, opts = self._hardware(lang)
            if opts:
                questions.append({"title": "", "kind": "multi", "path": "hardware", "options": opts})
        if sid == "privacy":
            facts = self._privacy_facts(lang)
        if sid == "backups":
            facts = [{"text": t(lang, "hardware.soon"), "badge": ""}]
        lines, plan_ok = [], False
        if sid == wz.SUMMARY:
            a = w.final_answers()
            lines = ["%s: %s" % (t(lang, "summary.profile"), self._name(a["profile"])),
                     "%s: %s" % (t(lang, "summary.addons"),
                                 ", ".join(self._name(i) for i in a["addons"]) or t(lang, "summary.none"))]
            if self.applier and self.hardware_ids():
                lines.append("%s: %s" % (t(lang, "summary.hardware"), ", ".join(self.hardware_ids())))
            if self.applier:
                more, plan_ok = self._plan_facts(lang)
                lines += more
        with self._lock:
            job = dict(self._job, log=self._job["log"][-12:])
        applying = sid == wz.APPLYING
        what_key = {"summary": "summary.what_apply" if self.applier else "summary.what"}.get(sid, sid + ".what")
        if sid == "done":
            what_key = "done.skipped" if w.skipped else ("done.applied" if job["status"] == "ok" else "done.what")
        what = t(lang, what_key)
        return {"id": sid, "title": t(lang, sid + ".title") if sid != "done" else t(lang, "done.title_applied" if job["status"] == "ok" else "done.title"),
                "facts": facts, "what": what, "whatLabel": t(lang, "what"), "lines": lines, "questions": questions,
                "progressText": t(lang, "step_of") % (pos, total), "progress": pos / total,
                "canBack": w.step > 0 and sid not in (wz.APPLYING, wz.DONE),
                "canSkip": w.can_skip(), "isFirst": sid == "welcome", "isSummary": sid == wz.SUMMARY,
                "isDone": sid == wz.DONE, "error": self.error or (job["error"] if applying else ""),
                "job": job, "isApplying": applying, "isRunning": applying and job["status"] == "running",
                "canApply": sid == wz.SUMMARY and plan_ok, "canRetry": applying and job["status"] == "failed",
                "canSaveLater": (sid == wz.SUMMARY) or (applying and job["status"] == "failed"),
                "labels": {k: t(lang, k) for k in ("back", "next", "skip", "start", "skip_all", "save_later", "close",
                                                    "apply", "retry")}}

    # ----- actions -----

    def _run(self, fn):
        self.error = ""
        try:
            fn()
        except HeissError as e:
            self.error = "%s %s" % (t(self.lang, "err"), e)
        return self.refresh()

    def refresh(self):
        """GUI thread only: pick up a finished job, drop a stale failed plan, save the resume state, redraw."""
        self._finalize()
        if self.w.step_id != wz.SUMMARY:
            with self._lock:
                if self._plan and self._plan["state"] == "failed":
                    self._plan = None
        self._save()
        return self.screen()

    def _save(self):
        if self.store and self.w.step_id != wz.DONE:
            self.store.save(self.w)

    def choose(self, path, value):
        return self._run(lambda: self.w.set(path, value))

    def toggle_addon(self, addon_id):
        cur = list(self.w.answers["addons"])
        cur.remove(addon_id) if addon_id in cur else cur.append(addon_id)
        return self._run(lambda: self.w.set("addons", cur))

    def toggle_hardware(self, proposal_id):
        r = self.report()
        known = {p.id: p for p in r.proposals} if r else {}
        if proposal_id not in known:
            return self._run(lambda: self.w.set("extra.nosuch", 0))   # rejected like any unknown option
        cur = dict(self.w.extras.get("hardware_toggles", {}))
        cur[proposal_id] = not self._hw_selected(known[proposal_id])
        return self._run(lambda: self.w.set("extra.hardware_toggles", cur))

    def next(self):
        return self._run(self.w.next)

    def back(self):
        return self._run(self.w.back)

    def skip(self):
        return self._run(self.w.skip)

    def skip_whole(self):
        return self._run(self._finish_skipped)

    def _finish_skipped(self):
        self.w.skip_whole()
        self._mark_done()

    def save_later(self):
        return self._run(self._finish_saved)

    # ----- apply (5e) -----

    def start_apply(self):
        return self._run(self._begin_apply)

    def _begin_apply(self):
        if self.applier is None:
            raise HeissError("applying is not available in this build")
        self.w.start_apply()
        self._launch()

    def retry_apply(self):
        def go():
            if self.w.step_id != wz.APPLYING or self._status() != "failed":
                raise HeissError("nothing to retry")
            self._launch()
        return self._run(go)

    def _launch(self):
        answers = self.w.final_answers()      # read on the GUI thread; the worker never touches the wizard
        hardware = self.hardware_ids()
        with self._lock:
            if self._job["status"] == "running":
                return
            self._job = {"status": "running", "step": "", "log": [], "error": ""}
        self._spawn(lambda: self.run_job(answers, hardware))

    def _update(self, **kw):
        with self._lock:
            self._job.update(kw)
        if self.on_update:
            self.on_update()

    def run_job(self, answers, hardware=()):
        """Worker thread body. Never raises, and touches only the job record (under the lock): the wizard and
        the store belong to the GUI thread, which finishes the job in _finalize()."""
        def on_line(text):
            with self._lock:
                self._job["log"] = (self._job["log"] + [text])[-200:]
            if self.on_update:
                self.on_update()

        def on_step(n, total, desc):
            self._update(step="[%d/%d] %s" % (n, total, desc))
        try:
            self.applier.run(answers, on_line, on_step, hardware)
        except HeissError as e:
            return self._update(status="failed", error=str(e))
        except Exception as e:   # the thread must not die silently
            return self._update(status="failed", error="unexpected error: %s" % e)
        self._update(status="applied")

    def _finalize(self):
        """GUI thread: a job that applied successfully becomes 'done'. The answers are saved first and the step
        moves last, so a failed save leaves the applying screen with the error visible (Try again is offered)."""
        if self._status() != "applied":
            return
        try:
            if self.store:
                self.store.save_answers(self.w)
                self.store.mark_done()
            self.w.finish()
        except Exception as e:
            with self._lock:
                self._job.update(status="failed", error="applied, but saving the result failed: %s" % e)
            return
        with self._lock:
            self._job["status"] = "ok"

    def _finish_saved(self):
        if self._status() in ("running", "applied"):
            raise HeissError("wait until applying has finished")
        self.w.finish()
        if self.store:
            self.store.save_answers(self.w)
        if self.queue:
            wz.queue_apply(self.queue, self.w)
        self._mark_done()

    def _mark_done(self):
        if self.store:
            self.store.mark_done()
