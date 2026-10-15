# OpenShell shutdown ordering acceptance

The ordering option stays disabled until actual OpenShell passes this procedure.
Run only in a disposable NixOS VM with its own user, gateway state, Podman
storage and persistent journal. Never stop the operator's shared services.

## Prerequisites

Use locked configuration, OpenShell 0.1.2 CLI/gateway and configured pinned
supervisor/runtime images and locked packages (current host: Podman 5.8.7,
systemd 260.4; the smoke test records actual guest versions). Provide cached
`localhost/phoenix-codex:0.1.2`, valid sandbox policy and VM-local TLS; no personal
credentials/providers. Enable `phoenix.agent.shutdownOrdering.enable` in the
guest before boot. Record package/image identities, effective units and stop
deadlines. Preserve the observed 45-second scope fallback; shortening it is not
a fix. The default command sandbox hides `/dev/kvm`; supported host-level read-only
inspection confirmed the host device exists. The host subsequently passed an explicit read/write KVM open and
`KVM_GET_API_VERSION=12` probe without creating a VM. No realized cached QEMU
package was found in the bounded store inspection. Actual OpenShell and VM-manager shutdown
have **not** passed this procedure.

## Active workload and captures

Run in a separate guest terminal/harness and retain command-output attachment:

```sh
openshell sandbox create --name shutdown-acceptance --no-auto-providers \
  --no-tty --from localhost/phoenix-codex:0.1.2 -- /bin/bash -c '
trap '\''printf "ACCEPT_TERM\n"; sleep 1; printf "ACCEPT_FINAL\n"; exit 0'\'' TERM
n=0
while :; do printf "ACCEPT_TICK_%s\n" "$n"; n=$((n+1)); sleep 1; done
'
```

Wait for several numbered lines; confirm workload and supervisor are running.
Record sandbox ID with `openshell sandbox get shutdown-acceptance --output json`;
resolve its exact containers through Podman's `openshell.ai/sandbox-id` labels.
Derive exact `libpod-<container-id>.scope` names; avoid broad container selection.
Capture CLI output, timestamped workload/supervisor Podman logs, persistent user
journal for gateway/Podman/exact scopes, and
`openshell logs shutdown-acceptance --tail --source sandbox`. Record scope
`Before`, `ControlGroup`, `TimeoutStopUSec`, process cgroups, and actual workload
`memory.max`/`pids.max` against requested limits.

Workload stdout and supervisor `PushSandboxLogs` are separate channels. Generate
repeatable policy-mediated activity using a fixture allowed by the guest policy;
match its supervisor events between local supervisor logs and gateway logs.
Retain the final shutdown supervisor events for durable comparison. A workload
final marker or tail disconnect alone does not establish gateway log flush.

## Stop transactions

Exercise ordinary sandbox stop using the supported CLI, then recreate the
fixture. Submit gateway and both exact scope stops in one guest transaction:

```sh
# Replace these placeholders only with IDs recorded for this fixture.
workload_scope='libpod-<workload-id>.scope'
supervisor_scope='libpod-<supervisor-id>.scope'
time systemctl --user stop phoenix-openshell-gateway.service \
  "$workload_scope" "$supervisor_scope"
```

Check monotonic journal ordering: gateway begins shutdown while both scopes
exist; driver stops supervisor before workload teardown; dependent scope stop
jobs do not deliver competing early TERM. Conmon remains in the Podman service
cgroup; workload resource cgroups remain enabled.

Collect stopped state, then restart only the disposable gateway. Query
`openshell logs shutdown-acceptance --source sandbox`; compare final supervisor
events with local logs to prove persistence across gateway exit. If legitimate
reconciliation removes the sandbox, obtain its durable log evidence through a
supported gateway interface before removal; otherwise report the missing
inspection capability rather than claiming success.

