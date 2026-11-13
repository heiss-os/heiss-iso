"""The two things the Advanced page can start. Fixed argument lists only, no shell, no helper, no privileges.

`run_check` is `heiss check` run in this process (read-only; every command it runs is listed in `heiss check
--report`). `open_settings` starts the stock KDE System Settings detached from this window.
"""
import os
import subprocess

from heiss_core import check as ck
from heiss_core import themesync

STATUSES = (ck.OK, ck.WARN, ck.FAIL)


def run_check():
    env = ck.CheckEnv()
    items = ck.run_checks(env, themesync.RealEnv(), os.environ.get("HEISS_PROFILES", ck.PROFILES_DIR))
    return [i.to_dict() for i in items]


def open_settings(popen=subprocess.Popen):
    """Return (ok, message); message is empty on success."""
    try:
        popen(["systemsettings"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              start_new_session=True)
    except (OSError, ValueError) as e:
        return False, "cannot start System Settings: %s" % e
    return True, ""
