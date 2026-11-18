"""Fixed-argument helpers of the settings window: run a short read-only command, start a program, read the screens.

No shell, no privileges. A program is started by name from a fixed table (`PROGRAMS`), never from user input.
"""
import json
import math
import shutil
import subprocess

MAX_OUTPUT = 65536
PROGRAMS = {"network": "nm-connection-editor", "bluetooth": "blueman-manager", "audio": "pavucontrol"}


def run(argv, timeout=10, run_=subprocess.run):
    """(returncode, output) of a short command; (127, message) when it cannot run."""
    try:
        r = run_(argv, capture_output=True, text=True, errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return 127, "%s: %s" % (argv[0], e)
    return r.returncode, ((r.stdout or "") + (r.stderr if r.returncode else ""))[:MAX_OUTPUT]


def launch(key, which=shutil.which, popen=subprocess.Popen):
    """Start the program of `key` detached. (ok, name-or-message)."""
    name = PROGRAMS.get(key)
    if name is None:
        return False, key
    if not which(name):
        return False, name
    try:
        popen([name], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except (OSError, ValueError) as e:
        return False, "%s: %s" % (name, e)
    return True, name


def monitors(run_cmd=run):
    """[{name, width, height, refresh, scale}] from `hyprctl monitors -j`; raises RuntimeError when it is not available."""
    rc, out = run_cmd(["hyprctl", "monitors", "-j"])
    if rc != 0:
        raise RuntimeError("hyprctl monitors failed")
    try:
        data = json.loads(out)
    except (ValueError, RecursionError) as e:
        raise RuntimeError("hyprctl monitors printed no JSON") from e
    rows = []
    for m in data if isinstance(data, list) else []:
        if not isinstance(m, dict):
            continue
        try:
            row = {"name": str(m.get("name", ""))[:40], "width": int(m["width"]), "height": int(m["height"]),
                   "refresh": round(float(m.get("refreshRate", 0)), 1), "scale": float(m.get("scale", 1))}
            if not all(math.isfinite(row[k]) for k in ("refresh", "scale")):
                continue
            rows.append(row)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return rows[:16]


XKB_LIST = "/usr/share/X11/xkb/rules/base.lst"


def known_layouts(path=XKB_LIST):
    """The keyboard layout names xkeyboard-config knows (the `! layout` section of base.lst); empty when unreadable."""
    names, inside = set(), False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("!"):
                    inside = line.split()[1:2] == ["layout"]
                elif inside and line.strip():
                    names.add(line.split()[0])
    except OSError:
        return set()
    return names
