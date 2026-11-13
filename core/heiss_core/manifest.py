"""Profile and add-on manifests (TOML, parsed with stdlib tomllib).

A manifest declares what a profile or add-on installs. Everything is validated
strictly: unknown keys, bad names and unsafe paths are rejected, because the
privileged helper will only ever act on data that passed this validation.
"""
import os
import re
import tomllib
from dataclasses import dataclass, field

from .errors import ValidationError

ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
PKG_RE = re.compile(r"^[a-z0-9@_+][a-z0-9@._+-]{0,99}$")   # never starts with - or . (option injection)
FLATPAK_RE = re.compile(r"^[A-Za-z0-9._-]{3,200}$")
UNIT_RE = re.compile(r"^[A-Za-z0-9@:._-]{1,100}\.(service|timer|socket)$")
KINDS = ("profile", "addon")
TIERS = ("essential", "important", "extended")
# post-actions are ids resolved by the helper, never shell strings
POST_ACTIONS = {"update-desktop-database", "update-mime-database", "mkinitcpio", "grub-mkconfig"}
ALLOWED_KEYS = {
    "schema_version", "id", "kind", "tier", "name", "description", "requires", "conflicts",
    "packages", "flatpaks", "services", "dropins", "kde_settings", "post_actions", "size",
}


@dataclass(frozen=True)
class Manifest:
    id: str
    kind: str
    tier: str
    name: dict
    description: dict
    requires: tuple = ()
    conflicts: tuple = ()
    packages: tuple = ()
    flatpaks: tuple = ()
    services: tuple = ()
    dropins: tuple = ()        # ({"path": ..., "content": ...},)
    kde_settings: tuple = ()   # ({"file","group","key","value"},)
    post_actions: tuple = ()
    size: dict = field(default_factory=dict)  # optional {"download_mib", "installed_mib"}


def _strs(doc, key, regex, where):
    vals = doc.get(key, [])
    if not isinstance(vals, list) or not all(isinstance(v, str) for v in vals):
        raise ValidationError("%s: '%s' must be a list of strings" % (where, key))
    for v in vals:
        if not regex.fullmatch(v):   # fullmatch: "$" alone would let a trailing newline through
            raise ValidationError("%s: invalid %s entry %r" % (where, key, v))
    if len(set(vals)) != len(vals):
        raise ValidationError("%s: duplicate entries in '%s'" % (where, key))
    return tuple(vals)


def _text(doc, key, where):
    t = doc.get(key)
    if not isinstance(t, dict) or not t.get("en") or not t.get("ru"):
        raise ValidationError("%s: '%s' needs non-empty 'en' and 'ru' texts" % (where, key))
    if set(t) - {"en", "ru"}:
        raise ValidationError("%s: '%s' has unsupported languages" % (where, key))
    return dict(t)


def _dropins(doc, where):
    out = []
    for d in doc.get("dropins", []):
        path = d.get("path", "")
        if set(d) != {"path", "content"} or not isinstance(d["content"], str):
            raise ValidationError("%s: dropin needs exactly 'path' and 'content'" % where)
        norm = os.path.normpath(path)
        if norm != path or not path.startswith("/etc/") or ".d/" not in path or ".." in path:
            raise ValidationError("%s: dropin path %r must be a normalized /etc/**/*.d/ file" % (where, path))
        out.append({"path": path, "content": d["content"]})
    return tuple(out)


def _kde(doc, where):
    out = []
    for k in doc.get("kde_settings", []):
        if set(k) != {"file", "group", "key", "value"} or not all(isinstance(v, str) for v in k.values()):
            raise ValidationError("%s: kde_settings entries need file, group, key, value (strings)" % where)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", k["file"]):
            raise ValidationError("%s: bad kde_settings file %r" % (where, k["file"]))
        out.append(dict(k))
    return tuple(out)


def parse(doc, source="manifest"):
    where = source
    unknown = set(doc) - ALLOWED_KEYS
    if unknown:
        raise ValidationError("%s: unknown keys %s" % (where, sorted(unknown)))
    if doc.get("schema_version") != 1:
        raise ValidationError("%s: schema_version must be 1" % where)
    mid = doc.get("id", "")
    if not isinstance(mid, str) or not ID_RE.fullmatch(mid):
        raise ValidationError("%s: invalid id %r" % (where, mid))
    if doc.get("kind") not in KINDS:
        raise ValidationError("%s: kind must be one of %s" % (where, KINDS))
    if doc.get("tier", "important") not in TIERS:
        raise ValidationError("%s: tier must be one of %s" % (where, TIERS))
    actions = doc.get("post_actions", [])
    if not isinstance(actions, list) or set(actions) - POST_ACTIONS:
        raise ValidationError("%s: post_actions must be a subset of %s" % (where, sorted(POST_ACTIONS)))
    size = doc.get("size", {})
    if set(size) - {"download_mib", "installed_mib"} or not all(isinstance(v, (int, float)) for v in size.values()):
        raise ValidationError("%s: size allows numeric download_mib/installed_mib only" % where)
    return Manifest(
        id=mid, kind=doc["kind"], tier=doc.get("tier", "important"),
        name=_text(doc, "name", where), description=_text(doc, "description", where),
        requires=_strs(doc, "requires", ID_RE, where), conflicts=_strs(doc, "conflicts", ID_RE, where),
        packages=_strs(doc, "packages", PKG_RE, where), flatpaks=_strs(doc, "flatpaks", FLATPAK_RE, where),
        services=_strs(doc, "services", UNIT_RE, where), dropins=_dropins(doc, where),
        kde_settings=_kde(doc, where), post_actions=tuple(actions), size=dict(size),
    )


def load_dir(path):
    """Load every *.toml in a directory. Returns {id: Manifest}; checks references and cycles."""
    manifests = {}
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".toml"):
            continue
        with open(os.path.join(path, fn), "rb") as f:
            try:
                doc = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise ValidationError("%s: %s" % (fn, e))
        m = parse(doc, fn)
        if fn != m.id + ".toml":
            raise ValidationError("%s: file name must match id %r" % (fn, m.id))
        manifests[m.id] = m
    check_graph(manifests)
    return manifests


def check_graph(manifests):
    for m in manifests.values():
        for ref in m.requires + m.conflicts:
            if ref not in manifests:
                raise ValidationError("%s references unknown manifest %r" % (m.id, ref))
    state = {}

    def visit(mid, trail):
        if state.get(mid) == 2:
            return
        if state.get(mid) == 1:
            raise ValidationError("dependency cycle: %s" % " -> ".join(trail + [mid]))
        state[mid] = 1
        for r in manifests[mid].requires:
            visit(r, trail + [mid])
        state[mid] = 2

    for mid in manifests:
        visit(mid, [])


def closure(manifests, ids):
    """Selected ids plus everything they require, in dependency order (requirements first)."""
    order, seen = [], set()

    def visit(mid):
        if mid in seen:
            return
        seen.add(mid)
        for r in manifests[mid].requires:
            visit(r)
        order.append(mid)

    for i in ids:
        if i not in manifests:
            raise ValidationError("unknown profile or add-on %r" % i)
        visit(i)
    for a in order:
        for c in manifests[a].conflicts:
            if c in seen:
                raise ValidationError("%r conflicts with %r" % (a, c))
    return order
