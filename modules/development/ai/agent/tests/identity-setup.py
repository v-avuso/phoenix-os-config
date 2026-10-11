#!/usr/bin/env python3
"""Disposable setup checks; full setup mocks privilege/quiescence and ACL subprocesses."""
import errno
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid

spec = importlib.util.spec_from_file_location("identity_setup", Path(__file__).resolve().parents[1] / "identity-setup.py")
setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)


class OfflineSetup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root / "old"; self.state = self.root / "new"; self.workspace = self.root / "workspace"
        self.gateway = self.old / "openshell/gateway"
        self.gateway.mkdir(parents=True); self.state.mkdir(mode=0o700); self.workspace.mkdir()
        (self.gateway / "openshell.db").write_bytes(b"disposable provider db")
        (self.gateway / "credentials").mkdir()
        (self.gateway / "credentials/key-encryption-key.bin").write_bytes(b"disposable fixture key")
        (self.old / "account-id.json").write_text(json.dumps(str(uuid.uuid4())))
        native = self.root / "native"
        for name in ("sessions", "archived_sessions", "thread-writer-locks"):
            (native / name).mkdir(parents=True)
        history = self.old / "history"
        (history / "sqlite").mkdir(parents=True)
        (history / "sqlite/state_5.sqlite").write_bytes(b"fixture history")
        (history / "ready.json").write_text(json.dumps({"schema": 1, "nativeHome": str(native), "sqliteHome": str(history / "sqlite"), "databases": ["state_5.sqlite"]}))
        self.config = {"uid": os.getuid(), "gid": os.getgid(), "readyOwner": os.getuid(), "subordinateStart": 300000, "subordinateCount": 65536, "operatorUid": os.getuid(),
                       "operatorHome": "/unused-home", "nativeHome": str(native), "historyRoot": str(history), "historyRuntime": str(Path(__file__).resolve().parents[1] / "history-runtime.py"), "oldState": str(self.old), "state": str(self.state),
                       "workspaces": [str(self.workspace)], "historyDirectories": [],
                       "historyFiles": [str(self.old / "history.lock")], "setfacl": shutil.which("setfacl"), "cp": shutil.which("cp")}

    def execute(self, cp_failure=False):
        real_run = subprocess.run
        def controlled_run(command, **kwargs):
            if command[0] == self.config["cp"]:
                if cp_failure:
                    raise subprocess.CalledProcessError(1, command, stderr=b"synthetic-secret-copy-error")
                return real_run(command, **kwargs)
            return None
        with patch.object(setup.os, "geteuid", return_value=0), patch.object(setup, "quiescent"), patch.object(setup, "validate_allocations"), patch.object(setup.subprocess, "run", side_effect=controlled_run):
            setup.setup(self.config)

    def test_installed_range_collision_and_valid_case(self):
        from types import SimpleNamespace
        account = SimpleNamespace(pw_uid=self.config["uid"], pw_gid=self.config["gid"], pw_name="phoenix-agent")
        group = SimpleNamespace(gr_gid=self.config["gid"], gr_name="phoenix-agent")
        config = self.config | {"operatorUid": self.config["uid"] + 1}
        entries = [("phoenix-agent", 300000, 65536)]
        with patch.object(setup.pwd, "getpwnam", return_value=account), patch.object(setup.pwd, "getpwall", return_value=[account]), patch.object(setup.grp, "getgrnam", return_value=group), patch.object(setup.grp, "getgrall", return_value=[group]), patch.object(setup, "allocated_ranges", return_value=entries):
            setup.validate_allocations(config)
            entries.append(("operator", 300001, 65536))
            with self.assertRaises(ValueError): setup.validate_allocations(config)

    def test_offline_refusal(self):
        with self.assertRaises(ValueError): setup.quiescent(os.getuid())
        with patch.object(setup.os, "geteuid", return_value=0), patch.object(setup, "validate_allocations"):
            with self.assertRaises(ValueError): setup.setup(self.config)
        self.assertTrue(self.gateway.is_dir()); self.assertFalse((self.state / "identity-ready").exists())

    def test_inactive_history_refuses_before_rename(self):
        (self.old / "history/ready.json").unlink()
        with self.assertRaises(ValueError): self.execute()
        self.assertTrue(self.gateway.is_dir())
        self.assertFalse((self.state / "identity-ready").exists())

    def test_narrow_success_marker_and_auth_bytes(self):
        self.execute()
        self.assertFalse(self.gateway.exists())
        new = self.state / "openshell/gateway"
        self.assertEqual((new / "openshell.db").read_bytes(), b"disposable provider db")
        self.assertEqual((new / "credentials/key-encryption-key.bin").read_bytes(), b"disposable fixture key")
        self.assertTrue((self.state / "identity-ready").is_file())
        self.assertFalse((self.state / "tls").exists()) # fresh upstream generation is later

    def test_ready_type_owner_and_history(self):
        self.execute()
        setup.ready(self.config)
        with self.assertRaises(ValueError): setup.ready(self.config | {"readyOwner": os.getuid() + 1})
        marker = self.state / "identity-ready"
        marker.unlink(); marker.symlink_to(self.state / "account-id.json")
        with self.assertRaises(ValueError): setup.ready(self.config)

    def cross_filesystem(self):
        original = os.rename
        first = True
        def rename(*args, **kwargs):
            nonlocal first
            if first:
                first = False
                raise OSError(errno.EXDEV, "different filesystem")
            return original(*args, **kwargs)
        return patch.object(setup.os, "rename", side_effect=rename)

    def test_exdev_verified_copy_keeps_source(self):
        with self.cross_filesystem(): self.execute()
        self.assertTrue(self.gateway.is_dir())
        target = self.state / "openshell/gateway"
        self.assertEqual((target / "credentials/key-encryption-key.bin").read_bytes(), b"disposable fixture key")
        self.assertEqual((target / "openshell.db").read_bytes(), (self.gateway / "openshell.db").read_bytes())
        self.assertTrue((self.state / "identity-ready").exists())
        self.assertEqual(json.loads((self.state / "identity-migration.json").read_text())["mode"], "verified-copy-source-retained")
        self.assertEqual(list(self.root.glob(".phoenix-agent-migration-*")), [])

    def test_copy_failure_keeps_source_no_marker_or_staging(self):
        with self.cross_filesystem():
            with self.assertRaises(subprocess.CalledProcessError): self.execute(cp_failure=True)
        self.assertTrue(self.gateway.is_dir())
        self.assertFalse((self.state / "identity-ready").exists())
        self.assertFalse((self.state / "openshell/gateway").exists())
        self.assertEqual(list(self.root.glob(".phoenix-agent-migration-*")), [])

    def test_bad_workspace_and_gateway_links_before_rename(self):
        alias = self.root / "alias"; alias.symlink_to(self.workspace)
        self.config["workspaces"] = [str(alias)]
        with self.assertRaises(ValueError): self.execute()
        self.assertTrue(self.gateway.is_dir())
        self.config["workspaces"] = [str(self.workspace)]
        (self.gateway / "outside").symlink_to(self.workspace)
        with self.assertRaises(ValueError): self.execute()
        self.assertTrue(self.gateway.is_dir())

    def test_history_file_symlink_and_hardlink_reject(self):
        target = self.root / "target"; target.write_bytes(b"unchanged")
        lock = self.old / "history.lock"; lock.symlink_to(target)
        with self.assertRaises(OSError): setup.history_file(lock, os.getuid())
        lock.unlink(); os.link(target, lock)
        with self.assertRaises(ValueError): setup.history_file(lock, os.getuid())
        self.assertEqual(target.read_bytes(), b"unchanged")

    def test_failure_diagnostic_excludes_fixture_secret(self):
        config = self.root / "setup.json"
        config.write_text(json.dumps(self.config | {"ignored": "synthetic-secret-auth"}))
        result = subprocess.run([os.sys.executable, "-I", str(Path(__file__).resolve().parents[1] / "identity-setup.py"), str(config)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"stage=root-authorization category=root-required", result.stderr)
        self.assertNotIn(b"synthetic-secret", result.stderr)

    def test_real_recursive_acl_on_held_root(self):
        if not self.config["setfacl"]: self.skipTest("ACL command unavailable")
        nested = self.workspace / "nested"; nested.mkdir(); (nested / "file").write_text("fixture")
        outside = self.root / "outside"; outside.mkdir(); (outside / "file").write_text("fixture")
        (self.workspace / "link").symlink_to(outside, target_is_directory=True)
        config = self.config | {"uid": os.getuid() + 7}
        setup.acl(config, str(self.workspace), recursive=True)
        getfacl = shutil.which("getfacl")
        result = subprocess.check_output([getfacl, "-n", str(nested / "file")], stderr=subprocess.DEVNULL).decode()
        self.assertIn(f'user:{config["uid"]}:rw-', result)
        defaults = subprocess.check_output([getfacl, "-n", str(nested)], stderr=subprocess.DEVNULL).decode()
        self.assertIn(f'default:user:{config["uid"]}:rwx', defaults)
        skipped = subprocess.check_output([getfacl, "-n", str(outside / "file")], stderr=subprocess.DEVNULL).decode()
        self.assertNotIn(f'user:{config["uid"]}:', skipped)


if __name__ == "__main__":
    unittest.main()
