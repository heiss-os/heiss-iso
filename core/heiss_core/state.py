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


def atomic_write(path, text):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
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
            doc = json.load(f)
    except FileNotFoundError:
        return json.loads(json.dumps(EMPTY))
    except json.JSONDecodeError as e:
        raise ValidationError("state: %s" % e)
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
    atomic_write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")


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
