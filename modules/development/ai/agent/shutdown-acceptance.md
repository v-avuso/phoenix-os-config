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
The corrected smoke passed in 21.9 seconds, producing
`/nix/store/r7j4ilpb5gd34s7kxf283jhsqawrnld9-vm-test-run-phoenix-shutdown-smoke`.
This proves guest/rootless prerequisites, not OpenShell shutdown.
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

### Explicit OpenShell ordinary-stop slice

`tests/shutdown-openshell.nix` takes `{ pkgs, runtime, supervisor, workload }`.
Each image argument is `{ archive, sha256, id }`: an explicit immutable public
OCI or Docker archive path, its hexadecimal SHA256 and its independently verified
image configuration ID (without `sha256:`). Evaluation checks archive hashes; the guest
checks loaded IDs and references images by those IDs, avoiding lost registry
digest names after archive import. It never adopts host container state or credentials.
Do not add binary archives to Git. For a verified export, verify the exact
configured repository digest and configuration ID. Export that exact cached ID
with `podman save --format docker-archive --output ARCHIVE IMAGE_ID`, without
adding or changing host tags. Record the new archive SHA256 while retaining the
original RepoDigest-to-ID proof, then publish only the image archive into the Nix
store. Podman 5.8.7's save/load manuals support both OCI and Docker archives; its
[save implementation](https://github.com/containers/podman/blob/v5.8.7/pkg/domain/infra/abi/images.go#L462-L481)
accepts a name or ID. This transport choice still requires guest-load/ID verification;
it does not claim bit-identical archives across exports. A future fixed-output `dockerTools.pullImage` may supply the same
contract after its image/hash binding is independently verified.

The current verified Docker-archive bindings below passed guest loading. The
original OCI runtime/supervisor exports failed import and were superseded without
changing expected image IDs. The workload archive binding is unchanged:

| Image | Archive SHA256 | Image ID |
| --- | --- | --- |
| runtime | `ff175171aa978b7232ec5ca938162b95c825b8c387c42cc380d53421d8c886aa` | `e7a78d2e2c9c7d6ffc801e429a3304b51ffd65a84692530f2bbceea11e6e1558` |
| supervisor | `b77c8746e6228799e00bddb5b751f9155244c7e7f0b8f28f8eefaf936609e2c2` | `494b86855b51987cd68e205aa1b08d67592d4ea7b989f94c66e7179e17a97388` |
| workload | `581c4cbbbbeac1aee7481c14e9702e9c39c2906627e1a3e28f4652492e1405aa` | `d090ea4d6e2780f9ee6aaf8e89543f70808d792731dc3e733438d4ccd5c77623` |

Use the previous exact-Git-revision expression, importing
`tests/shutdown-openshell.nix` instead, and pass the three bindings. For example,
`runtime.archive = builtins.storePath "/nix/store/...-runtime.docker.tar";` retains
its dependency context. No host archive locations are defaults. Evaluate/dry-run
this explicit derivation before authorizing its build/run.

This first slice uses exact release CLI/gateway packages and production-equivalent
rootless API/TLS parameters, a new guest UID 1000 and eight-GiB guest disk. Ordering
stays OFF, stop fallback stays 45 seconds, and the driver has a 300-second global
limit. The attached supported create stream records TERM/final workload markers;
Podman runtime logs and the supervisor's supported log stream are separate captures.
A deliberately denied guest-local HTTP request must produce a supervisor deny
event before stopping. Ordinary supported stop must finish under ten seconds with
zero container exit codes and the final workload markers. Bounded before/failure/final
artifacts include workload stream/status, workload/supervisor logs/inspect and
user-manager/unit journals. A failure identifies its last explicit stage; it does
not prove which internal await stalled.

The first actual OpenShell VM attempt failed after 19.6 seconds at image loading:
Podman reported `Digest of source image manifest would not match destination
reference` for the runtime OCI archive exported by registry digest. No gateway,
sandbox or shutdown operation was reached; this is archive transport evidence,
not a supervisor failure. Re-exporting the same verified IDs in supported Docker
archive format resolved image loading. Ordinary-stop acceptance remains unpassed
until subsequent stages succeed.
The Docker-archive rerun passed image imports, TLS/gateway readiness and CLI
status, but failed before workload readiness: CreateSandbox returned its
30-second API timeout. Exact 0.1.2 source places the last completed channel-volume
creation immediately before workload `POST /v5.0.0/libpod/containers/create`.
No workload-create completion was observed. A same-image identity inspection had
completed quickly; cold keep-id/rootfs preparation remains a hypothesis, not a
permission or hardware diagnosis. This did not exercise ordinary shutdown.

For the next isolated run, pass `probeCreateOnly = true;` to the same test import.
It starts only the dedicated guest API after image import, then uses maintained
`podman --remote --url unix:///run/user/1000/phoenix-openshell-podman.sock create`
with the exact workload ID and no execution. Baseline uses `--network=none`,
`--pull=never` and `/bin/true` entrypoint; the second request adds production
`--userns keep-id:uid=1000,gid=1000`. Both use fixed labeled fixture names and a
35-second external cap. Record entered/completed monotonic timing and status;
a failure stops after captures, without proceeding or warming a later ordinary
stop run. A successful created probe is removed before the next comparison.
No gateway or sandbox is started in probe-only mode; it cannot pass shutdown
acceptance. Neither production's 30-second API deadline nor 45-second stop fallback
changes. Server debug/body logging is not enabled; remote command status/timing,
fixed-name inspections and bounded user-service journals supply metadata.

Captures discover partial containers by managed and exact sandbox-name labels
even before READY, and preserve all disposable guest container-list metadata plus
fixed probe-name snapshots. Attached create now fails promptly when its status
file appears before readiness, rather than waiting the remaining 60-second poll.

Combined gateway/exact-scope stop, manager-wide shutdown and durable final
supervisor-event comparison after gateway restart remain pending; workload stdout
or a closed tail alone never proves final log persistence. Do not extend or patch
Rust until this first actual OpenShell slice produces evidence.

For the full regression, reuse the locked Nixpkgs `pkgs.testers.runNixOSTest` driver and its rootless
Podman/lingering-user pattern in the existing module-local smoke; extend it only
after the cost gate. The maintained NixOS driver owns the harness; the adjacent
`shutdown-openshell.py` is only its test script. The upstream OpenShell 0.1.2
Podman gateway restart test
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
before choosing a Rust fix. The rootless smoke passed. The ordinary OpenShell
slice is defined and syntax-checked; the latest VM attempt passed archive loading
and gateway readiness but timed out creating the workload. Ordinary-stop runtime
acceptance remains pending. Combined
gateway/scope stop, full user-manager shutdown and durable final-log persistence
remain pending.
