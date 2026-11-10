"""Heiss Welcome: the first-run wizard model (no GUI).

The QML front end only draws this model: steps, defaults, validation, Back/Next/Skip, resume
after an interruption and the pending-actions queue all live here so they can be tested without
a display. Nothing here touches the system: applying goes through `apply.apply_plan` and the
helper, and an offline apply is queued instead of failing.

Answers that exist in the answers schema (profile, level, language, add-ons, theme, animations,
Flathub, update policy, privacy level) are validated by `answers.validate`. The other screen
options (accent, density, font size, hardware toggles, backups) are kept in `extras`: saved and
resumable, but NOT applied by anything yet (see docs/WELCOME.md).
"""
import copy
import json
import os
import time

from . import answers as ans
from . import resolver
from .errors import HeissError, ValidationError
from .state import atomic_write

STATE_VERSION = 1
# (id, skippable). Order is the screen order of the master plan (section 7).
STEPS = (("welcome", False), ("profile", False), ("level", True), ("addons", True), ("hardware", True),
         ("appearance", True), ("privacy", True), ("software", True), ("backups", True),
         ("summary", False), ("applying", False), ("done", False))
SUMMARY, APPLYING, DONE = "summary", "applying", "done"

# per-profile defaults (only keys of the answers schema); the user's own choices are never overwritten
PROFILE_DEFAULTS = {
    "base": {"privacy": {"level": "standard"}},
    "cyber": {"privacy": {"level": "enhanced"}},
    "developer": {"privacy": {"level": "standard"}},
    "custom": {"privacy": {"level": "standard"}},
}
EXTRA_KEYS = {"accent": str, "density": str, "font_scale": float, "hardware_toggles": dict, "backups": str}
PENDING_KINDS = ("apply-profile",)


def skip_all_answers():
    """Skipping the whole wizard applies Base with every default."""
    return ans.validate({})


class Wizard:
    def __init__(self, manifests, language="en"):
        self.profiles = {i for i, m in manifests.items() if m.kind == "profile"}
        self.addons = {i for i, m in manifests.items() if m.kind == "addon"}
        self.answers = ans.validate({"language": language})
        self.extras = {}
        self.touched = set()      # dotted answer paths the user chose; profile defaults skip these
        self.step = 0
        self.skipped = False

    # ----- navigation -----

    @property
    def step_id(self):
        return STEPS[self.step][0]

    def progress(self):
        """(position, total) counted over the screens the user walks through (not 'applying')."""
        ids = [s for s, _ in STEPS if s != APPLYING]
        cur = self.step_id if self.step_id != APPLYING else SUMMARY
        return ids.index(cur) + 1, len(ids)

    def can_skip(self):
        return STEPS[self.step][1]

    def next(self):
        self._check_step()
        if self.step_id in (SUMMARY, APPLYING, DONE):
            raise HeissError("use start_apply() or finish(): the summary is left by applying or saving")
        self.step += 1
        return self.step_id

    def skip(self):
        if not self.can_skip():
            raise HeissError("step %r cannot be skipped" % self.step_id)
        self.step += 1      # keeps the defaults and whatever was already chosen
        return self.step_id

    def back(self):
        if self.step_id in (APPLYING, DONE) or self.step == 0:
            raise HeissError("cannot go back from %r" % self.step_id)
        self.step -= 1      # answers are kept
        return self.step_id

    def skip_whole(self):
        self.answers, self.extras, self.touched, self.skipped = skip_all_answers(), {}, set(), True
        self.step = [s for s, _ in STEPS].index(DONE)

    def _check_step(self):
        if self.step_id == "profile" and self.answers["profile"] not in self.profiles:
            raise ValidationError("choose one of the profiles")

    # ----- answers -----

    def set(self, path, value):
        """Set one answer by dotted path ("profile", "appearance.theme") or an extras key ("extra.accent")."""
        if path.startswith("extra."):
            key = path[6:]
            if key not in EXTRA_KEYS or not isinstance(value, EXTRA_KEYS[key]):
                raise ValidationError("unknown or badly typed option %r" % path)
            self.extras[key] = value
            return
        trial = copy.deepcopy(self.answers)
        node = trial
        *head, last = path.split(".")
        for p in head:
            node = node[p] if isinstance(node, dict) and p in node else self._bad(path)
        if not isinstance(node, dict) or last not in node or last == "schema_version":
            self._bad(path)
        node[last] = value
        ans.validate(trial, self.profiles, self.addons)    # raises on a bad value; self.answers stays untouched
        self.answers = trial
        self.touched.add(path)
        if path == "profile":
            self._apply_profile_defaults()

    @staticmethod
    def _bad(path):
        raise ValidationError("unknown answer %r" % path)

    def _apply_profile_defaults(self):
        for section, vals in PROFILE_DEFAULTS.get(self.answers["profile"], {}).items():
            for k, v in vals.items():
                if "%s.%s" % (section, k) not in self.touched:
                    self.answers[section][k] = v

    def final_answers(self):
        return ans.validate(self.answers, self.profiles, self.addons)

    def advanced_visible(self):
        """Advanced sections (for example linux-hardened in the privacy step) only for Confident and Advanced."""
        return self.answers["level"] in ("confident", "advanced")

    def confirmations(self):
        """Beginner: confirm every change in plain words; Advanced: one summary confirmation."""
        return self.answers["level"] != "advanced"

    # ----- resume -----

    def to_dict(self):
        return {"version": STATE_VERSION, "step": self.step_id, "answers": self.answers, "extras": self.extras,
                "touched": sorted(self.touched), "skipped": self.skipped}

    @classmethod
    def from_dict(cls, doc, manifests):
        if not isinstance(doc, dict) or doc.get("version") != STATE_VERSION:
            raise ValidationError("wizard state: unsupported version")
        w = cls(manifests)
        w.answers = ans.validate(doc.get("answers", {}), w.profiles, w.addons)
        extras = doc.get("extras", {})
        if not isinstance(extras, dict) or any(k not in EXTRA_KEYS or not isinstance(v, EXTRA_KEYS[k]) for k, v in extras.items()):
            raise ValidationError("wizard state: bad extras")
        w.extras, w.touched, w.skipped = extras, set(doc.get("touched", [])), bool(doc.get("skipped"))
        ids = [s for s, _ in STEPS]
        if doc.get("step") not in ids:
            raise ValidationError("wizard state: unknown step")
        # an interrupted apply restarts from the summary: the plan is recomputed against the real system
        w.step = ids.index(SUMMARY) if doc["step"] == APPLYING else ids.index(doc["step"])
        return w


