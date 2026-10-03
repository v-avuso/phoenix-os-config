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
    config = {"home": "/home/example", "workspaces": [str(workspace)],
              "profile": directory + "/private-profile", "path": "/immutable-tools"}
    import os
    env = {"XDG_RUNTIME_DIR": "/run/user/" + str(os.getuid()), "WAYLAND_DISPLAY": "wayland-1",
           "SECRET_TOKEN": "must-not-enter", "CODEX_CLI_PATH": "/unrestricted", "PYTHONPATH": "/injected"}
    clean = launch.environment(config, env)
    assert not any(key in clean for key in ("SECRET_TOKEN", "CODEX_CLI_PATH", "PYTHONPATH"))
    assert clean["HOME"] == "/home/example"
    assert clean["PATH"] == "/immutable-tools"
    launch.validate(config)
    assert (Path(config["profile"]) / "home").stat().st_mode & 0o777 == 0o700
    alias = Path(directory) / "alias"
    alias.symlink_to(workspace, target_is_directory=True)
    for invalid in [config | {"workspaces": [str(alias)]},
                    config | {"profile": str(alias)},
                    config | {"workspaces": [directory + "/missing"]}]:
        try:
            launch.validate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Aliased or missing private path accepted")
    for invalid in [env | {"WAYLAND_DISPLAY": "../bus"}, env | {"XDG_RUNTIME_DIR": "/run/user/foreign"}]:
        try:
            launch.environment(config, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Foreign display/runtime accepted")
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
