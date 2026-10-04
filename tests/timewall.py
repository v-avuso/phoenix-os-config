#!/usr/bin/env python3
"""Isolated Timewall/Caelestia adapter tests; all commands are mocked."""

from datetime import time
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time as wall_clock
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "home/timewall-helper.py"
MODULE_PATH = ROOT / "home/timewall.nix"
SPEC = importlib.util.spec_from_file_location("phoenix_timewall_helper", HELPER_PATH)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)

TIMEWALL = "/nix/store/timewall/bin/timewall"
CAELESTIA = "/nix/store/caelestia-cli/bin/caelestia"
FALLBACK = "/nix/store/phoenix-black.png"


class TimewallAdapter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.env_patch = patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp.cleanup()

    def runner(self, statuses):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            status = statuses.pop(0) if statuses else 0
            return SimpleNamespace(returncode=status)

        return calls, run

    def test_local_theme_boundaries_are_half_open(self):
        self.assertEqual(helper.theme_mode(time(6, 59)), "dark")
        self.assertEqual(helper.theme_mode(time(7, 0)), "light")
        self.assertEqual(helper.theme_mode(time(19, 59)), "light")
        self.assertEqual(helper.theme_mode(time(20, 0)), "dark")

    def test_external_wallpaper_path_is_one_argument_and_daemon_selects_now(self):
        image = self.root / "city image.heic"
        image.write_bytes(b"fixture only")
        calls, run = self.runner([0])
        self.assertEqual(helper.start_timewall(TIMEWALL, str(image), CAELESTIA, FALLBACK, run), 0)
        self.assertEqual(calls[0][0], [TIMEWALL, "set", "--daemon", str(image)])

    def test_service_uses_fresh_private_runtime_for_timewall_pid_state(self):
        module = MODULE_PATH.read_text()
        self.assertIn('RuntimeDirectory = "phoenix-timewall";', module)
        self.assertIn('RuntimeDirectoryMode = "0700";', module)
        self.assertIn('"TIMEWALL_RUNTIME_DIR=%t/phoenix-timewall"', module)

    def test_missing_directory_and_unreadable_assets_fall_back_once(self):
        calls, run = self.runner([0])
        self.assertEqual(helper.start_timewall(TIMEWALL, str(self.root / "missing.heic"), CAELESTIA, FALLBACK, run), 0)
        self.assertEqual(calls, [([CAELESTIA, "wallpaper", "-f", FALLBACK, "--no-smart"], unittest.mock.ANY)])

        calls, run = self.runner([0])
        self.assertEqual(helper.start_timewall(TIMEWALL, str(self.root), CAELESTIA, FALLBACK, run), 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][2:4], ["-f", FALLBACK])

        image = self.root / "unreadable.heic"
        image.write_bytes(b"fixture only")
        with patch.object(helper.os, "open", side_effect=PermissionError):
            self.assertFalse(helper.is_readable_regular_file(image))

        fifo = self.root / "not-a-wallpaper.fifo"
        os.mkfifo(fifo)
        started = wall_clock.monotonic()
        self.assertFalse(helper.is_readable_regular_file(fifo))
        self.assertLess(wall_clock.monotonic() - started, 1, "FIFO validation blocked")

    def test_timewall_nonzero_uses_fallback_without_restart(self):
        image = self.root / "malformed.heic"
        image.write_bytes(b"not a heic")
        calls, run = self.runner([2, 0])
        self.assertEqual(helper.start_timewall(TIMEWALL, str(image), CAELESTIA, FALLBACK, run), 0)
        self.assertEqual(calls[0][0], [TIMEWALL, "set", "--daemon", str(image)])
        self.assertEqual(calls[1][0], [CAELESTIA, "wallpaper", "-f", FALLBACK, "--no-smart"])

    def test_failed_backend_uses_black_and_keeps_frame_path_atomic(self):
        frame = self.root / "cache frame.heic"
        calls, run = self.runner([1, 0])
        self.assertEqual(helper.set_wallpaper(CAELESTIA, FALLBACK, str(frame), run), 0)
        self.assertEqual(calls[0][0], [CAELESTIA, "wallpaper", "-f", str(frame), "--no-smart"])
        self.assertEqual(calls[1][0], [CAELESTIA, "wallpaper", "-f", FALLBACK, "--no-smart"])

    def test_theme_command_preserves_current_scheme_name(self):
        for local_time, mode in ((time(7, 0), "light"), (time(20, 0), "dark")):
            calls, run = self.runner([0])
            self.assertEqual(helper.sync_theme(CAELESTIA, runner=run, local_time=local_time), 0)
            self.assertEqual(calls[0][0], [CAELESTIA, "scheme", "set", "-m", mode])

    def test_unsupported_light_mode_logs_without_forcing_palette(self):
        calls, run = self.runner([1])
        self.assertEqual(helper.sync_theme(CAELESTIA, runner=run, local_time=time(12, 0)), 1)
        self.assertEqual(calls[0][0], [CAELESTIA, "scheme", "set", "-m", "light"])

    def test_setter_and_theme_writes_share_one_exclusive_lock(self):
        active = 0
        maximum = 0
        guard = threading.Lock()

        def run(argv, **kwargs):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            wall_clock.sleep(0.05)
            with guard:
                active -= 1
            return SimpleNamespace(returncode=0)

        frame = self.root / "frame.heic"
        threads = [
            threading.Thread(target=helper.set_wallpaper, args=(CAELESTIA, FALLBACK, str(frame), run)),
            threading.Thread(target=helper.sync_theme, args=(CAELESTIA,), kwargs={"runner": run, "local_time": time(12, 0)}),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive(), "mocked adapter write hung")
        self.assertEqual(maximum, 1, "wallpaper and theme writes were not serialized")

    def test_preexisting_lock_symlink_is_rejected_without_touching_target(self):
        target = self.root / "unrelated"
        target.write_text("keep")
        (self.runtime / helper.LOCK_NAME).symlink_to(target)
        with self.assertRaises(OSError):
            with helper.wallpaper_theme_lock():
                self.fail("the helper followed a preexisting lock symlink")
        self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
