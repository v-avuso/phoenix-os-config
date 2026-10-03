#!/usr/bin/env python3
"""Focused GUI boundary fixtures; no display, credentials or activation."""
import importlib.util
import tempfile
import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "modules/development/ai/agent" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

client = load("gui-client")
assert client.supported(["-c", "features.code_mode_host=true", "app-server", "--analytics-default-enabled"])
assert not client.supported(["exec", "touch", "/tmp/escape"])
assert not client.supported(["app-server", "--listen", "tcp://0.0.0.0:1234"])
assert client.main("/missing/phoenix-gui.sock", "0.159.0", ["app-server"]) == 1

launch = load("gui-launch")
with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory) / "workspace"
    workspace.mkdir()
    config = {"home": "/home/example", "user": "example", "workspaces": [str(workspace)],
              "workdir": str(workspace), "bwrap": "/bwrap", "ca_file": "/immutable-ca-bundle", "client": "/client", "desktop": "/desktop", "path": "/tools"}
    args = launch.command(config, {"XDG_RUNTIME_DIR": "/run/user/1000", "WAYLAND_DISPLAY": "wayland-1",
                                  "SECRET_TOKEN": "must-not-enter"}, Path(directory), Path(directory) / "bus")
    assert "--clearenv" in args and "SECRET_TOKEN" not in args
    cli_index = args.index("CODEX_CLI_PATH")
    assert args[cli_index + 1] == "client"  # Plain override prevents bundled fallback.
    assert "/home/example/.codex" in args  # Private namespace home, not host bind.
    mounts = [args[i + 1:i + 3] for i, item in enumerate(args) if item in ("--bind", "--ro-bind", "--dev-bind")]
    assert ["/home/example", "/home/example"] not in mounts
    assert [str(workspace), str(workspace)] in mounts
    for destination in ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-bundle.crt"]:
        assert ["/immutable-ca-bundle", destination] in mounts
    assert ["/etc/ssl", "/etc/ssl"] not in mounts
    assert not any(path.startswith("/etc/static") for pair in mounts for path in pair)
    assert args[args.index("SSL_CERT_FILE") + 1] == "/etc/ssl/certs/ca-certificates.crt"
    assert not any("podman" in path or "phoenix-admin" in path for pair in mounts for path in pair)
    assert ["/run/user/1000/bus", "/run/user/1000/bus"] not in mounts
    try:
        launch.command(config, {"XDG_RUNTIME_DIR": "/run/user/1000", "WAYLAND_DISPLAY": "../bus"}, Path(directory), Path(directory) / "bus")
    except ValueError:
        pass
    else:
        raise AssertionError("Aliased Wayland socket accepted")
# Exercise the socket-activated service contract with a real subprocess. The
# client sends bytes only; no header can select a host executable or arguments.
with tempfile.TemporaryDirectory() as directory:
    temporary = Path(directory)
    fixture = temporary / "launcher.py"
    fixture.write_text("import sys\nassert sys.argv[2:] == ['app-server', '--analytics-default-enabled']\nprint(sys.stdin.readline().strip(), flush=True)\n")
    config = temporary / "relay.json"
    config.write_text(json.dumps({"python": sys.executable, "launcher": str(fixture),
        "launcher_config": "/immutable-config", "workdir": directory,
        "home": directory, "path": "/unused"}))
    parent, child = socket.socketpair()
    process = subprocess.Popen([sys.executable, "-I", str(ROOT / "modules/development/ai/agent/gui-relay.py"), str(config)],
                               stdin=child, stdout=child, stderr=subprocess.PIPE)
    child.close()
    try:
        parent.settimeout(5)
        payload = b'{"method":"initialize","untrusted":"/bin/sh"}\n'
        parent.sendall(payload)
        assert parent.recv(4096) == payload
        process.wait(timeout=5)
        assert process.returncode == 0, process.stderr.read()
    finally:
        parent.close()
        if process.poll() is None:
            process.kill()
            process.wait()
print("agent-gui: boundary and socket relay fixtures passed")
