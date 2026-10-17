# OpenShell shutdown ordering acceptance

Shutdown options remain disabled on the live host. Final repeatable source-built
images now pass cooperative ordinary log-drain (1.528 seconds) and ordered
user-manager teardown (1.489 seconds): TERM/FINAL, both container exits 0, explicit
client cancellation 1, actual accepted-tail RPC acknowledgement and verified
running ELF/image bindings. Ordinary proves a final live gateway event; manager
is immediately inactive with resource/cgroup gates preserved and no PAM/restart.
Earlier prototype transaction evidence remains scoped below. Next required work
is actual cold service composition, a pinned-contract-length peer-loss client
observation and controlled rollout. Atomic module wiring is implemented/OFF with
focused helper/launcher and generated ON/OFF checks; no service activation is
claimed. TERM-ignore passes in 5.484s with truthful forced workload
status; gateway loss passes local cleanup/typed log failure in 1.536s with
independent markers, while its attached CLI remains pending after 5s. Detached denial-summary draining is a telemetry
limit, not a baseline blocker; restart durability is outside the upstream
memory-tail contract. See [source packaging and exact final receipts](shutdown/README.md).

## Prerequisites

Run only in a disposable NixOS VM with fresh user/home, isolated gateway/Podman
state, local TLS, persistent journal and locked packages. Use OpenShell 0.1.2
CLI/gateway, independently verified immutable runtime/supervisor archives and the
small representative workload below; full Phoenix-image startup is a separate
gap. No personal mounts, credentials or providers. Enable ordering only for its
explicit A/B case, not as an ordinary-stop prerequisite. Record actual guest
versions, image IDs, effective units and deadlines. Preserve the five-second TERM
grace and observed 45-second fallback; shortening deadlines is not a repair.

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
Retain the final shutdown supervisor events for live gateway receipt comparison. A workload
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

Collect stopped state and final-event receipt while the gateway is still alive.
Its log tail is memory-only: restart is not a durable-log acceptance test. For
combined teardown retain independent persistent journal/Podman captures; a later
gateway restart must follow normal retained-intent behavior, without interpreting
loss of the old in-memory tail as a new flush defect.

