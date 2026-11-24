"""Exercise the game lifetime independently of the original app process."""
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "tsm-session.sh"


class TsmSessionTests(unittest.TestCase):
    def run_session(self, snapshots, locked=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # The initial launcher exits as it would when handing off an update.
            app = root / "tsm-app"
            app.write_text('#!/usr/bin/env bash\ntouch "$XDG_RUNTIME_DIR/launched"\n')
            app.chmod(0o755)
            harness = '''
set -euo pipefail
i=0
pgrep() {
  state=${SNAPSHOTS:i:1}
  [[ -n "$state" ]] || state=${SNAPSHOTS: -1}
  [[ "$state" != e ]] || return 2
  if [[ "${*: -1}" == Battle* ]]; then [[ "$state" == b ]]
  else [[ "$state" == w ]]; fi
}
sleep() { wait; i=$((i + 1)); }
trap 'wait || true; printf "%s" "$i" > "$XDG_RUNTIME_DIR/tick"' EXIT
source "$1"
'''
            with (root / "phoenix-tsm.lock").open("w") as lock:
                if locked:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = subprocess.run(
                    ["bash", "-c", harness, "fixture", str(HELPER)],
                    env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                         "XDG_RUNTIME_DIR": directory, "SNAPSHOTS": snapshots},
                    capture_output=True, text=True, timeout=10,
                )
            return result.returncode, (root / "tick").read_text(), (root / "launched").exists()

    def test_game_lifetime_survives_initial_app_exit(self):
        self.assertEqual(self.run_session("bbwww-"), (0, "5", True))

    def test_cancelled_launcher_times_out(self):
        self.assertEqual(self.run_session("bb-"), (0, "31", True))

    def test_no_launcher_start_times_out(self):
        self.assertEqual(self.run_session("-"), (0, "59", True))

    def test_manual_instance_lock_is_preserved(self):
        self.assertEqual(self.run_session("w-", locked=True), (0, "0", False))

    def test_process_query_error_ends_session(self):
        self.assertEqual(self.run_session("e"), (2, "0", True))


if __name__ == "__main__":
    unittest.main()
