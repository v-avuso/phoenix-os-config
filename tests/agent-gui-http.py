#!/usr/bin/env python3
"""Desktop HTTP/auth boundaries without real accounts, services or sockets."""
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "modules/development/ai/agent" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = load("gui-http-worker")
relay = load("gui-relay")


class DesktopHTTP(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"CODEX_AUTH_ACCESS_TOKEN": "opaque-fixture-handle", "PHOENIX_CODEX_ACCOUNT_ID": "11111111-1111-4111-8111-111111111111"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_fixed_destination_and_method(self):
        for url in ["https://evil.test/backend-api/me", "http://chatgpt.com/backend-api/me",
                    "https://chatgpt.com:443/backend-api/me", "https://chatgpt.com@evil.test/backend-api/me",
                    "https://chatgpt.com/backend-api/../auth", "https://chatgpt.com/backend-api/%2e%2e/auth",
                    "https://chatgpt.com/backend-api/\\evil", "https://chatgpt.com/auth/token",
                    "https://chatgpt.com/backend-api/me#fragment"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                worker.validate({"url": url})
        with self.assertRaises(ValueError):
            worker.validate({"url": "https://chatgpt.com/backend-api/me", "method": "CONNECT"})

    def test_caller_cannot_select_credential_account_or_cookie(self):
        request = worker.validate({"url": "https://chatgpt.com/backend-api/me", "headers": {
            "Authorization": "Bearer attacker-token", "Cookie": "private-host-cookie", "Host": "evil.test",
            "ChatGPT-Account-Id": "attacker-account", "X-OpenAI-Account-Routing-Override": "attacker",
            "Accept": "text/event-stream"}})
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(headers["authorization"], "Bearer opaque-fixture-handle")
        self.assertEqual(headers["chatgpt-account-id"], os.environ["PHOENIX_CODEX_ACCOUNT_ID"])
        self.assertNotIn("cookie", headers)
        self.assertNotIn("host", headers)
        self.assertNotIn("x-openai-account-routing-override", headers)
        self.assertEqual(headers["accept"], "text/event-stream")

    def test_header_injection_and_bounds(self):
        with self.assertRaises(ValueError):
            worker.validate({"url": "https://chatgpt.com/backend-api/me", "headers": {"Accept": "ok\r\nAuthorization: evil"}})
        with patch.object(worker, "LIMIT", 2), self.assertRaises(ValueError):
            worker.validate({"url": "https://chatgpt.com/backend-api/me", "body": base64.b64encode(b"123").decode()})
        with self.assertRaises(ValueError):
            worker.validate({"url": "https://chatgpt.com/backend-api/me", "body": "not-base64!"})

    def test_redirects_never_replay_auth(self):
        self.assertIsNone(worker.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://evil.test/"))

    def test_streaming_without_cookie_export(self):
        class Response:
            status = 200
            headers = {"Content-Type": "text/event-stream", "Set-Cookie": "secret-cookie"}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read1(self, _): return chunks.pop(0)
        chunks = [b"data: first\n\n", b"data: second\n\n", b""]
        output = []
        with patch.object(worker.sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b'{"url":"https://chatgpt.com/backend-api/me"}\n')})()), \
             patch.object(worker.urllib.request, "build_opener") as opener, patch.object(worker, "emit", output.append), \
             patch.object(worker, "apply_routing"):
            opener.return_value.open.return_value = Response()
            self.assertEqual(worker.main(), 0)
        self.assertEqual(output[0], {"status": 200, "headers": {"content-type": "text/event-stream"}})
        self.assertEqual(base64.b64decode(output[1]["chunk"]), b"data: first\n\n")
        self.assertEqual(base64.b64decode(output[2]["chunk"]), b"data: second\n\n")
        self.assertTrue(output[-1]["done"])

    def test_residency_comes_from_discovery_not_caller(self):
        account = os.environ["PHOENIX_CODEX_ACCOUNT_ID"]
        entry = {"id": account, "workspace_backend_origin": "NO_CONSTRAINT", "account_routing_override": "us_cr"}
        request = worker.validate({"url": "https://chatgpt.com/backend-api/me", "headers": {"X-OpenAI-Account-Routing-Override": "us"}})
        with patch.object(worker.urllib.request, "build_opener") as factory:
            opener = factory.return_value
            opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({"accounts": [entry]}).encode()
            worker.apply_routing(opener, request)
            headers = {key.lower(): value for key, value in request.header_items()}
            self.assertEqual(headers["x-openai-account-routing-override"], "us_cr")
            self.assertEqual(opener.open.call_args.args[0].full_url, worker.ACCOUNTS_URL)
            entry["workspace_backend_origin"] = "https://evil.test"
            opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({"accounts": [entry]}).encode()
            with self.assertRaises(ValueError):
                worker.apply_routing(opener, request)

    def test_identity_contains_only_public_account_and_actual_profile(self):
        token = relay.desktop_identity("public-account", {"id": "actual-user", "email": "fixture@example.invalid"})
        claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        self.assertEqual(claims["https://api.openai.com/auth"], {"chatgpt_account_id": "public-account", "user_id": "actual-user"})
        self.assertNotIn("opaque-fixture-handle", token)
        self.assertNotIn("chatgpt_plan_type", json.dumps(claims))

    def test_real_routing_required_and_no_constraint_matches_upstream(self):
        account = os.environ["PHOENIX_CODEX_ACCOUNT_ID"]
        entry = {"id": account, "workspace_backend_origin": "NO_CONSTRAINT", "account_routing_override": "NO_CONSTRAINT"}
        with patch.object(relay, "worker_json", return_value={"accounts": [entry]}):
            self.assertEqual(relay.worker_routing({}, account)["backendOrigin"], "https://chatgpt.com")
        with patch.object(relay, "worker_json", return_value={"accounts": [entry, entry]}), self.assertRaises(ValueError):
            relay.worker_routing({}, account)
        entry["workspace_backend_origin"] = "https://evil.test"
        with patch.object(relay, "worker_json", return_value={"accounts": [entry]}), self.assertRaises(ValueError):
            relay.worker_routing({}, account)


if __name__ == "__main__":
    unittest.main()