Repeat with a fresh active fixture and the VM harness's orderly guest shutdown
(or termination of this disposable user's manager). Use `--detach` for this
case if needed, retaining Podman/local logs. Capture serial/journal output and
inspect persisted logs after reboot. This establishes manager-wide shutdown;
the three-unit transaction alone does not.

## Acceptance limits

Each cooperative case must satisfy:

- TERM/final markers, stopped owned workload/supervisor, and terminal semantics
  appropriate to the case: administrative cancellation is explicit nonzero failure,
  not a fabricated canonical command success;
- accepted final supervisor events acknowledged by the completed push RPC and
  observable in the live gateway tail; observer/tail exit alone proves neither
  push completion nor persistence across gateway restart;
- no supervisor SIGKILL/exit 137, boundary TERM-before-confirmation warning,
  or delay until the 45-second scope fallback;
- stop completes within 10 seconds for this one-second trap fixture, evidenced
  by monotonic timestamps with fallback deadlines unchanged;
- correct ordering, resource limits retained, and subsequent gateway start
  matches documented retained-intent behavior.

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

### Small representative workload

`tests/shutdown-workload.nix` is an on-demand `{ pkgs }` image factory using the
maintained `dockerTools.buildLayeredImage`. It contains Bash, curl, coreutils,
`/bin/sh`, CA certificates and numeric sandbox UID/GID 1000 accounts, with private
owned `/sandbox` and sticky `/tmp`. Fakeroot supplies archive ownership without a
root build or build-time VM. It contains no Codex, Nix CLI, agent/broker config,
history, credentials or host mounts. Build from the exact committed Git source:

```sh
nix build --no-link --print-out-paths --expr 'let
  f = builtins.getFlake "git+file:///home/v/repos/code/phoenix-os-config?rev=COMMIT";
  pkgs = f.inputs.nixpkgs.legacyPackages.x86_64-linux;
in import (f.outPath + "/modules/development/ai/agent/tests/shutdown-workload.nix") { inherit pkgs; }'
```

Record the built archive SHA256 and Docker config/image ID from its manifest;
pass that normal `{ archive, sha256, id }` workload record to the unchanged driver.
There is no default host path or import-from-derivation step. First run
`probeCreateOnly = true` with this image. Only if it passes should a fresh ordinary
OpenShell test use it, with the same exact runtime/supervisor images and keep-id.
The image tests shutdown/control and the policy log stream, not Codex/model or
full Phoenix-image startup. The large-image result below remains unresolved.

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
A direct HTTP request to reserved TEST-NET `192.0.2.1:80`, with curl proxies
explicitly disabled and bounded connect/total time, must produce the exact
0.1.2 destination-bound supervisor `Denied staged transparent connection` event
in gateway sandbox logs before stopping. Log delivery has a bounded ten-second
poll budget (each query capped at five seconds); the HTTP request is not retried. Ordinary supported stop must finish under ten seconds with
zero container exit codes and the final workload markers. Bounded before/failure/final
artifacts include workload stream/status, workload/supervisor logs/inspect and
user-manager/unit journals. A failure identifies its last explicit stage; it does
not prove which internal await stalled.

The first actual OpenShell VM attempt failed after 19.6 seconds at image loading:
Podman reported `Digest of source image manifest would not match destination
reference` for the runtime OCI archive exported by registry digest. No gateway,
sandbox or shutdown operation was reached; this is archive transport evidence,
not a supervisor failure. Re-exporting the same verified IDs in supported Docker
archive format resolved image loading. This historical setup failure did not
exercise shutdown; the current scoped prototype results are summarized above.
The small-image ordinary run reached the workload and network probe, but the
original localhost HTTP request only produced workload-local connection refusal,
not a supervisor deny event. That was an invalid probe: exact 0.1.2
`e2e/rust/tests/no_proxy.rs` deliberately tests localhost staying local;
`openshell-sandbox/src/network_broker.rs:824` bypasses staged policy for loopback.
The source-backed nonloopback replacement enters staged TCP mediation
(`network_broker.rs:835`), with the denial emitted before connection by
`openshell-supervisor-network/src/proxy.rs:700`. Its source-backed proxy mode has
no ordinary loopback listener when mediation is supplied (`proxy.rs:288–293`),
so forcing a loopback proxy listener would also be unsupported here. Corrected
source `82a9669` passed the nonloopback deny-event assertion. Ordinary stop took
1.498 seconds; workload output included `ACCEPT_TERM` and `ACCEPT_FINAL`.
Supervisor exited zero, runtime exited one without OOM, and attached create did
not produce its status file within five seconds. Ordinary acceptance failed
after stop; the original 45-second stall was not reproduced.

Exact 0.1.2 source explains distinct failure paths with high confidence:
administrative shutdown skips normal exit reporting and terminal-delivery drain
(`openshell-supervisor/src/lib.rs:1184–1238`); SSH waits for terminal-report
acknowledgement before sending Exit (`openshell-supervisor-process/src/ssh.rs:721–724`,
`delegated.rs:45–62`). Boundary termination sets state `Terminal`
(`openshell-sandbox/src/boundary_server.rs:1832–1855`), but later SIGTERM treats
every non-`Connected` state as before confirmation (`:493–519`). Prior gateway
logs prove enforcement confirmation. Runtime exit one therefore does not show
failed workload TERM handling; final markers also do not establish canonical
command exit zero or its delivery. Gateway log push ended gRPC 13 with relay/TLS
EOF at supervisor exit; durable final-log flush remains unproved. Artifacts:
`/nix/store/7dfjinf28r9wn1daldy3zks76dnyp5dm-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence`.

The subsequent combined and ordered-manager cases below supplied separate
lifetime-ordering evidence. The historical ordinary attachment/classification
failures motivated the now-validated isolated prototypes; full acceptance remains
strict and the original combined stall's exact awaited call remains unknown.

### Combined teardown reproduction

Source `8307f7` reproduced the stall in the disposable guest: one transaction
stopped the gateway and both exact recorded libpod scopes in 45.409 seconds
(status zero). Both containers exited 137 without OOM; TERM was observed but
FINAL was absent, attached transport remained pending, and log reader exited one.
Both scopes had empty `Before` and 45-second stop limits. Journals show simultaneous
stop, immediate Sandbox Protocol loss/freeze, then Podman supervisor fallback and
systemd workload-scope SIGKILL at the 45-second deadline. Gateway StopSandbox
completed only afterwards. Artifacts:
`/nix/store/pngnr2nxycqxfcj4jvjnl12r46v0mnv9-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence`.
The subsequent ordering A/B below mitigated this reproduction; it did not identify the exact blocked await.

The exact 0.1.2 mechanism is source-backed but the precise pending await remains
unknown. `boundary_server.rs:1732–1785` freezes on authenticated transport loss and
schedules recovery expiry after 30 seconds. `boundary_io.rs:126–140` sends SIGSTOP
to registered workload groups; `:187–208` explicitly continues them before graceful
TERM. A frozen trap cannot finish its sleep/final marker until resumed. Supervisor
shutdown (`lib.rs:1155–1178`) depends on remote Signal, Wait (five-second first
grace), Terminate, a second unbounded Wait, and finally TerminateBoundary. Backend
`runtime.rs:1261–1306` bounds idempotent control recovery at 30 seconds, while
`:1310` onward gives Wait no idle deadline. Existing captures do not establish
which call blocked, whether recovery could still execute after scope signals,
or why the scheduled recovery expiry did not produce a visible terminal event.
Thus concurrent destruction of cooperating lifetimes is strongly supported;
a specific RPC deadlock or original host-identical workload freeze is not proved.
The original host observation described prompt workload exit; this fixture instead
lost FINAL after freeze, so retain that distinction.

The ordering A/B and manager-stop observations below completed the first proposed
lifetime checks. If a future correctly ordered case stalls, instrument the exact
pending supervisor phase before choosing another repair; do not infer its await
from elapsed time or shorten the safety net.

### Ordered transaction and log-storage contract

The module-generated ordering A/B (`089bb10`) completed the same transaction in
1.484 seconds, compared with 45.409 seconds without ordering. Actual scope Before
included the gateway, conmon lived in the API service cgroup outside its workload
scope, and workload processes retained their scope resource cgroup. TERM and FINAL
were present; supervisor exited zero and runtime one. Attached transport remained
pending and log reader exited one. This validates the isolated lifetime-ordering
mitigation, not full graceful-shutdown acceptance or a production fix. Artifacts:
`/nix/store/v8pqcym3wg41kw1c495bj0vswwgbjww7-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence`.

The restart log assertion was invalid for exact 0.1.2's storage contract.
`openshell-server/src/grpc/policy.rs:4684–4740` queries a tail keyed by sandbox ID,
filtered only by time/source/level, not supervisor instance. Push handling at
`:4741–4780` publishes into `TracingLogBus`; `tracing_bus.rs:193–209` constructs
an empty in-memory map and `:294–307` retains a bounded 2000-event tail. No disk
restore or old-instance retrieval exists in this path. After gateway restart the
query showed new supervision only; missing pre-stop denial is therefore expected
buffer loss across process restart, not evidence that the supervisor failed to
flush it. New supervision is consistent with retained-intent reconciliation;
the exact restart-generation transition was not needed to establish this buffer
contract. No custom database export or restart suppression is proposed.

Delivery and persistence are separate: the matched ordinary prototype now proves
one uniquely identified final supervisor event in GetSandboxLogs plus an actual
accepted-tail RPC acknowledgement while the gateway remains alive. For combined
gateway stop, the cooperative ordered gate requires the same successful local
RPC acknowledgement. Explicit bounded incomplete delivery with an unavailable
peer belongs to a separate negative case, not cooperative acceptance. Do not require
GetSandboxLogs after stopping its process or restart the gateway merely to infer
durability. Its memory tail is not a persistence contract; retained-intent restart
behavior remains unchanged. TERM/FINAL proves workload cleanup, not all telemetry
flush. Explicit administrative client cancellation is correct, not a fabricated
successful workload exit.

### Ordered user-manager teardown

Source `fcda58b` also exercised root guest `systemctl stop user@1000.service`.
It returned zero in 1.518 seconds; the manager was immediately inactive (status
three), TERM/FINAL were present, both exact containers were stopped, and supervisor
exit was zero. Direct post-stop Podman inspection succeeded without PAM or manager
restart. Runtime exit one with the known confirmation error and pending attached
transport remain; the overall fixture deliberately failed that transport assertion.
Artifacts: `/nix/store/h88jbvg6aixwnjzgixlarcvvkfknnns9-vm-test-run-phoenix-shutdown-openshell/final/shutdown-evidence`.

The prior `9ea9723` manager attempt never stopped the manager: the shell wrapper's
background AND-list retained driver stdout until its 120/90-second job timeouts.
A local captured-output comparison confirmed the separated directory-change fix;
that invalid attempt is not shutdown evidence. The corrected run validates prompt
ordered manager teardown, not final-event delivery or successful canonical exit.
No live ordering option, timeout, package pin or production Rust was changed.

### Ordinary-stop repair: validated cancellation and classification prototypes

Preserve upstream's deliberate administrative-stop availability contract.
[PR #3036](https://github.com/NVIDIA/OpenShell/pull/3036), merged as
[`b143500`](https://github.com/NVIDIA/OpenShell/commit/b143500), includes
[`c8967ac`](https://github.com/NVIDIA/OpenShell/commit/c8967ac) to avoid shutdown
exit-report hangs: signal-driven shutdown intentionally skips durable canonical
exit reporting. It predates pinned 0.1.2. Reintroducing that retrying RPC would
undo a maintained fix; canonical exit zero is not promised on administrative stop.

The validation-only [cancellation prototype](tests/shutdown-cancellation/README.md)
retains that report/finalize skip and replaces the success-only terminal wait with
an acknowledged/cancelled outcome. Atomic attachment admission registers owned
writers before cancellation can drain them; a one-second absolute cleanup budget
never waits for a future client or remote channel-close acknowledgement. Normal
acknowledgement remains authoritative, and cancellation reports explicit failure
rather than successful canonical completion. Focused regressions passed 28 tests,
including a deterministic admission race and real in-process SSH status/close.

The real gateway VM passed the explicit terminal-delivery scope from frozen source
`g2k6w78…`, image `bcb8d358…`: ordinary stop took 1.491 seconds, TERM/FINAL arrived,
and attached transport returned 1 with the exact administrative cancellation
message. Supervisor exited 0 and runtime 1; both exact containers stopped without
137. Active workload and nonempty live log stream were established before stop.
Evidence is under `gkqj17q04…-vm-test-run-phoenix-shutdown-openshell`, with the exact
path and structured outcome in the linked fixture README. Gateway relay EOF and
absent captured stream-completion status remain independent limits: final remote
flush and full graceful shutdown did not pass. The binary is version 0.0.0 and the
overlay is not yet a reproducible source package; live shutdown options remain OFF.
Five-second TERM grace, the 45-second fallback and strict full acceptance remain.

The [runtime-classification prototype](tests/shutdown-cancellation/README.md)
retains Explicit versus RecoveryExpired cause inside the existing Terminating and
Terminal states. Recovery claims ownership before awaiting cleanup; explicit
retries cannot replace it. Completed retries still acknowledge either terminal
cause without reclassification. SIGTERM accepts Connected or completed explicit
termination, while awaiting/frozen/incomplete/recovery-loss states retain failure.
Nine focused regressions cover real runtime helpers, idempotency and deterministic
opposite ownership orderings; no wire protocol or timeout was changed.

The actual running static runtime ELF/image binding passed in the gateway VM from
source `c10cjab2…`, runtime image `1f746b8f…`: ordinary stop took 1.478 seconds,
TERM/FINAL arrived, both exact containers exited 0, the old confirmation warning
was absent, and attached client cancellation remained explicit status 1. Exact
patch/build identities and `6l8ar5bm…` structured evidence are in the linked README.
This validates the ordinary administrative classification path only; final log
flush, complete graceful shutdown, a reproducible full source package and live
rollout remain outside the accepted prototype.

The owned log-drain prototype is now implemented and validated with the matched
supervisor image `86c69d84…` and runtime `1f746b8f…`. Frozen source `g85n9g0f…`,
output `cpfb8pfd…`, stopped in 1.436 seconds with both containers exit 0 and
explicit client cancellation 1. Local static outcome appeared exactly once:
accepted-tail acknowledgement true, drops 0, prior-stream uncertainty false,
incomplete None; the fresh live gateway contained the final event exactly once.
The first run's local INFO-marker assertion was invalid because its console
filter defaults to WARN while push independently accepts INFO; the failed receipt
and corrected structured receipt remain preserved in the linked prototype docs.

The handle closes receiver admission, drains batches of at most 50, closes the
request stream and awaits the actual RPC under one absolute one-second budget.
It reports prior loss and incomplete delivery separately. This proves accepted
live-tail publication, not all historical events, restart durability, file-appender
flush or detached SubmitPolicyAnalysis denial-summary aggregation. The latter
emitted a separate failed-flush warning in the first run; it is not covered by the
RPC outcome. Full graceful shutdown and live rollout remain unaccepted.

A bounded official-source reuse check found latest stable
[v0.1.4 (`5a7728c`)](https://github.com/NVIDIA/OpenShell/releases/tag/v0.1.4)
(13 October) and current main still retain the completion skip, non-Connected
SIGTERM classification and unjoined log-push handle. No verified upgrade fix was
found for these paths; the search was not exhaustive. No newer CLI/runtime image
combination was built or tested here, and upgrading would require matched package,
image/protocol and containment compatibility checks rather than a blind pin bump.

Cancellation and runtime classification have isolated prototype proof; owned final
log-push drain remains a proposal. Combined-scope teardown
may remove the gateway before acknowledgement; in that case the expected outcome
is bounded explicit transport failure, not a fabricated durable success. The
original 45-second stall remains unexplained; no production Rust edit, stronger
shutdown guarantee or timeout reduction follows from this proposal.


The Docker-archive rerun passed image imports, TLS/gateway readiness and CLI
status, but failed before workload readiness: CreateSandbox returned its
30-second API timeout. Exact 0.1.2 source places the last completed channel-volume
creation immediately before workload `POST /v5.0.0/libpod/containers/create`.
No workload-create completion was observed. A same-image identity inspection had
completed quickly; cold keep-id/rootfs preparation remains a hypothesis, not a
permission or hardware diagnosis. This did not exercise ordinary shutdown.

The full Phoenix-image remote probe completed baseline create in 0.25 seconds
(exit zero), but keep-id reached 35.034 seconds and status 124. Subsequent guest
container inspections also blocked. This isolates an observed flag-dependent
startup difference; cold UID remapping/storage locking is a hypothesis, not a
proved underlying cause. The next workload should be the small synthetic image
above, preserving keep-id and all runtime/containment parameters rather than
raising deadlines or treating the large-image startup limitation as fixed.

For an isolated comparison, pass `probeCreateOnly = true;` to the same test import.
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

Combined gateway/exact-scope stop reproduced the stall as recorded above;
the matched ordered transaction and manager scopes now pass in 1.452 and 1.483
seconds respectively. Manager inactivity was observed immediately before reads;
no PAM, gateway restart or manager restart was introduced. Both modes preserve
TERM/FINAL, both container exits 0, explicit cancellation 1 and one successful
local RPC acknowledgement, with verified binaries/cgroup ordering/resources.
Exact prototype receipts are linked above. Workload stdout or a closed tail alone never proves final log
flush. Further Rust repairs require an agreed source-backed proposal.

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

Use bounded increments: two build CPUs, 4 GiB guest RAM, 8 GiB dependency-cache
and 25 GiB scratch caps; inspect missing inputs before provisioning. A ready guest
has a five-minute global bound. Preserve the ten-second cooperative target and
45-second safety net; diagnose the first material failure before any repeat.
Current ordinary prototypes pass their named cancellation, classification and
accepted-tail RPC and ordered transaction/manager scopes.
Final repeatable source-built images pass ordinary and ordered-manager scopes
as summarized above. Remaining: actual cold service composition of the implemented/OFF bundle,
pinned-contract peer-loss client observation and controlled rollout; full Phoenix workload startup
remains outside the small representative workload proof. Detached telemetry is a
stated limit; restart durability is outside the upstream memory-tail contract.
