"""Versioned answers document (TOML). System part: /etc/heiss/profile.toml."""
import os
import tomllib

from .errors import ValidationError

SCHEMA_VERSION = 1
LEVELS = ("beginner", "confident", "advanced")
THEMES = ("dark", "light", "auto")
ANIMATIONS = ("full", "reduced", "off")
UPDATE_POLICIES = ("notify", "download", "weekly")
PRIVACY = ("standard", "enhanced", "maximum")
LANGUAGES = ("en", "ru")

DEFAULTS = {
    "schema_version": SCHEMA_VERSION,
    "profile": "base",
    "level": "beginner",
    "language": "en",
    "addons": [],
    "appearance": {"theme": "auto", "animations": "full"},
    "software": {"flathub": False, "update_policy": "notify"},
    "privacy": {"level": "standard"},
}

# version N -> function(doc) returning a document of version N+1
MIGRATIONS = {}


def migrate(doc, migrations=None):
    migrations = MIGRATIONS if migrations is None else migrations
    v = doc.get("schema_version")
    if not isinstance(v, int) or v < 0:
        raise ValidationError("answers: schema_version missing or invalid")
    if v > SCHEMA_VERSION:
        raise ValidationError("answers: written by a newer Heiss (schema %d > %d)" % (v, SCHEMA_VERSION))
    while v < SCHEMA_VERSION:
        if v not in migrations:
            raise ValidationError("answers: no migration from schema %d" % v)
        doc = migrations[v](dict(doc))
        v += 1
        doc["schema_version"] = v
    return doc


def _choice(value, allowed, name):
    if value not in allowed:
        raise ValidationError("answers: %s must be one of %s, got %r" % (name, allowed, value))
    return value


def validate(doc, known_profiles=None, known_addons=None):
    """Return a complete, normalized document (defaults filled in). Unknown keys are rejected."""
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in DEFAULTS.items()}
    unknown = set(doc) - set(DEFAULTS)
    if unknown:
        raise ValidationError("answers: unknown keys %s" % sorted(unknown))
    for k, v in doc.items():
        if isinstance(DEFAULTS[k], dict):
            if not isinstance(v, dict) or set(v) - set(DEFAULTS[k]):
                raise ValidationError("answers: bad section [%s]" % k)
            out[k].update(v)
        else:
            out[k] = v
    _choice(out["level"], LEVELS, "level")
    _choice(out["language"], LANGUAGES, "language")
    _choice(out["appearance"]["theme"], THEMES, "appearance.theme")
    _choice(out["appearance"]["animations"], ANIMATIONS, "appearance.animations")
    _choice(out["software"]["update_policy"], UPDATE_POLICIES, "software.update_policy")
    _choice(out["privacy"]["level"], PRIVACY, "privacy.level")
    if not isinstance(out["software"]["flathub"], bool):
        raise ValidationError("answers: software.flathub must be true or false")
    if not isinstance(out["addons"], list) or not all(isinstance(a, str) for a in out["addons"]):
        raise ValidationError("answers: addons must be a list of ids")
    if len(set(out["addons"])) != len(out["addons"]):
        raise ValidationError("answers: duplicate add-ons")
    if known_profiles is not None and out["profile"] not in known_profiles:
        raise ValidationError("answers: unknown profile %r" % out["profile"])
    if known_addons is not None:
        for a in out["addons"]:
            if a not in known_addons:
                raise ValidationError("answers: unknown add-on %r" % a)
    return out


def loads(text, **kw):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ValidationError("answers: %s" % e)
    return validate(migrate(doc), **kw)


def load(path, **kw):
    with open(path, encoding="utf-8") as f:
        return loads(f.read(), **kw)


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"%s"' % v.replace("\\", "\\\\").replace('"', '\\"')
    if isinstance(v, list):
        return "[%s]" % ", ".join(_scalar(x) for x in v)
    raise ValidationError("cannot serialize %r" % (v,))


def dumps(doc):
    lines = []
    for k, v in doc.items():
        if not isinstance(v, dict):
            lines.append("%s = %s" % (k, _scalar(v)))
    for k, v in doc.items():
        if isinstance(v, dict):
            lines += ["", "[%s]" % k] + ["%s = %s" % (kk, _scalar(vv)) for kk, vv in v.items()]
    return "\n".join(lines) + "\n"


def save(path, doc):
    from .state import atomic_write
    atomic_write(path, dumps(doc))
