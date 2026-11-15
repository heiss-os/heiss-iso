"""State file: which packages, services and flatpaks Heiss itself installed.

A profile change may remove ONLY things recorded here. Writes are atomic and
guarded by a lock so two Heiss processes cannot interleave.
"""
import contextlib
import fcntl
import json
import os
import tempfile

from .errors import ValidationError

STATE_VERSION = 1
EMPTY = {"schema_version": STATE_VERSION, "applied": {"profile": None, "addons": []},
         "packages": [], "services": [], "flatpaks": []}


def atomic_write(path, text, mode=0o600):
    """Write `text` to `path` through a temporary file in the same directory. The file gets exactly `mode`
    (default: private to the writer; mkstemp creates 0600 and the umask no longer matters)."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), mode)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return json.loads(json.dumps(EMPTY))
    return parse(text)


def parse(text):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValidationError("state: %s" % e)
    if not isinstance(doc, dict):
        raise ValidationError("state: top level must be an object")
    if doc.get("schema_version") != STATE_VERSION:
        raise ValidationError("state: unsupported schema_version %r" % doc.get("schema_version"))
    for k in ("packages", "services", "flatpaks"):
        if not isinstance(doc.get(k), list) or not all(isinstance(x, str) for x in doc[k]):
            raise ValidationError("state: '%s' must be a list of strings" % k)
    return doc


def save(path, doc):
    doc = dict(doc)
    for k in ("packages", "services", "flatpaks"):
        doc[k] = sorted(set(doc[k]))
    # The state file is written by root (the helper) and read by ordinary users (the Control Center, `heiss profile
    # apply` for the plan). It only lists package, service and flatpak names, so it is world-readable; only
    # root can write it. The directory is created readable for the same reason.
    d = os.path.dirname(path) or "."
    if not os.path.isdir(d):
        os.makedirs(d, mode=0o755, exist_ok=True)
        os.chmod(d, 0o755)
    atomic_write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n", mode=0o644)


@contextlib.contextmanager
def lock(path):
    """Exclusive, non-blocking lock next to the state file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValidationError("another heiss process holds the lock")
        yield
    finally:
        os.close(fd)
