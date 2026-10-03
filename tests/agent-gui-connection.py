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
import unittest

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "modules/development/ai/agent"
ACCOUNT = "11111111-1111-4111-8111-111111111111"


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


if __name__ == "__main__":
    unittest.main()
