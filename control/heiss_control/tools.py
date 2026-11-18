"""What the System page runs: `heiss check` in this process (read-only; every command it runs is listed in
`heiss check --report`). No shell, no helper, no privileges."""
import os

from heiss_core import check as ck
from heiss_core import theme

STATUSES = (ck.OK, ck.WARN, ck.FAIL)


def run_check():
    env = ck.CheckEnv()
    items = ck.run_checks(env, os.environ.get("HEISS_PROFILES", ck.PROFILES_DIR), home=os.path.expanduser("~"), theme_env=theme.RealEnv())
    return [i.to_dict() for i in items]
