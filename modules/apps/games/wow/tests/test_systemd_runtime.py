"""Opt-in isolated user-unit checks: PHOENIX_WOW_SYSTEMD_TEST=1 python -m unittest discover -s modules/apps/games/wow/tests -v.

Requires access to the user manager. Creates only uniquely named disposable units;
never starts the real updater or emits desktop notifications.
"""
import datetime
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import unittest
import uuid

HELPER = Path(__file__).resolve().parents[1] / "scheduled-update.sh"


@unittest.skipUnless(os.environ.get("PHOENIX_WOW_SYSTEMD_TEST") == "1", "opt-in native user-manager fixture")
class SystemdRuntimeTests(unittest.TestCase):
    def test_terminal_notification_and_persistent_catchup(self):
        prefix = "phoenix-wow-fixture-" + uuid.uuid4().hex
        names = [prefix + suffix for suffix in ("-failure.service", "-notify.service", "-catchup.service", "-catchup.timer")]
        runtime_units = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "systemd/user"

        def ctl(*args, check=True):
            return subprocess.run(["systemctl", "--user", *args], check=check, capture_output=True, text=True)

        with tempfile.TemporaryDirectory(prefix=prefix + "-") as directory:
            root = Path(directory)
            marker = root / "notification"
            attempts = root / "attempts"
            catchup = root / "catchup"
            runner = root / "failure.sh"
            runner.write_text("set -euo pipefail\n"
                              "pgrep() { return 1; }\n"
                              "sleep() { :; }\n"
                              f"wow_sync() {{ echo attempt >> {shlex.quote(str(attempts))}; return 23; }}\n"
                              f"source {shlex.quote(str(HELPER))}\n")
            shell = subprocess.check_output(["sh", "-c", "command -v bash"], text=True).strip()
            units = {
                names[0]: f"[Unit]\nOnFailure={names[1]}\n[Service]\nType=oneshot\nExecStart={shell} {runner}\n",
                names[1]: f"[Service]\nType=oneshot\nExecStart={shell} -c 'echo notification >> {marker}'\n",
                names[2]: f"[Service]\nType=oneshot\nExecStart={shell} -c 'echo catchup >> {catchup}'\n",
                # Prime persistent state, stop before the event, then reactivate
                # after it was missed. UTC avoids machine zoneinfo assumptions.
                names[3]: "[Timer]\nOnCalendar=" +
                          (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S UTC") +
                          f"\nPersistent=true\nAccuracySec=1us\nUnit={names[2]}\n",
            }
            try:
                for name, text in units.items():
                    path = root / name
                    path.write_text(text)
                    ctl("link", "--runtime", str(path))
                ctl("daemon-reload")
                for guard, failures, expected_attempts in ((1, 0, 1), (1, 1, 2), (0, 0, 0)):
                    runner.write_text(
                        "set -euo pipefail\n"
                        f"pgrep() {{ return {guard}; }}\n"
                        "sleep() { :; }\ninstawow() { return 0; }\n"
                        "wow_sync() { local count=0; "
                        f"if [[ -f {attempts} ]]; then count=$(wc -l < {attempts}); fi; "
                        f"echo attempt >> {attempts}; (( count >= {failures} )) || return 23; }}\n"
                        f"source {shlex.quote(str(HELPER))}\n"
                    )
                    ctl("start", names[0])
                    actual_attempts = len(attempts.read_text().splitlines()) if attempts.exists() else 0
                    self.assertEqual(actual_attempts, expected_attempts)
                    self.assertFalse(marker.exists(), "success, recovery and running-game skip must not notify")
                    attempts.unlink(missing_ok=True)
                runner.write_text("set -euo pipefail\n"
                                  "pgrep() { return 1; }\nsleep() { :; }\n"
                                  f"wow_sync() {{ echo attempt >> {shlex.quote(str(attempts))}; return 23; }}\n"
                                  f"source {shlex.quote(str(HELPER))}\n")
                result = ctl("start", names[0], check=False)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                deadline = time.monotonic() + 5
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(attempts.read_text().splitlines(), ["attempt"] * 4)
                self.assertEqual(marker.read_text().splitlines(), ["notification"])
                self.assertEqual(ctl("show", "-p", "ExecMainStatus", "--value", names[0]).stdout.strip(), "23")
                ctl("start", names[3])
                ctl("stop", names[3])
                time.sleep(6)
                self.assertFalse(catchup.exists(), "timer must be inactive across its calendar event")
                ctl("start", names[3])
                deadline = time.monotonic() + 5
                while not catchup.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertEqual(catchup.read_text().splitlines(), ["catchup"])
            finally:
                ctl("stop", *names, check=False)
                ctl("reset-failed", *names, check=False)
                ctl("clean", "--what=state", names[3], check=False)
                for name in names:
                    path = runtime_units / name
                    if path.is_symlink() and path.resolve().parent == root:
                        path.unlink()
                ctl("daemon-reload", check=False)


if __name__ == "__main__":
    unittest.main()
