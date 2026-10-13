"""Shared GUI lifetime/readiness fixtures; synthetic state, no GUI/auth."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import socket
import select
import threading
from unittest import mock
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

    def test_link_bounds_and_unsupported_schemes(self):
        for uri in ("https://example.com", "file:///tmp/file", "codex://thread/ bad", "codex://" + "a" * 4097, "codex://user:pass@thread/fixture", "codex://["):
            result = subprocess.run(self.command("native", 'print("started")') + [uri], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"started", result.stdout)
            self.assertNotIn(uri.encode(), result.stderr)
        result = subprocess.run(self.command("native", 'print("started")') +
                                ["codex://one", "codex://two"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_existing_lock_requires_private_mode(self):
        lock = self.root / "gui.lock"
        for mode in (0o644, 0o660):
            lock.write_text("retained")
            lock.chmod(mode)
            result = subprocess.run(self.command("native", 'print("started")'), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"started", result.stdout)
            self.assertEqual(lock.read_text(), "retained")
            self.assertEqual(lock.stat().st_mode & 0o777, mode)

    @unittest.skipUnless(os.environ.get("PHOENIX_TEST_NODE"), "Set PHOENIX_TEST_NODE to an absolute Node executable")
    def test_guard_owner_normal_close_new_guard(self):
        node = os.environ["PHOENIX_TEST_NODE"]
        self.assertTrue(Path(node).is_absolute())
        config = json.loads(self.config.read_text())
        config["controlDir"] = str(self.root / "control")
        self.config.write_text(json.dumps(config))
        owner = self.root / "owner.cjs"
        owner.write_text("""
const {EventEmitter} = require('node:events');
const directory = process.env.PHOENIX_GUI_CONTROL_DIR;
delete process.env.PHOENIX_GUI_CONTROL_DIR;
const {createControl} = require(%s);
const app = new EventEmitter();
app.whenReady = async () => {};
app.on('phoenix-shared-open-link', () => console.log('link-received'));
app.quit = () => { app.emit('will-quit'); process.exit(0); };
const electron = {app, BrowserWindow:{getFocusedWindow:()=>null},
  Menu:{getApplicationMenu:()=>null}, dialog:{showMessageBox:async()=>({response:1})}};
const control = createControl(electron, {directory,
  token:process.env.PHOENIX_GUI_OWNER_TOKEN, variant:process.env.PHOENIX_GUI_VARIANT});
control.server.once('listening',()=>console.log('ready'));
""" % json.dumps(str(MODULE / "gui-control.cjs")))
        first = subprocess.Popen([sys.executable, "-I", str(self.script), str(self.config),
                                  "native", "--", node, str(owner)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([first.stdout], [], [], 5)[0], "Owner startup timed out")
            self.assertEqual(first.stdout.readline().strip(), b"ready")
            repeated = subprocess.run(self.command("native", 'raise SystemExit("must not launch")') +
                                      ["codex://thread/fixture"], capture_output=True, timeout=5)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertTrue(select.select([first.stdout], [], [], 5)[0])
            self.assertEqual(first.stdout.readline().strip(), b"link-received")
            previous = json.loads((self.root / "gui.lock").read_text())
            switched = subprocess.run(self.command("sandbox", 'import sys; assert sys.argv[1] == "codex://thread/fixture"; print("started")') + ["codex://thread/fixture"], capture_output=True, timeout=8)
            self.assertEqual(switched.returncode, 0, switched.stderr)
            self.assertIn(b"started", switched.stdout)
            self.assertEqual(first.wait(timeout=5), 0)
            current = json.loads((self.root / "gui.lock").read_text())
            self.assertEqual(current["variant"], "sandbox")
            self.assertNotEqual(current["nonce"], previous["nonce"])
        finally:
            if first.poll() is None:
                first.terminate()
            first.communicate(timeout=5)

    def test_owner_transport_partial_eof_and_slow_drip(self):
        spec = importlib.util.spec_from_file_location("state", MODULE / "gui-state.py")
        state = importlib.util.module_from_spec(spec); spec.loader.exec_module(state)
        owner = {"variant":"native", "nonce":"a" * 64}
        fd = os.open(self.root / "fixture.lock", os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        os.write(fd, json.dumps(owner).encode())
        directory = self.root / "control"; directory.mkdir(mode=0o700)
        endpoint = directory / (owner["nonce"][:16] + ".sock")
        for response in (b'{"status":', b'x'):
            server = socket.socket(socket.AF_UNIX); server.bind(str(endpoint)); endpoint.chmod(0o600); server.listen()
            def reply():
                peer, _ = server.accept()
                with peer:
                    peer.recv(512); peer.sendall(response)
            thread = threading.Thread(target=reply); thread.start()
            try:
                if response == b'x':
                    with mock.patch.object(state.time, "monotonic", side_effect=[0,0,46]):
                        result = state.request_owner({"controlDir":str(directory)}, fd, owner, "switch", "sandbox")
                else:
                    result = state.request_owner({"controlDir":str(directory)}, fd, owner, "switch", "sandbox")
                self.assertEqual(result, "unavailable")
            finally:
                thread.join(timeout=3); server.close(); endpoint.unlink()
                self.assertFalse(thread.is_alive())
        changed = {"variant":"sandbox", "nonce":"b" * 64}
        self.assertEqual(state.request_owner({"controlDir":str(directory)}, fd, changed, "open-link", "native", "codex://thread/fixture"), "changed")
        self.assertFalse(state.acquire_after_close(fd, changed, timeout=0.1))

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
