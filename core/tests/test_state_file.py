"""File modes of what heiss-core writes: the root-written state file is readable by ordinary users, user files are private."""
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from heiss_core import state as st  # noqa: E402
from heiss_core import wizard as wz  # noqa: E402


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class Umask:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.old = os.umask(self.value)

    def __exit__(self, *a):
        os.umask(self.old)


class StateFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = os.path.join(self.tmp.name, "lib", "heiss")
        self.path = os.path.join(self.dir, "state.json")

    def test_state_file_is_world_readable_and_only_the_owner_can_write_whatever_the_umask(self):
        for umask in (0o077, 0o022, 0o000):
            os.makedirs(self.dir, exist_ok=True)
            with Umask(umask):
                st.save(self.path, dict(st.EMPTY, packages=["a", "b"]))
            self.assertEqual(mode(self.path), 0o644, oct(umask))
            self.assertEqual(st.load(self.path)["packages"], ["a", "b"])

    def test_a_new_state_directory_is_readable_and_traversable_under_a_strict_umask(self):
        with Umask(0o077):
            st.save(self.path, dict(st.EMPTY))
        self.assertEqual(mode(self.dir), 0o755)

    def test_an_existing_directory_keeps_its_mode(self):
        os.makedirs(self.dir, mode=0o750)
        os.chmod(self.dir, 0o750)
        st.save(self.path, dict(st.EMPTY))
        self.assertEqual(mode(self.dir), 0o750)

    def test_replacing_the_file_keeps_the_mode_and_leaves_no_temporary_file(self):
        st.save(self.path, dict(st.EMPTY))
        st.save(self.path, dict(st.EMPTY, packages=["x"]))
        self.assertEqual(mode(self.path), 0o644)
        self.assertEqual(os.listdir(self.dir), ["state.json"])

    def test_other_files_stay_private_by_default_even_with_a_loose_umask(self):
        os.makedirs(self.dir)
        p = os.path.join(self.dir, "wizard-state.json")
        with Umask(0o000):
            st.atomic_write(p, "{}")
        self.assertEqual(mode(p), 0o600)
        with Umask(0o000):
            wz.PendingQueue(os.path.join(self.dir, "pending.json")).add("apply-profile", {"profile": "base", "addons": []})
        self.assertEqual(mode(os.path.join(self.dir, "pending.json")), 0o600)

    def test_a_failed_write_leaves_no_temporary_file(self):
        os.makedirs(self.dir)
        with self.assertRaises(TypeError):
            st.atomic_write(self.path, 123)    # not a string: the write fails
        self.assertEqual(os.listdir(self.dir), [])


if __name__ == "__main__":
    unittest.main()
