"""What the screens show, and what the buttons do. No Qt here: the QML only draws this and calls it.

Every action returns the new screen dict, and saves the resume state after a step change. The wizard
rules (validation, order, skip, defaults) stay in heiss_core.wizard.
"""
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
    def __init__(self, wizard, manifests, store=None, queue=None, detector=None):
        """detector: callable returning a heiss_core.hardware.Report (may raise); None means no detection."""
        self.w, self.manifests, self.store, self.queue = wizard, manifests, store, queue
        self.detector, self._report, self._detected = detector, None, False
        self.error = ""

    def report(self):
        """Detection runs once, when the hardware screen is first shown. A failure means no proposals."""
        if not self._detected:
            self._detected = True
            try:
                self._report = self.detector() if self.detector else None
            except Exception:  # detection is advisory: never block the wizard
                self._report = None
        return self._report

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
        lines = []
        if sid == wz.SUMMARY:
            a = w.final_answers()
            lines = ["%s: %s" % (t(lang, "summary.profile"), self._name(a["profile"])),
                     "%s: %s" % (t(lang, "summary.addons"),
                                 ", ".join(self._name(i) for i in a["addons"]) or t(lang, "summary.none"))]
        what = t(lang, sid + ".what") if sid != "done" else t(lang, "done.skipped" if w.skipped else "done.what")
        return {"id": sid, "title": t(lang, sid + ".title") if sid != "done" else t(lang, "done.title"),
                "facts": facts, "what": what, "whatLabel": t(lang, "what"), "lines": lines, "questions": questions,
                "progressText": t(lang, "step_of") % (pos, total), "progress": pos / total,
                "canBack": w.step > 0 and sid not in (wz.APPLYING, wz.DONE),
                "canSkip": w.can_skip(), "isFirst": sid == "welcome", "isSummary": sid == wz.SUMMARY,
                "isDone": sid == wz.DONE, "error": self.error,
                "labels": {k: t(lang, k) for k in ("back", "next", "skip", "start", "skip_all", "save_later", "close")}}

    # ----- actions -----

    def _run(self, fn):
        self.error = ""
        try:
            fn()
        except HeissError as e:
            self.error = "%s %s" % (t(self.lang, "err"), e)
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

    def _finish_saved(self):
        self.w.finish()
        if self.store:
            self.store.save_answers(self.w)
        if self.queue:
            wz.queue_apply(self.queue, self.w)
        self._mark_done()

    def _mark_done(self):
        if self.store:
            self.store.mark_done()