class Store:
    """~/.config/heiss: wizard-state.json (resume), welcome-done (marker), answers.toml (saved answers), pending.json."""

    def __init__(self, config_dir):
        self.dir = config_dir

    def p(self, name):
        return os.path.join(self.dir, name)

    def is_done(self):
        return os.path.exists(self.p("welcome-done"))

    def mark_done(self):
        atomic_write(self.p("welcome-done"), "")
        self.clear()

    def save(self, wiz):
        atomic_write(self.p("wizard-state.json"), json.dumps(wiz.to_dict(), indent=2, sort_keys=True) + "\n")

    def load(self, manifests):
        """Resumed wizard, or None when there is nothing usable (a corrupt file is ignored, never fatal)."""
        try:
            with open(self.p("wizard-state.json"), encoding="utf-8") as f:
                return Wizard.from_dict(json.load(f), manifests)
        except (OSError, ValueError, HeissError):
            return None

    def clear(self):
        try:
            os.unlink(self.p("wizard-state.json"))
        except FileNotFoundError:
            pass

    def save_answers(self, wiz):
        ans.save(self.p("answers.toml"), wiz.final_answers())


def summary_plan(wiz, manifests, state, system, adopt=True):
    """What Apply would do: the resolver plan for the current answers (reads the system, changes nothing)."""
    return resolver.resolve(wiz.final_answers(), manifests, state, system, adopt=adopt)


# ---------- pending actions ----------

class PendingQueue:
    """Actions that need the network or a later moment; run from the Control Center. Order is kept."""

    def __init__(self, path):
        self.path = path

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                items = json.load(f)
        except FileNotFoundError:
            return []
        except ValueError as e:
            raise ValidationError("pending queue: %s" % e)
        if not isinstance(items, list):
            raise ValidationError("pending queue: must be a list")
        return items

    def _save(self, items):
        atomic_write(self.path, json.dumps(items, indent=2, sort_keys=True) + "\n")

    def list(self):
        return self._load()

    def add(self, kind, payload, now=None):
        if kind not in PENDING_KINDS:
            raise ValidationError("unknown pending action %r" % kind)
        items = self._load()
        item = {"id": (max([i["id"] for i in items]) + 1) if items else 1, "kind": kind, "payload": payload,
                "created": int(now if now is not None else time.time()), "status": "pending", "error": ""}
        self._save(items + [item])
        return item

    def remove(self, item_id):
        self._save([i for i in self._load() if i["id"] != item_id])

    def run(self, executor, online):
        """Run pending items in order. Offline: nothing runs. A failure stops the run and keeps the item
        (status 'failed', with the message) so the user can retry or remove it. Returns the ids that were done."""
        if not online:
            return []
        items, done = self._load(), []
        for it in items:
            if it["status"] == "done":
                continue
            try:
                executor(it)
            except HeissError as e:
                it["status"], it["error"] = "failed", str(e)
                break
            it["status"], it["error"] = "done", ""
            done.append(it["id"])
        self._save([i for i in items if i["status"] != "done"])
        return done


def queue_apply(queue, wiz):
    """'Save answers and apply later', or an apply attempted without a network."""
    a = wiz.final_answers()
    return queue.add("apply-profile", {"profile": a["profile"], "addons": a["addons"]})
