"""Socket-activated fixed app-server relay; never accepts a host command."""
import os
import base64
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid


def desktop_identity(account, profile):
    """Public routing claims, never a credential accepted by OpenAI.

    The desktop parses its auth status as JWT before invoking its own HTTP.
    That HTTP is separately mediated; the actual app-server retains handles.
    No entitlement is invented here.
    """
    encode = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    now = int(time.time())
    return ".".join([encode({"alg": "none", "typ": "JWT"}),
                     encode({"sub": profile["id"], "exp": now + 3600,
                             "https://api.openai.com/auth": {
                                 "chatgpt_account_id": account, "user_id": profile["id"]},
                             "https://api.openai.com/profile": {"email": profile.get("email")}}),
                     "phoenix-opaque-desktop"])


def worker_json(config, url):
    request = {"url": url, "method": "GET"}
    result = subprocess.run(
        [config["python"], "-I", config["launcher"], config["launcher_config"], "--phoenix-gui-http"],
        input=json.dumps(request).encode() + b"\n", stdout=subprocess.PIPE, stderr=sys.stderr,
        cwd=config["workdir"], timeout=180,
        env={"HOME": config["home"], "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}", "PATH": config["path"]})
    if result.returncode or len(result.stdout) > 2 * 1024 * 1024:
        raise ValueError("Sandbox routing discovery failed")
    frames = [json.loads(line) for line in result.stdout.splitlines()]
    if not frames or frames[0].get("status") != 200 or frames[-1].get("done") is not True:
        raise ValueError("Sandbox routing discovery unavailable")
    body = b"".join(base64.b64decode(frame["chunk"], validate=True) for frame in frames[1:-1])
    return json.loads(body)


def worker_routing(config, account):
    discovered = worker_json(config, "https://chatgpt.com/backend-api/wham/accounts/check")
    candidates = [entry for entry in discovered["accounts"] if entry.get("id") == account]
    if len(candidates) != 1:
        raise ValueError("Sandbox workspace routing is ambiguous")
    selected = candidates[0]
    # Upstream treats NO_CONSTRAINT as the configured bootstrap origin.
    origin = selected.get("workspace_backend_origin")
    if origin == "NO_CONSTRAINT":
        origin = "https://chatgpt.com"
    if origin != "https://chatgpt.com" or selected.get("account_routing_override") not in {"NO_CONSTRAINT", "us", "us_cr"}:
        raise ValueError("Sandbox workspace routing outside declared endpoint")
    return {"chatgptAccountId": account, "backendOrigin": origin,
            "accountRoutingOverride": selected["account_routing_override"]}


def relay(config):
    # systemd supplies the accepted full-duplex socket on stdin/stdout.
    # Only this immutable command can run, irrespective of client bytes.
    process = subprocess.Popen(
        [config["python"], "-I", config["launcher"], config["launcher_config"],
         "app-server", "--analytics-default-enabled"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
        cwd=config["workdir"], env={"HOME": config["home"],
            "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
            "PATH": config["path"]})

    pending = {}
    pending_lock = threading.Lock()
    account = None
    routing = None
    profile = None

    def input_stream():
        try:
            buffer = b""
            # Raw fd reads avoid a daemon thread retaining Python's buffered
            # stdin lock when an app-server exits before the GUI disconnects.
            while chunk := os.read(0, 65536):
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line += b"\n"
                    try:
                        request = json.loads(line)
                        if request.get("method") in {"account/read", "getAuthStatus"} and "id" in request:
                            with pending_lock:
                                pending[json.dumps(request["id"])] = request["method"]
                            # Gateway is the sole credential-refresh owner.
                            if isinstance(request.get("params"), dict):
                                request["params"]["refreshToken"] = False
                                line = json.dumps(request).encode() + b"\n"
                    except (ValueError, TypeError):
                        pass
                    process.stdin.write(line)
                    process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            process.stdin.close()

    threading.Thread(target=input_stream, daemon=True).start()
    try:
        for line in process.stdout:
            method = None
            response = {}
            try:
                response = json.loads(line)
                with pending_lock:
                    method = pending.pop(json.dumps(response.get("id")), None)
                if method and isinstance(response.get("result"), dict):
                    if account is None:
                        launcher = json.loads(Path(config["launcher_config"]).read_text())
                        account = str(uuid.UUID(json.loads((Path(launcher["state"]) / "account-id.json").read_text())))
                    result = response["result"]
                    if method == "getAuthStatus" and result.get("authToken"):
                        profile = profile or worker_json(config, "https://chatgpt.com/backend-api/me")
                        if not isinstance(profile.get("id"), str) or not profile["id"]:
                            raise ValueError("Desktop profile identity missing")
                        result["authToken"] = desktop_identity(account, profile)
                    if method == "account/read" and (result.get("account") or {}).get("type") == "chatgpt" and not result.get("workspaceRouting"):
                        routing = routing or worker_routing(config, account)
                        result["workspaceRouting"] = routing
                    line = json.dumps(response).encode() + b"\n"
            except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
                # A failed routing repair cannot silently claim usable auth or
                # expose an upstream handle; return a bounded protocol failure.
                if method:
                    line = json.dumps({"id": response.get("id"), "error": {
                        "code": -32000, "message": "Sandbox desktop routing unavailable; retained login was preserved"}}).encode() + b"\n"
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    import json
    with open(sys.argv[1]) as stream:
        relay(json.load(stream))
