"""Metadata-only history planning fixtures; never use personal Codex state."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
import sqlite3
import subprocess
import sys

source = Path(__file__).resolve().parents[1] / "modules/development/ai/agent/history-plan.py"
spec = importlib.util.spec_from_file_location("history_plan", source)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)
runtime_spec = importlib.util.spec_from_file_location("history_runtime", source.with_name("history-runtime.py"))
runtime = importlib.util.module_from_spec(runtime_spec)
runtime_spec.loader.exec_module(runtime)


class HistoryPlan(unittest.TestCase):
    def test_preserves_both_homes_without_reading_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native, sandbox = root / "native", root / "sandbox"
            for home in (native, sandbox):
                home.mkdir()
                (home / "sessions").mkdir()
                (home / "state_5.sqlite").write_bytes(b"not a database; must never be opened")
                (home / "state_5.sqlite-wal").write_bytes(b"keep WAL")
                (home / "auth.json").write_bytes(b"do not read credentials")
            before = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            result = history.plan(native, root / "shared", [sandbox])
            self.assertEqual(result["status"], "plan-only")
            self.assertEqual(result["sandbox_codex_home"], str(native))
            self.assertEqual(result["native"]["databases"], ["state_5.sqlite", "state_5.sqlite-wal"])
            self.assertEqual(len(result["retained_sandboxes"]), 1)
            self.assertNotIn("auth.json", str(result))
            self.assertFalse((root / "shared").exists())
            self.assertEqual(before, {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()})

    def test_rejects_aliases_and_profile_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "native"
            native.mkdir()
            (root / "alias").symlink_to(native)
            for bad in (root / "alias", native / ".." / "native"):
                with self.assertRaises(ValueError):
                    history.plan(bad, root / "shared", [])
            with self.assertRaises(ValueError):
                history.plan(native, native / "sqlite", [])
            (native / "sessions").symlink_to(root)
            with self.assertRaises(ValueError):
                history.plan(native, root / "shared", [])


class HistoryRuntime(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "native"
        self.home.mkdir()
        for name in runtime.DIRECTORIES:
            (self.home / name).mkdir()
        self.proc = self.root / "proc"
        self.proc.mkdir()
        self.config = {"nativeHome": str(self.home), "root": str(self.root / "shared"),
                       "transportHelper": str(source.with_name("launch.py"))}
        self.connection = sqlite3.connect(self.home / "state_5.sqlite")
        self.addCleanup(self.connection.close)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("CREATE TABLE fixture (value TEXT)")
        self.connection.execute("INSERT INTO fixture VALUES ('saved task')")
        self.connection.commit()
        (self.home / "auth.json").write_text("private credential sentinel")

    def test_dry_run_and_atomic_wal_backup_preserve_sources(self):
        before = {name: (self.home / name).read_bytes() for name in ("state_5.sqlite", "state_5.sqlite-wal", "auth.json")}
        self.assertEqual(runtime.status(self.config), {"active": False})
        self.assertEqual(runtime.enable(self.config, proc=self.proc)["status"], "cold-preflight-only")
        self.assertFalse(Path(self.config["root"]).exists())
        runtime.enable(self.config, apply=True, proc=self.proc)
        selected = runtime.status(self.config)
        self.assertTrue(selected["active"])
        with sqlite3.connect(Path(selected["sqliteHome"]) / "state_5.sqlite") as copied:
            self.assertEqual(copied.execute("SELECT value FROM fixture").fetchone(), ("saved task",))
        self.assertEqual(before, {name: (self.home / name).read_bytes() for name in before})
        self.assertFalse((Path(selected["sqliteHome"]) / "auth.json").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            runtime.enable(self.config, apply=True, proc=self.proc)
        (Path(self.config["root"]) / "ready.json").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.status(self.config)

    def test_backup_failure_never_publishes_or_changes_source(self):
        original = (self.home / "state_5.sqlite-wal").read_bytes()
        def failed(source, target):
            target.write_bytes(b"incomplete")
            raise RuntimeError("fixture failure")
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            runtime.enable(self.config, apply=True, proc=self.proc, backup=failed)
        self.assertFalse(Path(self.config["root"]).exists())
        self.assertFalse(Path(self.config["root"] + ".preparing").exists())
        self.assertEqual((self.home / "state_5.sqlite-wal").read_bytes(), original)

    def test_refuses_writers_unknown_database_and_config_override(self):
        process = self.proc / "42"
        process.mkdir()
        (process / "exe").symlink_to("/nix/store/fixture-codex/bin/codex")
        (process / "comm").write_text("codex")
        with self.assertRaisesRegex(ValueError, "exiting every"):
            runtime.enable(self.config, apply=True, proc=self.proc)
        (process / "exe").unlink()
        (process / "comm").unlink()
        process.rmdir()
        (self.home / "future_99.sqlite").write_bytes(b"future")
        with self.assertRaisesRegex(ValueError, "unknown Native"):
            runtime.enable(self.config, proc=self.proc)
        (self.home / "future_99.sqlite").unlink()
        (self.home / "config.toml").write_text('[profiles.custom]\nsqlite_home = "/other"\n')
        with self.assertRaisesRegex(ValueError, "override"):
            runtime.enable(self.config, proc=self.proc)

    def test_staging_and_missing_database_fail_closed(self):
        preparing = Path(self.config["root"] + ".preparing")
        preparing.mkdir()
        with self.assertRaisesRegex(ValueError, "in progress"):
            runtime.status(self.config)
        preparing.rmdir()
        runtime.enable(self.config, apply=True, proc=self.proc)
        (Path(self.config["root"]) / "sqlite/state_5.sqlite").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            runtime.status(self.config)

    def test_overrides_only_reject_configuration_flags(self):
        self.assertTrue(runtime.has_sqlite_override(["-c", "sqlite_home=/other"]))
        self.assertTrue(runtime.has_sqlite_override(["--config=sqlite_home=/other"]))
        self.assertFalse(runtime.has_sqlite_override(["explain sqlite_home settings"]))

    def test_native_exec_receives_shared_locations_only_after_readiness(self):
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(self.config))
        command = [sys.executable, "-I", str(source.with_name("history-runtime.py")), str(config_path), "--", sys.executable,
                   "-c", 'import os,json; print(json.dumps({key:os.environ.get(key) for key in ("CODEX_HOME","CODEX_SQLITE_HOME")}))']
        inactive = json.loads(subprocess.check_output(command, env={"PATH": "/bin"}))
        self.assertEqual(inactive, {"CODEX_HOME": None, "CODEX_SQLITE_HOME": None})
        runtime.enable(self.config, apply=True, proc=self.proc)
        active = json.loads(subprocess.check_output(command, env={"PATH": "/bin"}))
        self.assertEqual(active, {"CODEX_HOME": str(self.home), "CODEX_SQLITE_HOME": str(Path(self.config["root"]) / "sqlite")})

    def test_lifecycle_lock_survives_native_exec_and_blocks_startup_during_prepare(self):
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(self.config))
        runtime_path = str(source.with_name("history-runtime.py"))
        command = [sys.executable, "-I", runtime_path, str(config_path), "--", sys.executable, "-c",
                   # Deliberately discard inherited FDs, as a runtime can.
                   'import os,sys; os.closerange(3,256); print("ready",flush=True); sys.stdin.readline()']
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            with self.assertRaisesRegex(ValueError, "lifecycle is busy"):
                runtime.enable(self.config, apply=True, proc=self.proc)
        finally:
            child.communicate("done\n", timeout=5)
        holder_script = ('import importlib.util,json,sys; '
                         'spec=importlib.util.spec_from_file_location("r",sys.argv[1]); '
                         'r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r); '
                         'fd=r.lifecycle_lock(json.load(open(sys.argv[2]))); '
                         'print("ready",flush=True); sys.stdin.readline()')
        holder = subprocess.Popen([sys.executable, "-c", holder_script, runtime_path, str(config_path)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "ready")
            blocked = subprocess.run(command, input="done\n", capture_output=True, text=True)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("lifecycle is busy", blocked.stderr)
            self.assertNotIn("ready", blocked.stdout)
        finally:
            holder.communicate("done\n", timeout=5)

    def test_cold_staging_recovery_restores_original_mode_only(self):
        staging = Path(self.config["root"] + ".preparing")
        staging.mkdir(mode=0o700)
        (staging / "sqlite").mkdir(mode=0o700)
        (staging / "sqlite/state_5.sqlite").write_bytes(b"unpublished")
        before = (self.home / "state_5.sqlite-wal").read_bytes()
        self.assertEqual(runtime.recover_staging(self.config, proc=self.proc)["status"], "unpublished-staging-removed")
        self.assertEqual(runtime.status(self.config), {"active": False})
        self.assertEqual((self.home / "state_5.sqlite-wal").read_bytes(), before)
        staging.mkdir(mode=0o700)
        (staging / "sqlite").mkdir(mode=0o700)
        (staging / "sqlite/state_5.sqlite").symlink_to(self.home / "state_5.sqlite")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            runtime.recover_staging(self.config, proc=self.proc)
        self.assertTrue(staging.exists())

    def test_unrelated_process_does_not_require_executable_access(self):
        process = self.proc / "99"
        process.mkdir()
        (process / "comm").write_text("chrome")
        # No exe/cmdline access is needed to dismiss this unrelated process.
        runtime.reject_writers(self.proc)
        (process / "comm").write_text("codex")
        with self.assertRaisesRegex(ValueError, "exiting every"):
            runtime.reject_writers(self.proc)


if __name__ == "__main__":
    unittest.main()
