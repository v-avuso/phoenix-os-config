#!/usr/bin/env python3
"""Focused GUI boundary fixtures; no display, credentials or activation."""
import importlib.util
import tempfile
import json
import socket
import subprocess
import shutil
import sys
import time
from pathlib import Path
from unittest import mock
from types import SimpleNamespace

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

# Standard tray replies select only the exact immutable filtered proxy owner.
tray_config = {"busctl": "/immutable/busctl", "proxyExecutable": "/immutable/proxy",
               "proxySocket": "/fixed/proxy/bus"}
tray_items = ["org.freedesktop.StatusNotifierItem-2-1/StatusNotifierItem"]
def tray_reply(command, **kwargs):
    assert command[:3] == [tray_config["busctl"], "--user", "--json=short"]
    assert kwargs["timeout"] <= 2
    if command[3] == "get-property": value = {"type": "as", "data": tray_items}
    elif "GetNameOwner" in command:
        service = command[-1]
        value = {"type": "s", "data": [service if service.startswith(":") else ":1.99"]}
    elif "GetConnectionUnixProcessID" in command: value = {"type": "u", "data": [987]}
    else:
        assert command[3:] == ["call", ":1.99", "/StatusNotifierItem", "org.kde.StatusNotifierItem", "Activate", "ii", "0", "0"]
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")
    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(value).encode(), stderr=b"")
with mock.patch.object(launch.subprocess, "run", side_effect=tray_reply) as run, \
     mock.patch.object(launch.Path, "resolve", return_value=Path("/immutable/proxy")), \
     mock.patch.object(launch.Path, "stat", return_value=SimpleNamespace(st_uid=os.getuid())), \
     mock.patch.object(launch.Path, "read_bytes", return_value=b"/immutable/proxy\0/fixed/proxy/bus\0--filter\0"):
    assert launch.reactivate(tray_config, clean)
    assert any("Activate" in call.args[0] for call in run.call_args_list)
    run.reset_mock()
    assert not launch.reactivate(tray_config | {"proxySocket": "/foreign/bus"}, clean)
    assert not any("Activate" in call.args[0] for call in run.call_args_list)
    tray_items[:] = [":1.99/StatusNotifierItem", ":1.100/StatusNotifierItem"]
    run.reset_mock()
    assert not launch.reactivate(tray_config, clean)
    assert not any("Activate" in call.args[0] for call in run.call_args_list)
with mock.patch.object(launch.subprocess, "run", side_effect=tray_reply) as run, \
     mock.patch.object(launch.Path, "resolve", return_value=Path("/native/electron")), \
     mock.patch.object(launch.Path, "stat", return_value=SimpleNamespace(st_uid=os.getuid())), \
     mock.patch.object(launch.Path, "read_bytes") as read:
    assert not launch.reactivate(tray_config, clean)
    read.assert_not_called()
    assert not any("Activate" in call.args[0] for call in run.call_args_list)

# Independent wrapper launches must not concurrently open one private profile:
# Chromium's own singleton check cannot see another wrapper's private /tmp.
with tempfile.TemporaryDirectory() as directory:
    temporary = Path(directory)
    marker = temporary / "started"
    wrapper = temporary / "wrapper.py"
    wrapper.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nimport time\n"
                       + "Path(" + repr(str(marker)) + ").touch()\ntime.sleep(1)\n")
    wrapper.chmod(0o700)
    config = temporary / "gui.json"
    config.write_text(json.dumps({"home": directory, "workspaces": [directory],
        "profile": directory + "/profile", "path": "/unused", "workdir": directory,
        "systemctl": shutil.which("true"), "wrapper": str(wrapper)}))
    command = [sys.executable, "-I", str(ROOT / "modules/development/ai/agent/gui-launch.py"), str(config)]
    env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/" + str(os.getuid()), WAYLAND_DISPLAY="wayland-1")
    first = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists(), first.communicate(timeout=3)
        second = subprocess.run(command, env=env, capture_output=True, timeout=3)
        assert second.returncode == 0 and b"already running" in second.stderr
        assert first.wait(timeout=3) == 0
        third = subprocess.run(command, env=env, capture_output=True, timeout=3)
        assert third.returncode == 0 and b"already running" not in third.stderr
    finally:
        if first.poll() is None:
            first.kill()
            first.wait()
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
