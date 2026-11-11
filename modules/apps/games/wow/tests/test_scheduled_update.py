"""Deterministic boundary tests; no network, add-on writes, or real sleeps."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scheduled-update.sh"


class ScheduledUpdateTests(unittest.TestCase):
    def run_update(self, sync_failures=0, update_failures=0, guards="1", native_guard=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Executable stubs preserve exit status and externally visible call order.
            for name, body in {
                "pgrep": '''i=$(cat "$TEST_ROOT/guard-index" 2>/dev/null || echo 0)
read -ra statuses <<< "$GUARDS"
status=${statuses[$i]:-${statuses[-1]}}
echo $((i+1)) > "$TEST_ROOT/guard-index"
exit "$status"''',
                "sleep": 'echo "sleep:$1" >> "$TEST_ROOT/events"',
                "instawow": '''echo "update:$3" >> "$TEST_ROOT/events"
i=$(cat "$TEST_ROOT/update-index" 2>/dev/null || echo 0)
echo $((i+1)) > "$TEST_ROOT/update-index"
(( i >= UPDATE_FAILURES )) || exit 23''',
            }.items():
                if native_guard and name == "pgrep":
                    continue
                path = root / name
                path.write_text("#!/usr/bin/env bash\n" + body + "\n")
                path.chmod(0o755)
            script = '''set -euo pipefail
wow_sync() {
  echo sync >> "$TEST_ROOT/events"
  local i
  i=$(cat "$TEST_ROOT/sync-index" 2>/dev/null || echo 0)
  echo $((i+1)) > "$TEST_ROOT/sync-index"
  (( i >= SYNC_FAILURES )) || return 17
}
wow_sync_forever() { echo forever-sync >> "$TEST_ROOT/events"; }
wow_manifest=fixture
source "$1"
'''
            result = subprocess.run(
                ["bash", "-c", script, "test", str(HELPER)],
                env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                     "TEST_ROOT": str(root), "GUARDS": guards,
                     "SYNC_FAILURES": str(sync_failures), "UPDATE_FAILURES": str(update_failures)},
                capture_output=True, text=True,
            )
            events = (root / "events").read_text().splitlines() if (root / "events").exists() else []
            return result, events

    def test_success_stops_after_one_attempt(self):
        result, events = self.run_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, ["forever-sync", "update:phoenix-forever", "sync", "update:phoenix-retail"])

    def test_transient_sync_failure_retries_whole_sequence(self):
        result, events = self.run_update(sync_failures=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, ["forever-sync", "update:phoenix-forever", "sync", "sleep:60", "sync", "update:phoenix-retail"])

    def test_terminal_failure_preserves_status_and_bounds_batch_retries(self):
        result, events = self.run_update(update_failures=4)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(events, ["forever-sync", "update:phoenix-forever", "sleep:60", "forever-sync", "update:phoenix-forever", "sync", "update:phoenix-retail", "sleep:60", "sync", "update:phoenix-retail"])

    def test_one_client_failure_does_not_skip_the_other(self):
        result, events = self.run_update(update_failures=2)
        self.assertEqual(result.returncode, 23)
        self.assertIn("update:phoenix-retail", events)

    def test_running_game_skips_without_mutation(self):
        result, events = self.run_update(guards="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, [])

    def test_game_started_during_sync_skips_update(self):
        result, events = self.run_update(guards="1 0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, ["forever-sync"])

    def test_game_started_after_forever_update_skips_retail(self):
        result, events = self.run_update(guards="1 1 0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, ["forever-sync", "update:phoenix-forever"])

    def test_game_started_during_retry_delay_skips_next_attempt(self):
        result, events = self.run_update(update_failures=1, guards="1 1 0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events, ["forever-sync", "update:phoenix-forever", "sleep:60"])

    @unittest.skipUnless(sys.platform == "linux", "native Linux comm detection")
    def test_native_process_name_is_detected(self):
        for name in ("Wow.exe", "WoW-64.exe", "WowClassicT.exe"):
            with self.subTest(name=name):
                process = subprocess.Popen(
                    [sys.executable, "-c",
                     "import ctypes, sys, time; "
                     "assert ctypes.CDLL(None).prctl(15, sys.argv[1].encode(), 0, 0, 0) == 0; "
                     "print('ready', flush=True); time.sleep(30)", name],
                    stdout=subprocess.PIPE, text=True,
                )
                try:
                    self.assertEqual(process.stdout.readline().strip(), "ready")
                    result, events = self.run_update(native_guard=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(events, [])
                    self.assertIsNone(process.poll(), "updater must leave game process alive")
                finally:
                    process.terminate()
                    process.wait()
                    process.stdout.close()

    def test_process_detection_error_fails_closed(self):
        result, events = self.run_update(guards="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
