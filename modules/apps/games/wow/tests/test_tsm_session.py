"""Exercise the watcher with a real owned child and deterministic process snapshots."""
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
            app = root / "tsm-app"
            app.write_text('''#!/usr/bin/env python3
import os, signal, time
from pathlib import Path
root = Path(os.environ['XDG_RUNTIME_DIR'])
def stop(*_):
    (root / 'stopped').write_text('TERM:' + (root / 'tick').read_text())
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
(root / 'started').write_text(os.environ['PHOENIX_TSM_START_MINIMIZED'])
while True:
    time.sleep(.01)
''')
            app.chmod(0o755)
            # Snapshots model every poll: w=WoW, b=Battle.net, -=neither,
            # e=process-query error. The final snapshot repeats until timeout.
            harness = '''set -euo pipefail
i=0
pgrep() {
  while [[ ! -e "$XDG_RUNTIME_DIR/started" ]]; do command sleep .01; done
  state=${SNAPSHOTS:i:1}
  [[ -n "$state" ]] || state=${SNAPSHOTS: -1}
  [[ "$state" != e ]] || return 2
  if [[ "${*: -1}" == Battle* ]]; then [[ "$state" == b ]];
  else [[ "$state" == w ]]; fi
}
sleep() { i=$((i + 1)); printf '%s' "$i" > "$XDG_RUNTIME_DIR/tick"; }
printf 0 > "$XDG_RUNTIME_DIR/tick"
source "$1"
'''
            lock = None
            if locked:
                import fcntl
                lock = (root / "phoenix-tsm.lock").open("w")
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                result = subprocess.run(
                    ["bash", "-c", harness, "fixture", str(HELPER)],
                    env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                         "XDG_RUNTIME_DIR": directory, "SNAPSHOTS": snapshots},
                    capture_output=True, text=True, timeout=10,
                )
                return result, {p.name: p.read_text() for p in root.iterdir()
                                if p.name in ("started", "stopped")}
            finally:
                if lock:
                    lock.close()

    def test_game_outlives_launcher_and_receives_cleanup(self):
        result, events = self.run_session("bbwww-")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, {"started": "1", "stopped": "TERM:5"})

    def test_cancelled_launcher_does_not_leave_companion(self):
        result, events = self.run_session("bb-")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events.get("stopped"), "TERM:31")

    def test_no_launcher_start_times_out(self):
        result, events = self.run_session("-")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events.get("stopped"), "TERM:59")

    def test_manual_instance_lock_is_preserved(self):
        result, events = self.run_session("w-", locked=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, {})

    def test_query_failure_stops_owned_companion(self):
        result, events = self.run_session("e")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(events.get("stopped"), "TERM:0")


if __name__ == "__main__":
    unittest.main()
