"""Trusted allowlists and parameter validation (pure, no side effects except write_dropin)."""
import os
import stat

from heiss_core import hardware as hw
from heiss_core import manifest as mf
from heiss_core import state as st

from .errors import invalid

MAX_ITEMS = 500
# post-actions are ids; the argv is fixed here, never taken from a client or a manifest
POST_ACTION_ARGV = {
    "update-desktop-database": ["update-desktop-database", "-q"],
    "update-mime-database": ["update-mime-database", "/usr/share/mime"],
    "mkinitcpio": ["mkinitcpio", "-P"],
    "grub-mkconfig": ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
}
assert set(POST_ACTION_ARGV) == mf.POST_ACTIONS  # kept in sync with the manifest validator


class Trusted:
    """What the helper may touch, derived from the installed manifests."""

    def __init__(self):
        self.packages, self.services, self.flatpaks = set(), set(), set()
        self.dropins = {}            # path -> content
        self.essentials = set()      # packages of the essentials manifest: never removable


def _check_trusted_dir(path):
    st_ = os.stat(path)
    if st_.st_uid != 0 or st_.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise invalid("untrusted manifest directory %s (must be root-owned, not group/world-writable)" % path)
    for fn in os.listdir(path):
        s = os.lstat(os.path.join(path, fn))
        if s.st_uid != 0 or s.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or stat.S_ISLNK(s.st_mode):
            raise invalid("untrusted file %s in %s" % (fn, path))


def load_trusted(profiles_dir, hardware_dir, strict=True):
    if strict:
        _check_trusted_dir(profiles_dir)
        _check_trusted_dir(hardware_dir)
    t = Trusted()
    manifests = mf.load_dir(profiles_dir)
    for m in manifests.values():
        t.packages.update(m.packages)
        t.services.update(m.services)
        t.flatpaks.update(m.flatpaks)
        for d in m.dropins:
            t.dropins[d["path"]] = d["content"]
    if "essentials" in manifests:
        t.essentials = set(manifests["essentials"].packages)
    for p in hw.load_profiles(hardware_dir).values():
        t.packages.update(p.packages)
        t.services.update(p.services)
        for d in p.dropins:
            t.dropins[d["path"]] = d["content"]
    return t


def _names(value, what):
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        raise invalid("%s must be a list of strings" % what)
    if len(value) > MAX_ITEMS:
        raise invalid("too many %s (max %d)" % (what, MAX_ITEMS))
    if len(set(value)) != len(value):
        raise invalid("duplicate %s" % what)
    return list(value)


def check_install(names, trusted):
    names = _names(names, "packages")
    if not names:
        raise invalid("no packages given")
    bad = [n for n in names if not mf.PKG_RE.fullmatch(n) or n not in trusted.packages]
    if bad:
        raise invalid("packages not allowed: %s" % ", ".join(sorted(bad)[:5]))
    return names


def check_remove(names, trusted, state_path):
    names = check_install(names, trusted)
    owned = set(st.load(state_path)["packages"])
    not_owned = [n for n in names if n not in owned]
    if not_owned:
        raise invalid("not installed by Heiss, refusing to remove: %s" % ", ".join(sorted(not_owned)[:5]))
    protected = [n for n in names if n in trusted.essentials]
    if protected:
        raise invalid("essential packages cannot be removed: %s" % ", ".join(sorted(protected)[:5]))
    return names


def check_services(enable, disable, trusted):
    enable, disable = _names(enable, "services to enable"), _names(disable, "services to disable")
    if not enable and not disable:
        raise invalid("no services given")
    if set(enable) & set(disable):
        raise invalid("a service cannot be enabled and disabled at once")
    bad = [s for s in enable + disable if not mf.UNIT_RE.fullmatch(s) or s not in trusted.services]
    if bad:
        raise invalid("services not allowed: %s" % ", ".join(sorted(bad)[:5]))
    return enable, disable


def check_dropin(path, trusted):
    if not isinstance(path, str) or path not in trusted.dropins or not mf.dropin_path_ok(path):
        raise invalid("drop-in not declared by any manifest")
    return path, trusted.dropins[path]


def check_post_action(action_id):
    if not isinstance(action_id, str) or action_id not in POST_ACTION_ARGV:
        raise invalid("unknown post action")
    return list(POST_ACTION_ARGV[action_id])


def write_dropin(path, content, root="/"):
    """Atomically write a drop-in below `root`; refuses symlinks and any directory not on the allowlist."""
    if not mf.dropin_path_ok(path):
        raise invalid("bad drop-in path")
    full = os.path.join(root, path.lstrip("/"))
    # no symlink on any component below root
    cur = root
    for part in path.strip("/").split("/"):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            raise invalid("symlink in drop-in path")
    if os.path.lexists(full) and not os.path.isfile(full):
        raise invalid("drop-in target is not a regular file")
    d = os.path.dirname(full)
    os.makedirs(d, mode=0o755, exist_ok=True)
    tmp = os.path.join(d, ".heiss-tmp-%d" % os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, full)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def remove_dropin(path, content, root="/"):
    """Delete a drop-in below `root` that a manifest declared, but only while it still has the declared content
    (a file the user changed is left alone). Returns a short message. Refuses symlinks like write_dropin."""
    if not mf.dropin_path_ok(path):
        raise invalid("bad drop-in path")
    cur = root
    for part in path.strip("/").split("/"):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            raise invalid("symlink in drop-in path")
    full = os.path.join(root, path.lstrip("/"))
    if not os.path.lexists(full):
        return "%s is already gone" % path
    if not os.path.isfile(full):
        raise invalid("drop-in target is not a regular file")
    try:
        fd = os.open(full, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as e:
        raise invalid("cannot open the drop-in: %s" % (e.strerror or e))
    with os.fdopen(fd, encoding="utf-8", errors="replace") as f:
        if f.read() != content:
            return "%s was changed by you, left in place" % path
    os.unlink(full)
    return "removed %s" % path
