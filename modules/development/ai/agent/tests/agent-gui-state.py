"""Shared GUI lifetime/readiness fixtures; synthetic state, no GUI/auth."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

MODULE = Path(__file__).resolve().parents[1]

class SharedGuiState(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "native"
        self.home.mkdir()
        self.shared = self.root / "history"
        self.shared.mkdir()
        (self.shared / "sqlite").mkdir()
        (self.shared / "sqlite/state_5.sqlite").touch()
        for name in ("sessions", "archived_sessions", "thread-writer-locks"):
            (self.home / name).mkdir()
        self.ready = self.shared / "ready.json"
        self.ready.write_text(json.dumps({"schema": 1, "nativeHome": str(self.home),
            "sqliteHome": str(self.shared / "sqlite"), "databases": ["state_5.sqlite"]}))
        self.history = self.root / "history.json"
        self.history.write_text(json.dumps({"nativeHome": str(self.home), "root": str(self.shared)}))
        # Individual immutable-style scripts have no sibling-library assumption.
        self.script = self.root / "standalone.py"
        self.script.write_bytes((MODULE / "gui-state.py").read_bytes())
        self.config = self.root / "state.json"
        self.config.write_text(json.dumps({"historyModule": str(MODULE / "history-runtime.py"),
            "historyConfig": str(self.history), "transportModule": str(MODULE / "launch.py"), "lock": str(self.root / "gui.lock")}))

    def command(self, variant, program):
        return [sys.executable, "-I", str(self.script), str(self.config), variant, "--",
                sys.executable, "-c", program]

    def test_readiness_and_failure_cleanup(self):
        self.ready.unlink()
        denied = subprocess.run(self.command("native", 'print("started")'), capture_output=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertNotIn(b"started", denied.stdout)
        self.setUpReady()
        failed = subprocess.run(self.command("sandbox", 'raise SystemExit(7)'), capture_output=True)
        self.assertEqual(failed.returncode, 7)
        success = subprocess.run(self.command("native", 'print("started")'), capture_output=True)
        self.assertEqual(success.returncode, 0)
        self.assertIn(b"started", success.stdout)

    def setUpReady(self):
        self.ready.write_text(json.dumps({"schema": 1, "nativeHome": str(self.home),
            "sqliteHome": str(self.shared / "sqlite"), "databases": ["state_5.sqlite"]}))

    def test_cross_variant_same_variant_and_history_exclusion(self):
        first = subprocess.Popen(self.command("native",
            'import os,sys; os.closerange(3,256); print("ready",flush=True); sys.stdin.readline()'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(first.stdout.readline().strip(), b"ready")
            for variant in ("sandbox", "native"):
                blocked = subprocess.run(self.command(variant, 'print("started")'), capture_output=True)
                self.assertEqual(blocked.returncode, 3)
                self.assertIn(b"Native", blocked.stderr)
                self.assertIn(b"close", blocked.stderr)
                self.assertNotIn(b"started", blocked.stdout)
            spec = importlib.util.spec_from_file_location("history", MODULE / "history-runtime.py")
            history = importlib.util.module_from_spec(spec); spec.loader.exec_module(history)
            with self.assertRaisesRegex(ValueError, "busy"):
                history.lifecycle_lock(json.loads(self.history.read_text()))
        finally:
            first.communicate(b"done\n", timeout=5)
        after = subprocess.run(self.command("sandbox", 'print("started")'), capture_output=True)
        self.assertEqual(after.returncode, 0)

    def test_shared_metadata_atomic_replace_pins(self):
        metadata = self.home / ".codex-global-state.json"
        metadata.write_text(json.dumps({"pinned-project-ids": ["fixture-project"],
                                       "pinned-thread-ids": ["fixture-thread"]}))
        program = ('import json,os; from pathlib import Path; p=Path(' + repr(str(metadata)) + '); '
                   's=json.loads(p.read_text()); assert s["pinned-project-ids"]==["fixture-project"]; '
                   's["pinned-thread-ids"].append("second-thread"); '
                   't=p.with_suffix(".tmp"); t.write_text(json.dumps(s)); os.replace(t,p)')
        self.assertEqual(subprocess.run(self.command("sandbox", program)).returncode, 0)
        self.assertEqual(json.loads(metadata.read_text())["pinned-thread-ids"], ["fixture-thread", "second-thread"])

if __name__ == "__main__":
    unittest.main()
