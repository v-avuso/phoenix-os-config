#!/usr/bin/env python3
"""Real relay processes with disposable launchers; no auth or live services."""
import base64
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "modules/development/ai/agent"
ACCOUNT = "11111111-1111-4111-8111-111111111111"
MAX_RPC_FRAME = 16 * 1024 * 1024


class Connections(unittest.TestCase):
    def config(self, directory, source):
        path = Path(directory)
        (path / "account-id.json").write_text(json.dumps(ACCOUNT))
        (path / "launcher.json").write_text(json.dumps({"state": directory}))
        (path / "launcher.py").write_text(source)
        config = path / "relay.json"
        config.write_text(json.dumps({"python": sys.executable, "launcher": str(path / "launcher.py"),
            "launcher_config": str(path / "launcher.json"), "workdir": directory,
            "home": directory, "path": "/unused"}))
        return config

    def start_stdio_relay(self, config):
        parent, child = socket.socketpair()
        process = subprocess.Popen(
            [sys.executable, "-I", str(AGENT / "gui-relay.py"), str(config)],
            stdin=child, stdout=child, stderr=subprocess.PIPE,
        )
        child.close()
        parent.settimeout(5)
        return parent, process

    def wait_for_file(self, path):
        deadline = time.monotonic() + 3
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists(), f"fixture did not start: {path}")

    def send_repeated(self, sock, size, suffix=b""):
        chunk = b"x" * 65536
        while size:
            current = min(size, len(chunk))
            sock.sendall(chunk[:current])
            size -= current
        if suffix:
            sock.sendall(suffix)

    def receive_to_eof(self, sock):
        received = bytearray()
        while True:
            try:
                chunk = sock.recv(65536)
            except ConnectionResetError:
                break
            if not chunk:
                break
            received.extend(chunk)
        return bytes(received)

    def assert_child_reaped(self, pid_file):
        pid = int(pid_file.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_protocol_identity_routing_and_refresh_owner(self):
        source = '''import base64,json,sys
if sys.argv[2:] == ["--phoenix-gui-http"]:
    request=json.loads(sys.stdin.readline())
    value={"id":"actual-fixture-user","email":"fixture@example.invalid"} if request["url"].endswith("/me") else {"accounts":[{"id":"11111111-1111-4111-8111-111111111111","workspace_backend_origin":"NO_CONSTRAINT","account_routing_override":"NO_CONSTRAINT","plan_type":"plus","account_user_id":"actual-fixture-account-user"}]}
    print(json.dumps({"status":200,"headers":{}}))
    print(json.dumps({"chunk":base64.b64encode(json.dumps(value).encode()).decode()}))
    print(json.dumps({"done":True}))
else:
    assert sys.argv[2:] == ["app-server","--analytics-default-enabled"]
    for line in sys.stdin:
        request=json.loads(line)
        if request["method"] == "getAuthStatus":
            assert request["params"]["refreshToken"] is False
            result={"authMethod":"chatgptAuthTokens","authToken":"opaque-must-not-enter-gui"}
        elif request["method"] == "account/read": result={"account":{"type":"chatgpt"},"workspaceRouting":None}
        else: result={"ok":True}
        print(json.dumps({"id":request["id"],"result":result}),flush=True)
'''
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(directory, source)
            process = subprocess.Popen([sys.executable, "-I", str(AGENT / "gui-relay.py"), str(config)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for index, method in enumerate(["initialize", "account/read", "getAuthStatus"]):
                    process.stdin.write(json.dumps({"id": index, "method": method, "params": {"refreshToken": True}}).encode() + b"\n")
                    process.stdin.flush()
                    self.assertTrue(select.select([process.stdout], [], [], 5)[0])
                    result = json.loads(process.stdout.readline())["result"]
                    if method == "getAuthStatus":
                        token = result["authToken"]
                        self.assertNotIn("opaque-must-not-enter-gui", token)
                        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
                        auth = payload["https://api.openai.com/auth"]
                        self.assertEqual(auth["user_id"], "actual-fixture-user")
                        # Pinned main account-info rejects a token without this field.
                        self.assertEqual(auth["chatgpt_user_id"], "actual-fixture-user")
                        self.assertEqual(auth["chatgpt_plan_type"], "plus")
                        self.assertEqual(auth["chatgpt_account_user_id"], "actual-fixture-account-user")
                    elif method == "account/read":
                        self.assertEqual(result["account"]["email"], "fixture@example.invalid")
                        self.assertEqual(result["account"]["planType"], "plus")
                        self.assertEqual(result["workspaceRouting"]["chatgptAccountId"], ACCOUNT)
                        self.assertEqual(result["workspaceRouting"]["backendOrigin"], "https://chatgpt.com")
                process.stdin.close()
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 0, process.stderr.read())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()

    def test_http_disconnect_cancels_fixed_worker(self):
        source = '''import base64,json,pathlib,signal,sys,time
assert sys.argv[2:] == ["--phoenix-gui-http"]
signal.signal(signal.SIGTERM,lambda *_:(pathlib.Path("cancelled").write_text("yes"),sys.exit(0)))
json.loads(sys.stdin.readline())
print(json.dumps({"status":200,"headers":{"content-type":"text/event-stream"}}),flush=True)
print(json.dumps({"chunk":base64.b64encode(b"data: first\\n\\n").decode()}),flush=True)
time.sleep(30)
'''
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(directory, source)
            parent, child = socket.socketpair()
            process = subprocess.Popen([sys.executable, "-I", str(AGENT / "gui-http-relay.py"), str(config)],
                stdin=child, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child.close()
            try:
                parent.settimeout(5)
                parent.sendall(b"GET https://chatgpt.com/backend-api/test HTTP/1.1\r\nHost: local\r\n\r\n")
                response = b""
                while b"data: first" not in response:
                    response += parent.recv(65536)
                self.assertIn(b"200 OK", response)
                parent.close()
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 0, process.stderr.read())
                self.assertEqual((Path(directory) / "cancelled").read_text(), "yes")
            finally:
                parent.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
                process.stderr.close()

    def test_shared_socket_keeps_input_open_between_requests(self):
        source = "import sys\nfor line in sys.stdin.buffer:\n sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\n"
        with tempfile.TemporaryDirectory() as directory:
            config = self.config(directory, source)
            parent, relay = self.start_stdio_relay(config)
            try:
                for index in range(3):
                    # The idle gap must not be mistaken for EOF/EAGAIN: stdin
                    # and stdout share the same nonblocking socket description.
                    time.sleep(0.1)
                    frame = json.dumps({"id": index, "method": "initialize"}).encode() + b"\n"
                    parent.sendall(frame)
                    received = b""
                    while len(received) < len(frame):
                        chunk = parent.recv(65536)
                        self.assertTrue(chunk, "relay closed between requests")
                        received += chunk
                    self.assertEqual(received, frame)
                    self.assertIsNone(relay.poll())
                parent.shutdown(socket.SHUT_WR)
                self.assertEqual(relay.wait(timeout=5), 0)
                self.assertEqual(relay.stderr.read(), b"")
            finally:
                parent.close()
                if relay.poll() is None:
                    relay.kill()
                    relay.wait()
                relay.stderr.close()

    def test_oversized_inbound_frames_terminate_child_without_forwarding(self):
        self.assertEqual(MAX_RPC_FRAME, 16 * 1024 * 1024)
        for newline in (False, True):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                launcher = path / "launcher.py"
                launcher.write_text(
                    "import os,pathlib,sys\n"
                    "assert sys.argv[2:]==['app-server','--analytics-default-enabled']\n"
                    "pathlib.Path('child.pid').write_text(str(os.getpid()))\n"
                    "data=os.read(0,65536)\n"
                    "pathlib.Path('received.bin').write_bytes(data)\n"
                    "os.write(1,b'{\"result\":{}}\\n')\n"
                )
                config = self.config(directory, launcher.read_text())
                parent, relay = self.start_stdio_relay(config)
                sender_error = []
                try:
                    pid_file = path / "child.pid"
                    self.wait_for_file(pid_file)

                    def send_oversize():
                        try:
                            # A newline-terminated frame is MAX+1 bytes; the
                            # unterminated case reaches the cap without it.
                            self.send_repeated(parent, MAX_RPC_FRAME,
                                               b"\n" if newline else b"")
                        except OSError as error:
                            sender_error.append(error)

                    sender = threading.Thread(target=send_oversize, daemon=True)
                    sender.start()
                    relay.wait(timeout=5)
                    sender.join(timeout=2)
                    self.assertFalse(sender.is_alive(), "oversize sender remained blocked")
                    self.assertEqual(relay.returncode, 1)
                    self.assert_child_reaped(pid_file)
                    self.assertEqual((path / "received.bin").read_bytes() if (path / "received.bin").exists() else b"", b"")
                    self.assertEqual(self.receive_to_eof(parent), b"")
                    self.assertEqual(relay.stderr.read(), b"Sandbox desktop RPC frame exceeds 16 MiB limit\n")
                finally:
                    parent.close()
                    relay.stderr.close()
                    if relay.poll() is None:
                        relay.kill()
                        relay.wait()

    def test_oversized_backend_frame_is_bounded_and_not_forwarded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            launcher = path / "launcher.py"
            launcher.write_text(
                "import os,pathlib,sys\n"
                "assert sys.argv[2:]==['app-server','--analytics-default-enabled']\n"
                "pathlib.Path('child.pid').write_text(str(os.getpid()))\n"
                "remaining=16*1024*1024+1\n"
                "chunk=b'x'*65536\n"
                "while remaining:\n"
                " n=min(remaining,len(chunk));os.write(1,chunk[:n]);remaining-=n\n"
            )
            config = self.config(directory, launcher.read_text())
            parent, relay = self.start_stdio_relay(config)
            try:
                pid_file = path / "child.pid"
                self.wait_for_file(pid_file)
                relay.wait(timeout=5)
                self.assertEqual(relay.returncode, 1)
                self.assert_child_reaped(pid_file)
                self.assertEqual(self.receive_to_eof(parent), b"")
                self.assertEqual(relay.stderr.read(), b"Sandbox desktop RPC frame exceeds 16 MiB limit\n")
            finally:
                parent.close()
                relay.stderr.close()
                if relay.poll() is None:
                    relay.kill()
                    relay.wait()

    def test_auth_refresh_rewrite_cannot_exceed_frame_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            launcher = path / "launcher.py"
            launcher.write_text(
                "import os,pathlib,sys\n"
                "assert sys.argv[2:]==['app-server','--analytics-default-enabled']\n"
                "pathlib.Path('child.pid').write_text(str(os.getpid()))\n"
                "data=os.read(0,65536)\n"
                "pathlib.Path('received.bin').write_bytes(data)\n"
            )
            config = self.config(directory, launcher.read_text())
            parent, relay = self.start_stdio_relay(config)
            try:
                pid_file = path / "child.pid"
                self.wait_for_file(pid_file)
                prefix = b'{"id":1,"method":"getAuthStatus","params":{"refreshToken":true,"p":"'
                suffix = b'"}}\n'
                padding = MAX_RPC_FRAME - len(prefix) - len(suffix)
                parent.sendall(prefix)
                self.send_repeated(parent, padding)
                parent.sendall(suffix)
                self.assertEqual(relay.wait(timeout=5), 1)
                self.assert_child_reaped(pid_file)
                self.assertEqual((path / "received.bin").read_bytes() if (path / "received.bin").exists() else b"", b"")
                self.assertEqual(self.receive_to_eof(parent), b"")
                self.assertEqual(relay.stderr.read(), b"Sandbox desktop RPC frame exceeds 16 MiB limit\n")
            finally:
                parent.close()
                relay.stderr.close()
                if relay.poll() is None:
                    relay.kill()
                    relay.wait()

    def test_oversized_input_interrupts_a_blocked_client_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            launcher = path / "launcher.py"
            launcher.write_text(
                "import os,pathlib,sys\n"
                "assert sys.argv[2:]==['app-server','--analytics-default-enabled']\n"
                "pathlib.Path('child.pid').write_text(str(os.getpid()))\n"
                "line=b'{\\\"id\\\":1,\\\"result\\\":{\\\"padding\\\":\\\"'+b'x'*(8*1024*1024)+b'\\\"}}\\n'\n"
                "view=memoryview(line);offset=0\n"
                "while offset<len(view): offset+=os.write(1,view[offset:])\n"
                "data=os.read(0,65536)\n"
                "pathlib.Path('received.bin').write_bytes(data)\n"
            )
            config = self.config(directory, launcher.read_text())
            parent, relay = self.start_stdio_relay(config)
            parent.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            sender_error = []
            try:
                pid_file = path / "child.pid"
                self.wait_for_file(pid_file)
                self.assertTrue(select.select([parent], [], [], 3)[0], "backend response did not reach client socket")
                time.sleep(0.1)  # Let the small receive buffer hold the relay's write open.

                def send_oversize():
                    try:
                        self.send_repeated(parent, MAX_RPC_FRAME)
                    except OSError as error:
                        sender_error.append(error)

                sender = threading.Thread(target=send_oversize, daemon=True)
                sender.start()
                started = time.monotonic()
                relay.wait(timeout=3)
                self.assertLess(time.monotonic() - started, 3)
                sender.join(timeout=2)
                self.assertFalse(sender.is_alive(), "oversize sender remained blocked")
                self.assertEqual(relay.returncode, 1)
                self.assert_child_reaped(pid_file)
                self.assertEqual((path / "received.bin").read_bytes() if (path / "received.bin").exists() else b"", b"")
                output = self.receive_to_eof(parent)
                self.assertLess(len(output), 8 * 1024 * 1024 + 64)
                self.assertEqual(relay.stderr.read(), b"Sandbox desktop RPC frame exceeds 16 MiB limit\n")
            finally:
                parent.close()
                relay.stderr.close()
                if relay.poll() is None:
                    relay.kill()
                    relay.wait()

    def test_maximum_sized_json_rpc_frame_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            launcher = path / "launcher.py"
            launcher.write_text(
                "import json,sys\n"
                "assert sys.argv[2:]==['app-server','--analytics-default-enabled']\n"
                "for line in sys.stdin.buffer:\n"
                " json.loads(line)\n"
                " print('{\"id\":1,\"result\":{\"ok\":true}}',flush=True)\n"
            )
            config = self.config(directory, launcher.read_text())
            parent, relay = self.start_stdio_relay(config)
            try:
                prefix = b'{"id":1,"method":"initialize","params":{"p":"'
                suffix = b'"}}\n'
                padding = MAX_RPC_FRAME - len(prefix) - len(suffix)
                self.assertGreater(padding, 0)
                parent.sendall(prefix)
                self.send_repeated(parent, padding)
                parent.sendall(suffix)
                self.assertEqual(parent.recv(128), b'{"id":1,"result":{"ok":true}}\n')
                parent.shutdown(socket.SHUT_WR)
                self.assertEqual(relay.wait(timeout=5), 0)
                self.assertEqual(relay.stderr.read(), b"")
            finally:
                parent.close()
                relay.stderr.close()
                if relay.poll() is None:
                    relay.kill()
                    relay.wait()


if __name__ == "__main__":
    unittest.main()
