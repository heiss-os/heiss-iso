"""Audit trail: journald (identifier "heiss") plus a readable log. No secrets, no file contents."""
import os
import re
import syslog
import time

_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean(text, limit=300):
    return _CTRL.sub("?", str(text))[:limit]


class Audit:
    def __init__(self, path="/var/log/heiss/audit.log"):
        self.path = path
        syslog.openlog("heiss", syslog.LOG_PID, syslog.LOG_DAEMON)

    def record(self, uid, action, summary, result):
        line = "%s uid=%s action=%s %s result=%s" % (
            time.strftime("%Y-%m-%dT%H:%M:%S%z"), clean(uid, 12), clean(action, 40), clean(summary), clean(result, 200))
        syslog.syslog(syslog.LOG_NOTICE, line)
        try:
            os.makedirs(os.path.dirname(self.path), mode=0o750, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o640)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass  # journald still has it
