"""Run fixed argument lists (never a shell) and stream their output."""
import os
import select
import signal
import subprocess
import time

MAX_OUTPUT_LINES = 20000
ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
KILL_GRACE_S = 10   # SIGTERM first (pacman then releases its database lock), SIGKILL when it did not stop
POLL_S = 0.5        # how often the reader looks at the clock and at the command while it is silent
CHUNK = 65536


def _stop(p, grace):
    """End the command and everything it started in its process group. Never waits more than 2 x grace."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            break
        try:
            p.wait(timeout=grace)
            break
        except subprocess.TimeoutExpired:
            continue


class Runner:
    grace = KILL_GRACE_S

    def run(self, argv, emit, timeout=3600):
        """Return the exit code, or 124 when `timeout` seconds passed. argv is a list built by this package, never
        from a client.

        The limit is checked by the loop that reads the output, with select(), so it also ends a command that
        prints nothing and never exits (which would hold the helper's single job slot until a restart), and a
        grandchild that left the process group and keeps the pipe open cannot keep the reader waiting past the
        limit or past the exit of the command itself."""
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=ENV, start_new_session=True)
        fd = p.stdout.fileno()
        deadline = time.monotonic() + timeout
        expired, lines, pending = False, 0, b""

        def deliver(data, final=False):
            nonlocal lines, pending
            pending += data
            parts = pending.split(b"\n")
            pending = b"" if final else parts.pop()
            if final and parts and parts[-1] == b"":
                parts.pop()
            for part in parts:
                lines += 1
                if lines <= MAX_OUTPUT_LINES:
                    emit(part.decode("utf-8", "replace").rstrip("\r"))

        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    expired = True
                    break
                ready, _, _ = select.select([fd], [], [], min(left, POLL_S))
                if ready:
                    chunk = os.read(fd, CHUNK)
                    if not chunk:
                        break                      # end of output
                    deliver(chunk)
                elif p.poll() is not None:
                    # the command is gone but something else holds the pipe open: take what is there and stop
                    while select.select([fd], [], [], 0)[0]:
                        chunk = os.read(fd, CHUNK)
                        if not chunk:
                            break
                        deliver(chunk)
                    break
            deliver(b"", final=True)
        finally:
            if expired or p.poll() is None:        # timed out, or the reader failed (emit raised): do not leave it running
                _stop(p, self.grace)
            p.stdout.close()
        if expired:
            return 124
        try:
            return p.wait(timeout=self.grace)
        except subprocess.TimeoutExpired:          # closed its output but does not exit
            _stop(p, self.grace)
            return 124
