"""The helper's command runner against real (harmless) processes: output, exit codes, the time limit."""
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "core"))
from heiss_helper import runner  # noqa: E402


def alive(pid):
    """Running, not just present: where PID 1 does not reap orphans (a container) a killed process stays a zombie."""
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.r = runner.Runner()
        self.r.grace = 0.5          # the SIGKILL fallback must not make the tests slow
        self.lines = []

    def run_cmd(self, *argv, timeout=30):
        t = time.monotonic()
        rc = self.r.run(list(argv), self.lines.append, timeout=timeout)
        return rc, time.monotonic() - t

    def test_output_and_exit_code_are_passed_through(self):
        self.assertEqual(self.run_cmd("sh", "-c", "echo one; echo two >&2; exit 3")[0], 3)
        self.assertEqual(sorted(self.lines), ["one", "two"])

    def test_a_silent_command_that_never_exits_is_ended_at_the_limit(self):
        rc, took = self.run_cmd("sleep", "60", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 5)

    def test_a_command_that_keeps_printing_is_ended_at_the_limit(self):
        rc, took = self.run_cmd("sh", "-c", "while true; do echo x; sleep 0.2; done", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 5)

    def test_a_child_that_holds_the_pipe_does_not_keep_the_runner_waiting(self):
        # the shell exits at once but its background child keeps stdout open: the whole group must go
        rc, took = self.run_cmd("sh", "-c", "sleep 60 & wait", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 5)

    def test_a_grandchild_in_another_session_cannot_keep_the_runner_waiting(self):
        # setsid puts the sleeper out of the command's process group: the group kill cannot reach it and it holds the pipe
        rc, took = self.run_cmd("sh", "-c", "setsid sleep 8 & exit 0", timeout=30)
        self.assertEqual(rc, 0)
        self.assertLess(took, 5)       # returned when the command exited, not at the 30 s limit
        rc, took = self.run_cmd("sh", "-c", "setsid sleep 8 & sleep 60", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 5)

    def test_binary_and_split_output_is_decoded_and_split_into_lines(self):
        rc, _ = self.run_cmd("sh", "-c", "printf 'a\\377b\\nlast without newline'")
        self.assertEqual(rc, 0)
        self.assertEqual(self.lines, ["a\ufffdb", "last without newline"])

    def test_a_command_that_closes_its_output_but_keeps_working_is_waited_for(self):
        rc, took = self.run_cmd("sh", "-c", "echo start; exec >&- 2>&-; sleep 0.7; exit 3", timeout=20)
        self.assertEqual(rc, 3)           # its own exit code, not a signal from the runner
        self.assertGreaterEqual(took, 0.6)
        self.assertEqual(self.lines, ["start"])

    def test_a_command_that_closes_its_output_and_never_exits_is_ended_at_the_limit(self):
        rc, took = self.run_cmd("sh", "-c", "exec >&- 2>&-; sleep 60", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 5)

    def test_a_chatty_grandchild_does_not_keep_the_runner_after_the_command_exited(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pidfile = os.path.join(tmp.name, "pid")

        def reap():
            try:
                with open(pidfile) as f:
                    os.killpg(int(f.read()), 9)    # the grandchild leads its own session and group
            except (OSError, ValueError):
                pass
        self.addCleanup(reap)
        script = "setsid sh -c 'echo $$ > %s; while true; do echo spam; sleep 0.05; done' & exit 0" % pidfile
        rc, took = self.run_cmd("sh", "-c", script, timeout=30)
        self.assertEqual(rc, 0)
        self.assertLess(took, 5)

    def test_no_time_limit_is_accepted(self):
        self.assertEqual(self.r.run(["true"], self.lines.append, timeout=None), 0)

    def test_a_group_member_that_ignores_sigterm_is_killed_even_when_the_leader_dies_on_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pidfile = os.path.join(tmp.name, "pid")
        # the shell dies on SIGTERM, its child ignores it and holds on
        script = "sh -c 'trap \"\" TERM; echo $$ > %s; sleep 60' & wait" % pidfile
        rc, took = self.run_cmd("sh", "-c", script, timeout=1)
        self.assertEqual(rc, 124)
        with open(pidfile) as f:
            pid = int(f.read())
        time.sleep(0.5)
        self.assertFalse(alive(pid), "the SIGTERM-ignoring member must have been killed with the group")

    def test_a_descriptor_above_1024_does_not_break_the_reader(self):
        spare = [os.open("/dev/null", os.O_RDONLY) for _ in range(1100)]
        try:
            rc, _ = self.run_cmd("sh", "-c", "echo hi")
        finally:
            for f in spare:
                os.close(f)
        self.assertEqual((rc, self.lines), (0, ["hi"]))

    def test_a_command_that_ignores_sigterm_is_killed(self):
        rc, took = self.run_cmd("sh", "-c", "trap '' TERM; while true; do sleep 0.2; done", timeout=1)
        self.assertEqual(rc, 124)
        self.assertLess(took, 6)

    def test_a_fast_command_is_not_hurt_by_the_watchdog(self):
        rc, took = self.run_cmd("true", timeout=30)
        self.assertEqual(rc, 0)
        self.assertLess(took, 5)
        time.sleep(0.1)
        self.assertEqual(self.run_cmd("sh", "-c", "exit 0", timeout=30)[0], 0)

    def test_output_beyond_the_cap_is_dropped_but_the_command_finishes(self):
        rc, _ = self.run_cmd("sh", "-c", "i=0; while [ $i -lt %d ]; do echo $i; i=$((i+1)); done" % (runner.MAX_OUTPUT_LINES + 50))
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.lines), runner.MAX_OUTPUT_LINES)

    def test_a_failing_emit_does_not_leave_the_command_running(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pidfile = os.path.join(tmp.name, "pid")

        def boom(line):
            raise RuntimeError("reader failed")
        with self.assertRaises(RuntimeError):
            self.r.run(["sh", "-c", "echo $$ > %s; echo hello; exec sleep 60" % pidfile], boom, timeout=30)
        with open(pidfile) as f:
            pid = int(f.read())
        time.sleep(0.3)
        self.assertFalse(alive(pid), "the command must have been stopped")


if __name__ == "__main__":
    unittest.main()
