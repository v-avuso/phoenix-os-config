import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).parents[1] / "nct6687-watchdog.py")
watchdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watchdog)


class FallbackTests(unittest.TestCase):
    def run_fallback(self, modes):
        class FakePath:
            def __truediv__(self, name):
                return File(name)

        class File:
            def __init__(self, name):
                self.name = name
            def is_file(self):
                return True
            def write_text(self, *args, **kwargs):
                pass

        clock = [0.0]
        def read(file):
            if file.name == "fan_control_watchdog":
                return "1" if clock[0] == 0 else "0"
            return modes(clock[0], file.name)
        def sleep(seconds):
            clock[0] += seconds
        with patch.object(watchdog, "read", side_effect=read), \
             patch.object(watchdog.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(watchdog.time, "sleep", side_effect=sleep):
            watchdog.expire_lease(FakePath())

    def test_cached_manual_mode_eventually_refreshes(self):
        self.run_fallback(lambda now, name: "1" if now < 1.0 else "2")

    def test_persistent_manual_mode_fails_closed(self):
        with self.assertRaisesRegex(watchdog.NotReady, "fan1"):
            self.run_fallback(lambda now, name: "1")


if __name__ == "__main__":
    unittest.main()
