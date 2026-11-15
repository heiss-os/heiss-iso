"""Run fixed argument lists (never a shell) and stream their output."""
import os
import signal
import subprocess
import threading

MAX_OUTPUT_LINES = 20000
ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
KILL_GRACE_S = 10   # SIGTERM first (pacman then releases its database lock), SIGKILL when it did not stop


def _stop(p, grace):
    """End the command and everything it started (it runs in its own process group)."""
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, None)):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            return
        try:
            p.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


class Runner:
    grace = KILL_GRACE_S

    def run(self, argv, emit, timeout=3600):
        """Return the exit code, or 124 when `timeout` seconds passed. argv is a list built by this package, never
        from a client. The limit is a watchdog: it also ends a command that prints nothing and never exits, which
        would otherwise hold the helper's single job slot until the helper is restarted."""
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=ENV, text=True, errors="replace", start_new_session=True)
        expired = threading.Event()

        def on_timeout():
            expired.set()
            _stop(p, self.grace)

        watchdog = threading.Timer(timeout, on_timeout)
        watchdog.daemon = True
        watchdog.start()
        try:
            for n, line in enumerate(p.stdout):
                if n < MAX_OUTPUT_LINES:
                    emit(line.rstrip("\n"))
            rc = p.wait()
        finally:
            watchdog.cancel()
            if p.poll() is None:      # the reader failed (emit raised) or the pipe closed early: do not leave it running
                _stop(p, self.grace)
            p.stdout.close()
        return 124 if expired.is_set() else rc
