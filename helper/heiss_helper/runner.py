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
DRAIN_S = 0.5      # after the command has exited, how long to keep reading what is left in the pipe


def _stop(p, grace):
    """End the command and everything it started in its process group: SIGTERM, wait for the leader (up to `grace`),
    then SIGKILL to the whole group, also when the leader already exited (a member may ignore SIGTERM).
    Never waits more than 2 x grace."""
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        p.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        p.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass


class Runner:
    grace = KILL_GRACE_S

    def run(self, argv, emit, timeout=3600):
        """Return the exit code, or 124 when `timeout` seconds passed. argv is a list built by this package, never
        from a client.

        The limit is checked by the loop that reads the output, with poll(), so it also ends a command that
        prints nothing and never exits (which would hold the helper's single job slot until a restart), and a
        grandchild that left the process group and keeps the pipe open cannot keep the reader waiting past the
        limit or past the exit of the command itself."""
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=ENV, start_new_session=True)
        fd = p.stdout.fileno()
        poller = select.poll()          # poll, not select: select() fails for descriptors >= 1024 in a long-running service
        poller.register(fd, select.POLLIN)
        deadline = float("inf") if timeout is None else time.monotonic() + timeout
        expired, finished, lines, pending = False, False, 0, b""

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

        def drain(seconds):
            """Take what is readable now, for at most `seconds` (a grandchild that keeps writing must not hold us)."""
            end = time.monotonic() + seconds
            while time.monotonic() < end and poller.poll(0):
                chunk = os.read(fd, CHUNK)
                if not chunk:
                    return
                deliver(chunk)

        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    expired = True
                    break
                ready = poller.poll(min(left, POLL_S) * 1000)
                if ready:
                    chunk = os.read(fd, CHUNK)
                    if not chunk:
                        break                      # end of output (the command may still be working)
                    deliver(chunk)
                if p.poll() is not None:
                    drain(DRAIN_S)                 # the command is gone; something else may still hold the pipe open
                    break
            deliver(b"", final=True)
            finished = True
        finally:
            try:
                if expired or not finished:        # timed out, or the reader failed (emit raised): do not leave it running
                    _stop(p, self.grace)
            finally:
                p.stdout.close()
        if expired:
            return 124
        try:                                       # output closed: the command may work on until the limit
            return p.wait(timeout=max(deadline - time.monotonic(), 0))
        except subprocess.TimeoutExpired:
            _stop(p, self.grace)
            return 124
