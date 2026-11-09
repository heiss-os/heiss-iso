"""Run fixed argument lists (never a shell) and stream their output."""
import subprocess

MAX_OUTPUT_LINES = 20000
ENV = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}


class Runner:
    def run(self, argv, emit, timeout=3600):
        """Return the exit code. argv is a list built by this package, never from a client."""
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=ENV, text=True, errors="replace")
        try:
            for n, line in enumerate(p.stdout):
                if n < MAX_OUTPUT_LINES:
                    emit(line.rstrip("\n"))
            return p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            return 124
