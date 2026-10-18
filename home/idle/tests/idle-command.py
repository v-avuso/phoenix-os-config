#!/usr/bin/env python3
"""Check the locked idle schema, monitor API, IPC route and applied patch."""

import json
import os
import re
import pathlib
import subprocess
import sys
import tempfile

shell_source, quickshell_source, cli_source, patch_file, baseline_file, shell_package, blank_command, hyprland_source = map(
    pathlib.Path, sys.argv[1:]
)


def block_after(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated block: {marker}")

schema = (shell_source / "plugin/src/Caelestia/Config/generalconfig.hpp").read_text()
assert "CONFIG_PROPERTY(QVariant, idleAction" in schema
assert "CONFIG_PROPERTY(QVariant, returnAction" in schema
assert "onTimeout" not in schema and "onResume" not in schema

monitor_api = (quickshell_source / "src/wayland/idle_notify/monitor.hpp").read_text()
assert "Defaults to zero, which reports idle status immediately." in monitor_api
assert "When set to true, @@isIdle will depend on both user interaction and active idle inhibitors." in monitor_api

ipc_cli = (quickshell_source / "src/launch/parsecommand.cpp").read_text()
assert 'add_subcommand("ipc"' in ipc_cli and 'add_subcommand("call"' in ipc_cli
caelestia_cli = (cli_source / "src/caelestia/subcommands/shell.py").read_text()
assert '["qs", "-c", "caelestia", *args]' in caelestia_cli
assert 'self.shell("ipc", "call", *args)' in caelestia_cli

# Exercise the packaged executable without blanking the live desktop.
with tempfile.TemporaryDirectory(prefix="phoenix-blank-route-") as tmp:
    root = pathlib.Path(tmp)
    stub = root / "caelestia"
    stub.write_text(f"#!{sys.executable}\nimport json, os, sys\nopen(os.environ['BLANK_TEST_LOG'], 'w').write(json.dumps(sys.argv[1:]))\n")
    stub.chmod(0o755)
    command = root / "blank"
    script, replacements = re.subn(r"/nix/store/[^\s]+/bin/caelestia", str(stub), blank_command.read_text())
    assert replacements == 2
    command.write_text(script)
    command.chmod(0o755)
    log = root / "argv.json"
    for args, expected in (([], ["shell", "idle", "activate", "0"]), (["off"], ["shell", "idle", "restore"])):
        subprocess.run([str(command), *args], env={**os.environ, "BLANK_TEST_LOG": str(log)}, check=True)
        assert json.loads(log.read_text()) == expected
    print("blank: packaged activation/restoration use the Caelestia CLI IPC route once")

with tempfile.TemporaryDirectory(prefix="phoenix-idle-patch-") as tmp:
    root = pathlib.Path(tmp)
    target = root / "modules/IdleMonitors.qml"
    target.parent.mkdir()
    target.write_bytes((shell_source / "modules/IdleMonitors.qml").read_bytes())
    subprocess.run(
        ["patch", "-p1", "-d", str(root)],
        input=patch_file.read_bytes(),
        check=True,
    )
    qml = target.read_text()

# Exercise the exact pinned compositor methods, rather than inventing resumed events.
manual_timeout = float(re.search(r"id: manualIdleMonitor\s+enabled:.*?timeout: ([0-9.]+)", qml, re.S).group(1))
compositor = (hyprland_source / "src/protocols/IdleNotify.cpp").read_text()
methods = []
for signature in ("void CExtIdleNotification::update(uint32_t elapsedMs)", "void CExtIdleNotification::reset()", "void CExtIdleNotification::onTimerFired()"):
    methods.append(signature + " {" + block_after(compositor, signature) + "}")
cpp = r"""
#include <chrono>
#include <optional>
struct Resource { int idled = 0, resumed = 0; void sendIdled() { ++idled; } void sendResumed() { ++resumed; } };
struct Timer { template<class T> void updateTimeout(T) {} };
struct Protocol { bool isInhibited = false; };
namespace PROTO { Protocol state; Protocol* idle = &state; }
struct CExtIdleNotification {
    Resource resource; Resource* m_resource = &resource;
    Timer timer; Timer* m_timer = &timer;
    uint32_t m_timeoutMs; bool m_obeyInhibitors = false, m_idled = false;
    void update(uint32_t elapsedMs); void reset(); void onTimerFired();
};
""" + "\n".join(methods) + f"""
int main() {{
    CExtIdleNotification notification;
    notification.m_timeoutMs = {int(manual_timeout * 1000)};
    notification.onTimerFired(); // inactivity reaches the configured timeout
    notification.update(0); // actual Hyprland input/activity path
    return notification.resource.resumed == 1 && !notification.m_idled ? 0 : 1;
}}
"""
with tempfile.TemporaryDirectory(prefix="phoenix-idle-compositor-") as tmp:
    source = pathlib.Path(tmp) / "idle.cpp"
    binary = pathlib.Path(tmp) / "idle"
    source.write_text(cpp)
    subprocess.run(["c++", "-std=c++23", str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

packaged_qml = (shell_package / "share/caelestia-shell/modules/IdleMonitors.qml").read_text()
assert 'target: "idle"' in packaged_qml
assert "function activate(index: int)" in packaged_qml
assert "function restore(): void" in packaged_qml
assert "timeout: 1.0" in packaged_qml
assert "respectInhibitors: false" in packaged_qml
assert "root.manualIdleEntry.idleAction" in packaged_qml
assert "Component.onDestruction: finishManualIdle()" in packaged_qml

for fragment in (
    "import Quickshell.Io",
    'target: "idle"',
    "function activate(index: int)",
    "function restore(): void",
    "timeout: 1.0",
    "respectInhibitors: false",
    "root.manualIdleEntry.idleAction",
    "root.finishManualIdle();",
    "Component.onDestruction: finishManualIdle()",
):
    assert fragment in qml, fragment

baseline = json.loads(baseline_file.read_text())
timeout = baseline["general"]["idle"]["timeouts"][0]
assert timeout["timeout"] == 300
assert "onTimeout" not in timeout and "onResume" not in timeout
assert timeout["idleAction"][2] == "phoenix_idle_blank(true)"
assert timeout["returnAction"][2] == "phoenix_idle_blank(false)"

finish = block_after(qml, "function finishManualIdle(): void")
finish = finish.replace("manualIdleEntry", "root.manualIdleEntry")
finish = finish.replace("manualIdleActionApplied", "root.manualIdleActionApplied")
finish = finish.replace("handleIdleAction", "root.handleIdleAction")
activate = block_after(qml, "function activate(index: int): void")
restore = block_after(qml, "function restore(): void")
idle_changed = block_after(qml, "onIsIdleChanged: {")
node_test = f"""
const assert = require('node:assert/strict');
const finishBody = {json.dumps(finish)};
const activateBody = {json.dumps(activate)};
const restoreBody = {json.dumps(restore)};
const idleChangedBody = {json.dumps(idle_changed)};
const entry = {{ idleAction: ['blank-on'], returnAction: ['restore'] }};
const GlobalConfig = {{ general: {{ idle: {{ timeouts: {{ values: [entry] }} }} }} }};

function harness(reenter = false) {{
  const actions = [];
  const root = {{ manualIdleEntry: null, manualIdleActionApplied: false }};
  root.finishManualIdle = new Function('root', `return function() {{{{${{finishBody}}}}}}`)(root);
  root.handleIdleAction = action => {{
    actions.push(action);
    if (reenter && action === entry.idleAction)
      root.finishManualIdle();
  }};
  root.activate = new Function('root', 'GlobalConfig', `return function(index) {{${{activateBody}}}}`)(root, GlobalConfig);
  root.restore = new Function('root', `return function() {{{{${{restoreBody}}}}}}`)(root);
  root.idleChanged = new Function('root', `return function(isIdle) {{${{idleChangedBody}}}}`)(root);
  return {{ root, actions }};
}}

// Activation is idempotent; idle runs once, input restores once and releases.
{{
  const {{ root, actions }} = harness();
  root.activate(99);
  assert.equal(root.manualIdleEntry, null);
  root.activate(0);
  const selected = root.manualIdleEntry;
  root.activate(0);
  assert.equal(root.manualIdleEntry, selected);
  root.idleChanged(true);
  root.idleChanged(true);
  assert.deepEqual(actions, [entry.idleAction]);
  root.idleChanged(false);
  root.idleChanged(false);
  assert.deepEqual(actions, [entry.idleAction, entry.returnAction]);
  assert.equal(root.manualIdleEntry, null);
}}

// Explicit restore before idle does nothing; after idle it releases once.
{{
  const {{ root, actions }} = harness();
  root.activate(0);
  root.restore();
  assert.deepEqual(actions, []);
  root.idleChanged(true);
  assert.deepEqual(actions, []);
  root.activate(0);
  root.idleChanged(true);
  root.restore();
  root.restore();
  assert.deepEqual(actions, [entry.idleAction, entry.returnAction]);
}}

// The state flips before calling an action, so a reentrant release is safe.
{{
  const {{ root, actions }} = harness(true);
  root.activate(0);
  root.idleChanged(true);
  root.idleChanged(false);
  assert.deepEqual(actions, [entry.idleAction, entry.returnAction]);
  assert.equal(root.manualIdleEntry, null);
}}

// Component teardown uses the same exactly-once cleanup as explicit restore.
{{
  const {{ root, actions }} = harness();
  root.activate(0);
  root.idleChanged(true);
  root.finishManualIdle();
  root.finishManualIdle();
  assert.deepEqual(actions, [entry.idleAction, entry.returnAction]);
}}
"""
subprocess.run(["node", "-e", node_test], check=True)
print("idle schema, positive-timeout compositor resume, CLI IPC, patch and manual state transitions passed")
