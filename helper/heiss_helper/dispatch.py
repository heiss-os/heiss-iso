"""Transport-independent core of the service: authorize -> validate -> run one job.

The D-Bus glue (service.py) only translates; everything security-relevant is here
and is tested without a bus.
"""
import secrets
import threading
import time

from .actions import ACTIONS, Context, execute
from .audit import Audit, clean
from .errors import HelperError


MAX_PENDING = 8   # concurrent requests waiting for polkit or validation


class Dispatcher:
    def __init__(self, authorizer, emit, ctx=None, audit=None):
        """emit(sender, signal_name, args_tuple) delivers a signal to that caller only."""
        self.authorizer, self.emit = authorizer, emit
        self.ctx = ctx or Context()
        self.audit = audit or Audit()
        self._busy = threading.Lock()
        self.last_activity = time.monotonic()
        self._threads = []
        self._admission = threading.BoundedSemaphore(MAX_PENDING)

    def admit(self):
        """Cheap gate for the transport: False when too many requests are already waiting."""
        return self._admission.acquire(blocking=False)

    def leave(self):
        self._admission.release()

    def idle_for(self):
        return 0.0 if self._busy.locked() else time.monotonic() - self.last_activity

    def handle(self, sender, uid, method, args):
        """Return a job id or raise HelperError. May block on polkit: call from a worker thread."""
        self.last_activity = time.monotonic()
        action = ACTIONS.get(method)
        if action is None:
            raise HelperError("Invalid", "unknown method")
        summary = "args=%s" % clean(args, 200)
        try:
            if not self.authorizer.is_authorized(sender, action.polkit):
                raise HelperError("NotAuthorized", "not authorized (%s)" % action.polkit)
            steps = action.build(self.ctx, *args)      # validation after authorization: no allowlist oracle
            if not self._busy.acquire(blocking=False):
                raise HelperError("Busy", "another job is running")
        except HelperError as e:
            self.audit.record(uid, method, summary, "refused:%s" % e.code)
            raise
        except Exception as e:  # a bug must never surface as a crash or a half-validated request
            self.audit.record(uid, method, summary, "refused:internal %s" % type(e).__name__)
            raise HelperError("Failed", "internal error") from e
        job = secrets.token_hex(8)
        self.audit.record(uid, method, summary, "started job=%s" % job)
        t = threading.Thread(target=self._run_job, args=(sender, uid, method, job, steps), daemon=True)
        self._threads.append(t)
        t.start()
        return job

    def _run_job(self, sender, uid, method, job, steps):
        try:
            ok, message = execute(steps, self.ctx, lambda line: self.emit(sender, "JobOutput", (job, clean(line, 2000))))
        except Exception as e:  # never leave a job without a result
            ok, message = False, "internal error: %s" % type(e).__name__
        finally:
            self.last_activity = time.monotonic()
            self._busy.release()
        self.audit.record(uid, method, "job=%s" % job, "ok" if ok else "failed:%s" % clean(message, 100))
        self.emit(sender, "JobFinished", (job, ok, clean(message, 500)))

    def join(self, timeout=10):
        for t in list(self._threads):
            t.join(timeout)