Repeat with a fresh active fixture and the VM harness's orderly guest shutdown
(or termination of this disposable user's manager). Use `--detach` for this
case if needed, retaining Podman/local logs. Capture serial/journal output and
inspect persisted logs after reboot. This establishes manager-wide shutdown;
the three-unit transaction alone does not.

## Acceptance limits

Each cooperative case must satisfy:

- TERM and final markers delivered, terminal status consistent with graceful
  exit, and no surviving owned workload, supervisor or monitor;
- final supervisor events persisted in gateway logs, without forced
  `PushSandboxLogs` termination or unexplained missing events;
- no supervisor SIGKILL/exit 137, boundary TERM-before-confirmation warning,
  or delay until the 45-second scope fallback;
- stop completes within 10 seconds for this one-second trap fixture, evidenced
  by monotonic timestamps with fallback deadlines unchanged;
- correct ordering, resource limits retained, and subsequent gateway start
  succeeds without unintended sandbox resurrection.

Also test disposable TERM-ignoring workload and unavailable control/log peer.
Record which deadline terminates each phase; cleanup must finish within existing
fallback plus five seconds of harness margin. Require explicit forced-exit/log
loss evidence when it occurs. Do not shorten 45 seconds or weaken cgroups. If
normal shutdown still stalls, instrument the specific awaited phase before
adding a Rust patch; source inspection does not identify the stalled call.

## Existing evidence and upstream limits

The October 11 isolated trial used an owned transient rootless API,
`CONTAINERS_CONF_OVERRIDE`, cached Phoenix image and installed crun 1.27.1.
API-created scope had the expected `Before=<trial-api>.service`; conmon belonged
to that service; `memory.max=268435456` and `pids.max=64` survived. Concurrent
API/scope stop completed in 1.96 seconds with TERM/final markers, exit zero and
service success. Container removed and service inactive. This proves native
configuration/runtime compatibility, not OpenShell shutdown or gateway drain.

Pinned 0.1.2 supervisor source matched its release tar. Shutdown can signal,
wait five seconds, terminate, then wait without one overall deadline; log push
is detached. Exact v0.1.3 and inspected main retain these relevant patterns.
The observed 45-second supervisor stall's exact await remains unknown. Ordering
is a supported experiment; upgrade or shorter timeout is not a proven remedy.

## On-demand smoke and pending regression

`tests/shutdown.nix` now defines only a small rootless Podman smoke: one guest,
4 GiB RAM/two CPUs, fresh UID 1000 with lingering user manager, persistent journal
and an owned BusyBox image. It loads the image locally, starts/stops a cooperative
container, checks exit zero/removal and no surviving conmon, then verifies the
user manager remains active. It is not registered in default flake checks and
was cost-qualified: 245.4 MiB cached downloads/726.9 MiB unpacked, with prebuilt
QEMU. Its first 55.6-second build/run reached the user manager but failed before
container creation because the login shell lacked the guest user runtime/bus
environment. The wrapper now supplies `/run/user/1000` and its bus explicitly;
Nix/Python syntax checks pass, but a rerun is pending and smoke has not passed.
It has no personal mounts, credentials, gateway or OpenShell images.

After committing the owned files, evaluate and inspect download/build costs from
the exact Git revision (replace COMMIT with its full hash):

```sh
nix eval --raw --expr 'let
  f = builtins.getFlake "git+file:///home/v/repos/code/phoenix-os-config?rev=COMMIT";
  pkgs = f.inputs.nixpkgs.legacyPackages.x86_64-linux;
  smoke = import (f.outPath + "/modules/development/ai/agent/tests/shutdown.nix") { inherit pkgs; };
in smoke.drvPath'
nix build --dry-run --no-link --expr 'let
  f = builtins.getFlake "git+file:///home/v/repos/code/phoenix-os-config?rev=COMMIT";
  pkgs = f.inputs.nixpkgs.legacyPackages.x86_64-linux;
in import (f.outPath + "/modules/development/ai/agent/tests/shutdown.nix") { inherit pkgs; }'
```

These commands do not request a build/test run. Stop if dry-run requires source
compilation of QEMU/Rust or exceeds the cost gate below; do not fetch dependencies
to discover their cost. An actual smoke build/run needs the next explicit execution
step after this preflight. Never use `path:.` or include the unrelated root draft.

For the full regression, reuse the locked Nixpkgs `pkgs.testers.runNixOSTest` driver and its rootless
Podman/lingering-user pattern in the existing module-local smoke; extend it only
after the cost gate. No separate Python harness is currently needed. The upstream OpenShell 0.1.2 Podman gateway restart test
covers lifecycle intent, but not concurrent systemd scope teardown and durable
final logs. Running its whole conformance/Ansible setup would add unrelated work.

Use one guest (4 GiB RAM, two CPUs), fresh user/home, isolated Podman/gateway
state, local TLS, persistent journal and exact pinned packages. Pre-import the
Phoenix workload image and two pinned runtime images; no runtime image pulls,
GUI/history mounts or personal provider credentials. Verify a guest-local policy
HTTP event is present in supervisor and gateway logs before running both stop
cases above. Account for intended gateway restart/resume semantics when checking
post-stop state.

Estimate: 2–4 hours implementation/integration, not a measured completion promise.
Proposed preflight limit: 30 minutes, 8 GiB downloads and 25 GiB scratch; stop and
reassess if exceeded or if Rust/QEMU must build from source. Cold closure sizes
remain unknown. Verify KVM access and image archives/hashes before proceeding;
allow at most five minutes for the ready guest's regression run. Preserve the
10-second cooperative pass and 45-second safety net; stop at the first reproduced
stall (50-second harness deadline) to identify the last acknowledged cleanup phase
before choosing a Rust fix. Only the rootless smoke definition exists; full OpenShell regression implementation
and all VM execution remain pending.
