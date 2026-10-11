#!/usr/bin/env python3
"""Disposable kernel transport checks; no accounts, ACLs, Podman or services changed."""
import array
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import shutil
import io
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "identity-transport.py"
spec = importlib.util.spec_from_file_location("identity_transport", MODULE)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class IdentityTransport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        self.config = {"operatorUid": os.getuid(), "workspaces": [self.root],
                       "command": [sys.executable, "-c", 'import sys; print("ready",flush=True); x=sys.stdin.readline(); print(x,flush=True); print("stderr",file=sys.stderr); sys.exit(7)'],
                       "environment": {}}

    def request(self, connection, fds, args=None):
        connection.sendmsg([json.dumps({"args": args or [], "cwd": self.root}).encode() + b"\n"],
                           [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))])

    def test_duplex_eof_separate_stderr_exit(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close); self.addCleanup(right.close)
        ri, wi = os.pipe(); ro, wo = os.pipe(); re, we = os.pipe()
        for fd in (wi, ro, re): self.addCleanup(os.close, fd)
        thread = threading.Thread(target=transport.serve, args=(self.config, right))
        thread.start()
        self.request(left, [ri, wo, we])
        for fd in (ri, wo, we): os.close(fd)
        self.assertEqual(os.read(ro, 6), b"ready\n")
        os.write(wi, b"hello\n")
        self.assertEqual(json.loads(left.recv(1024)), {"exit": 7})
        self.assertIn(b"hello", os.read(ro, 1024))
        self.assertEqual(os.read(re, 1024), b"stderr\n")
        thread.join(5); self.assertFalse(thread.is_alive())

    def test_peer_and_admission(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close); self.addCleanup(right.close)
        with self.assertRaises(ValueError):
            transport.serve(self.config | {"operatorUid": os.getuid() + 1}, right)
        for args in (["--config", "bad"], ["--phoenix-exec", "/bin/sh"], ["app-server", "--listen", "tcp://localhost"]):
            with self.assertRaises(ValueError): transport.admit(self.config, {"args": args, "cwd": self.root})
        with self.assertRaises(ValueError): transport.admit(self.config, {"args": [], "cwd": "/"})
        alias = Path(self.root, "alias"); alias.symlink_to(self.root)
        with self.assertRaises(ValueError): transport.admit(self.config, {"args": [], "cwd": str(alias)})

    def test_isolated_launcher_packaging(self):
        address = str(Path(self.root, "launch.sock"))
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(address); listener.listen(1); self.addCleanup(listener.close)
        errors = []
        def worker():
            try:
                connection, _ = listener.accept()
                with connection: transport.serve(self.config, connection)
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=worker); thread.start()
        isolated = Path(self.root, "launch.py")
        shutil.copyfile(MODULE.with_name("launch.py"), isolated)
        config = Path(self.root, "launcher.json")
        config.write_text(json.dumps({"identitySocket": address, "identityTransport": str(MODULE)}))
        result = subprocess.run([sys.executable, "-I", str(isolated), str(config), "app-server"], cwd=self.root, input=b"duplex\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        thread.join(5)
        self.assertEqual(result.returncode, 7)
        self.assertIn(b"duplex", result.stdout)
        self.assertEqual(result.stderr, b"stderr\n")
        self.assertEqual(errors, [])
        self.assertEqual(transport.admit(self.config, {"args": ["login"], "cwd": self.root})[0], ["--", "login"])
        self.assertEqual(transport.admit(self.config, {"args": ["app-server"], "cwd": self.root})[0], ["app-server"])

    def test_partial_initial_send_is_completed(self):
        class Connection:
            def connect(self, _address): pass
            def sendmsg(self, data, rights):
                self.frame = data[0]; self.sent = self.frame[:7]; return 7
            def sendall(self, data): self.sent += data
            def makefile(self, _mode): return io.BytesIO(b'{"exit":0}\n')
            def close(self): pass
        connection = Connection()
        with patch.object(transport.socket, "socket", return_value=connection), patch.object(transport.os, "isatty", return_value=False):
            self.assertEqual(transport.client({"socket": "unused"}, ["fixture"]), 0)
        self.assertEqual(connection.sent, connection.frame)

    def test_failure_diagnostic_excludes_prompt(self):
        config = Path(self.root, "client.json")
        config.write_text(json.dumps({"socket": str(Path(self.root, "missing"))}))
        result = subprocess.run([sys.executable, "-I", str(MODULE), "--client", str(config), "synthetic-secret-prompt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"stage=connect category=socket-unavailable", result.stderr)
        self.assertNotIn(b"synthetic-secret", result.stderr)

    def test_bad_descriptor_count_closes_received_rights(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close); self.addCleanup(right.close)
        fd = os.open("/dev/null", os.O_RDONLY); self.addCleanup(os.close, fd)
        before = len(os.listdir("/proc/self/fd"))
        self.request(left, [fd, fd])
        with self.assertRaises(ValueError): transport.serve(self.config, right)
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_disconnect_cancels(self):
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        ro, wo = os.pipe(); null = os.open("/dev/null", os.O_RDWR)
        self.addCleanup(os.close, ro); self.addCleanup(os.close, null)
        errors = []
        def worker():
            try: transport.serve(self.config | {"command": [sys.executable, "-c", 'import os,time; print(os.getpid(),flush=True); time.sleep(60)']}, right)
            except BrokenPipeError: pass
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=worker); thread.start()
        self.request(left, [null, wo, null]); os.close(wo)
        pid = int(os.read(ro, 64)); left.close()
        thread.join(7); self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])
        with self.assertRaises(ProcessLookupError): os.kill(pid, 0)

    def test_client_restores_terminal_and_forwards_resize(self):
        import fcntl
        import pty
        import struct
        import termios
        master, slave = pty.openpty()
        self.addCleanup(os.close, master); self.addCleanup(os.close, slave)
        initial = termios.tcgetattr(slave)
        address = str(Path(self.root, "launch.sock"))
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(address); listener.listen(1); self.addCleanup(listener.close)
        code = 'import termios,signal,os,fcntl,struct; a=termios.tcgetattr(0); a[3]&=~termios.ECHO; termios.tcsetattr(0,termios.TCSANOW,a); signal.signal(signal.SIGWINCH,lambda *_: (print(struct.unpack("HHHH",fcntl.ioctl(0,termios.TIOCGWINSZ,bytes(8)))[:2],flush=True),exit(0))); print("ready",flush=True); signal.pause()'
        errors=[]
        def worker():
            try:
                connection, _ = listener.accept()
                with connection: transport.serve(self.config | {"command": [sys.executable, "-c", code]}, connection)
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=worker); thread.start()
        config = Path(self.root, "client.json"); config.write_text(json.dumps({"socket": address}))
        client = subprocess.Popen([sys.executable, "-I", str(MODULE), "--client", str(config)], cwd=self.root,
                                  stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(client.stdout.close); self.addCleanup(client.stderr.close)
        self.addCleanup(lambda: client.poll() is None and (client.kill(), client.wait()))
        self.assertEqual(client.stdout.readline(), b"ready\n")
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 35, 120, 0, 0))
        client.send_signal(signal.SIGWINCH)
        self.assertEqual(client.stdout.readline(), b"(35, 120)\n")
        self.assertEqual(client.wait(timeout=5), 0)
        thread.join(5); self.assertEqual(errors, [])
        self.assertEqual(termios.tcgetattr(slave), initial)


if __name__ == "__main__":
    unittest.main()
