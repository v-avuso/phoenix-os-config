# Exclusive testing reservations

`phoenix.agent.reservations.enable` defaults to **false**. When enabled, management
uses the existing admin broker, and test/switch/boot plus configured mapped fixed
admin operations require a private task capability. Build/dry-build remain independent.
Engine/adapter fixtures and the packaged broker/systemd lifetime VM pass.
Native Polkit and broader live acceptance remain pending.
Keep this experimental feature off on the daily driver.

The engine supplies SQLite state and kernel flock exclusion; the management
adapter adds no daemon, arbitrary executable dispatch, or OS mutation.

## Ownership and API

A server constructs `Engine` with an absolute private state directory and a
server-owned baseline reader. Production defaults require root ownership, private
state files, no symlinks, and root-owned non-writable directory ancestry. The
explicit `owner_uid`, boot-ID and monotonic-clock constructor hooks permit
unprivileged disposable fixtures; adapters must never populate them from callers.
SQLite uses short `BEGIN IMMEDIATE` transactions with a two-second busy timeout.
Python's standard SQLite and flock support cover persistence and kernel exclusion;
custom code owns only capability, FIFO, baseline and expiry policy. This avoids a
second coordination service while retaining the existing broker architecture.

The exact qualified mapping defaults to `deployment.test`, `switch`, `boot`,
`update`, `override` and `rollback`, all sharing `system-testing` (the qualified
prefix applies to each name). Build is excluded. Server configuration may supply
other exact names/resources; callers cannot choose a group, executable, or path.

- `acquire(uid, task, command, expected_baseline)` returns a random 256-bit capability
  once, generation, and owned/queued state. Only its SHA-256 hash is stored.
- `poll(uid, generation, capability)` is quick; it refreshes queued liveness and
  promotes only the first live ticket. Waiting callers poll within 30 seconds.
- `cancel`, `renew`, and `release` require the same UID, generation and capability.
  Release accepts an owner's changed baseline. Status contains no capabilities.
- `force_unlock(expected_generation, reason)` is an **authenticated operator-only
  adapter interface**. It revokes that resource's owner and queue and stores only
  a bounded reason hash; it neither authenticates nor grants any root action.
- `operation(...)` checks ownership and server baseline at mutation entry and holds
  the resource flock through the caller's entire mutation and failure rollback.
  Its yielded `advance_baseline()` follows server-proven successful own mutation.

Lease defaults: 900 seconds; renew at most 3600 seconds; total ownership at most
14400 seconds. Queue deadline at most 3600 seconds, liveness 30 seconds; global
queue default 64 and per-UID default 4. Bounds may be reduced. Same-boot engine
restart retains state; a changed boot ID invalidates authority without resetting
monotonic generations. Baseline changes require stale queued requests to cancel
and resubmit, rather than silently refreshing approval.

## Execution lifetime and integration limits

Expiration, release and operator revocation revoke future entry, never kill a
process or switch/rollback the OS. A held flock independently blocks later entry,
even when a newer owner has acquired a reservation. Operation records are bounded
per resource and aid management, but an orphan record is advisory; the kernel
flock determines execution exclusion. The next successful entry replaces it.

`Operation.run_child` accepts server-selected argv, requires a bounded timeout,
passes the gate descriptor and waits/reaps the foreground child. Keep rollback
inside the same operation context. On parent death an explicitly inherited
open descriptor retains the gate. **A parent flock alone does not protect detached
activation descendants.** Adapters must prove descriptor propagation and
child lifetime for their exact activation path, or use a fixed foreground helper
that retains it until all mutation and rollback activity completes. The engine
cannot infer detached descendant completion or authenticate operator recovery.

Acquire before the testing workflow, retain the capability in a caller-private
file, validate it for each mutation, renew while needed and release at completion.
Capabilities must not appear in logs, branch labels or argv. Management
uses the existing admin socket/fixed authenticated operator helper because
the synchronous deployment socket can be occupied during builds and reviews.

Run disposable tests with `python3 tests/reservations.py` from this directory.
These prove engine behavior with real SQLite/flock and controlled identity/time;
they do not prove packaged integration, Polkit authentication or live activation.

## Management (opt-in)

Exact qualified commands map to resources through `reservations.mapping`; clients
cannot select resources or execution. Config bounds may be reduced, except queued
liveness must remain 25..30 seconds to cover a broker diagnostic (up to 10 seconds),
15-second socket timeout and a short polling margin. The broker uses root-owned
`/var/lib/phoenix-reservations` (0700), database/gates 0600. The explicit immutable
`engine` and `adapter` store paths avoid sibling-import assumptions.

```sh
phoenix-reservation --capability-file /absolute/private/task-cap.json --task task-id --command deployment.test --wait 60 acquire
phoenix-reservation --capability-file /absolute/private/task-cap.json --seconds 900 renew
phoenix-reservation --capability-file /absolute/private/task-cap.json release
phoenix-reservation status
```

Use `--operator` on the native host for the fixed Polkit helper. Under protected
identity the operator does not gain access to the agent-only admin socket. Each
high-level operator command authenticates freshly; acquisition and its bounded
wait use one helper lifetime (server status, acquire, then quick poll/cancel).
Agent acquisition polls client-side; no broker handler sleeps. Poll queued tickets
within their liveness window. Renew owned tickets well before expiry (at least
60 seconds for ordinary callers; allow additional human authentication time for
operator renew). Reduced leases require correspondingly earlier renewal.

Acquisition requires a new caller-owned file; existing files are never overwritten.
Capabilities travel only through stdin/socket/private stdout and the explicit
caller-owned regular 0600 file, with no symlink or multiple-link reads/writes.
They never appear in argv or broker journal. Release/cancel leaves the file for
caller-controlled cleanup; it then contains a stale capability. Failure after
acquisition may leave a ticket; queued liveness and bounded leases recover it.

```sh
phoenix-reservation --operator --generation 123 --reason 'crashed testing owner' force-unlock
```

Recovery uses a distinct immutable helper and fresh critical Polkit action. Normal
helper requests cannot force unlock; recovery helper requests cannot perform
ordinary management. The client displays generation and SHA-256 reason before
authentication; the Polkit dialog describes the fixed recovery effect and does
not promise to display dynamic stdin details. Server recovery checks the exact
current owner generation, revokes its queue and stores a reason hash. It does not
stop running work, remove the kernel execution gate or activate/roll back anything.

The server derives baseline JSON from resolved activated source, current runtime
closure, system profile and profile source. Missing provenance is unsupported;
changed baseline between status/acquisition explicitly requires reacquisition.
`status` returns the canonical baseline string, mapping, bounds and secret-free
owners/queue/operations. The wire envelope is `{"reservation": REQUEST}`; kernel
SO_PEERCRED selects agent UID. The root-only fixed helper adds configured
`operator_uid`; the broker never accepts a caller-selected agent UID.

Request fields (no extras): `status`: operation; `acquire`: operation/task/command/
baseline; `poll`, `cancel`, `release`: operation/generation/capability; `renew` adds
seconds; operator-only `force-unlock`: operation/generation/reason. The helper's
high-level acquire takes operation/task/command/wait instead of baseline, captures
it server-side and composes the bounded wait. All broker requests return quickly;
success uses `ok=true,reservation=RESULT`, denial uses `ok=false,error=...`.

Run `python3 tests/reservation-management.py` here alongside engine fixtures.
These exercise real Unix sockets, SQLite and FIFO with explicitly fake OS
baseline/root/Polkit identities. Nix evaluation verifies packaging; native GUI
Polkit, protected identity/OpenShell and live VM/systemd activation/runtime
acceptance remain pending. No live service or account is used.

## Deployment and runtime workflow

Acquire before requesting activation, renew during a long build/review or runtime
validation, and release only when the task finishes. Management uses the separate
admin socket, so deployment's synchronous build/review does not block renewal.
A successful activation advances that same owner's baseline and leaves the lease
owned for runtime validation; it does not automatically release it.

```sh
phoenix-reservation acquire --task TASK --command deployment.test --capability-file /private/task.json --wait 60
ai-broker --reason "authorized task purpose" -- phoenix-test --worktree /absolute/registered/worktree --reservation-file /private/task.json
phoenix-reservation renew --capability-file /private/task.json --seconds 900
# Complete runtime validation first.
phoenix-reservation release --capability-file /private/task.json
```

Native operators add `--operator` when acquiring/managing a lease. Disabled AI
still requires normal native deployment Polkit authentication. Agent sockets keep
their configured kernel UID boundary. The deployment client reads only an explicit
caller-owned regular 0600 file with one link and no symlink; only generation and
capability cross the private socket/stdin, never argv, logs, or model input.

A failed AI review records its frozen source/closure/nonce and original caller
metadata without a bearer. An explicit critical override requires a fresh operator
reservation and existing critical Polkit authentication:

```sh
phoenix-reservation --operator acquire --task RECOVERY --command deployment.override --capability-file /private/recovery.json
phoenix-deploy-review --security-override PENDING_NONCE --reservation-file /private/recovery.json
```

The authenticated operator's lease replaces no agent authority silently. The exact
pending source/closure/action and current base/profile checks remain mandatory.
If the original agent still owns the resource, wait for its release or use explicit
operator force recovery before acquiring. Changed baselines require a fresh request.

Routine deterministic updates continue making zero AI calls. After publisher,
source, build and closure checks, the server acquires a bounded root-owned update
lease immediately before staging boot. It cancels a queued ticket and reports busy
rather than waiting or generating human authentication prompts; normal next-run
retry remains the existing updater's responsibility. The actual service releases
this internal lease after completion. Callers cannot supply a lease for `update`.

## Activation lifetime and recovery

Both actual activation entry points (reservations ON and OFF) also hold the fixed
root-owned `/var/lib/phoenix-deploy/activation.lock` through mutation and rollback.
It is distinct from controller build/review serialization and never renamed with
resource mappings. This prevents a new configuration changing the resource name
or disabling reservations from overlapping a still-running guarded old helper.
Foreground children inherit this guard too. It does not retroactively guard an
already-installed older helper lacking the lock: the first live acceptance requires
an explicitly quiescent activation boundary. Never reset or rename a live guard.

The actual transient activation service opens a fixed root-owned 0600 envelope
from a private root 0700 spool; unit argv contains only its random nonce. It owns
the resource gate throughout mutation and failure rollback. Foreground children
inherit the gate; timeout/cancellation kills and reaps only that operation's child
process group before recovery. The helper independently owns the gate, including
when the deployment controller disappears. Expiry/release/revocation does not free
an active mutation gate, activate another system, or trigger speculative rollback.
Successful work after owner expiry/revocation remains successful, but cannot
refresh another owner; a contender with the old baseline must cancel/reacquire.

Immutable spool GC roots keep source, candidate closure and previous runtime
available after controller death. A completing helper removes only its own nonce
record and generated roots. Orphans before service dispatch are deliberately
retained; at 64 envelope records, new activation refuses with
`spool-recovery-required`. An operator must inspect matching
`phoenix-deploy-activation-NONCE` service state and ensure no activation/rollback
is running before deleting only that reviewed nonce's `.json`, `.source`,
`.closure`, and `.runtime` entries under `/var/lib/phoenix-deploy/activation`.
Never clear the whole directory or active roots. Forced reservation recovery alone
does not stop a service or remove spool roots.

Optional mappings such as `admin.wakeup-set = "system-testing"` gate only the
existing fixed operation; they add no executable dispatch. Supply its private file
with `phoenix-admin --reservation-file FILE --reason PURPOSE wakeup-set ...`.
Unmapped commands reject unused reservation extras. All deployment actions,
critical override and rollback must share one configured resource.

## Disposable verification

Run `python3 -B modules/development/ai/agent/tests/reservation-deployment.py` with
the existing engine, management, deployment, broker and command fixtures. The
activation fixture runs the actual helper/engine in subprocesses with explicit
root ownership, Nix/store, activation and host baseline stubs. It checks controller
death, expiry/revocation during mutation, rollback exclusion, process-group timeout,
owner baseline advancement/runtime hold, fresh contender baseline and mapped broker
socket rejection. It does not prove live systemd cgroup, graphical Polkit or VM
activation acceptance; those remain the final isolated acceptance window.


## On-demand systemd lifetime acceptance

`tests/reservation-lifetime.nix { pkgs = ...; }` uses locked Nixpkgs'
`testers.runNixOSTest` (two CPUs, 2 GiB, 120-second global bound). It is not a
default check. The actual VM passed from source
`ecd35ed25e419e9f8962353a897c183e200ff6d1`; evidence is in
`/nix/store/cnwjwkjxy1hy0br7l94mnjhn54h69c0y-vm-test-run-phoenix-reservation-lifetime/evidence`. Build from an exact committed Git-flake source,
not the checkout path, then select this factory with that flake's locked pkgs.

The guest supplies synthetic immutable source provenance to its own current
runtime; if its initial system profile is absent, setup points it at that runtime.
A separate immutable candidate closure contains only a fixed recorder executable
and matching provenance. Real `recheck_bound`, root ownership checks, default
Management mapping, activation guard, `activate_reserved`, reservation operation
and inherited-descriptor child runner execute. No baseline/store/identity methods
are mocked. Recorder activation only starts a child, waits for a guest release
marker and records completion; successful recorder execution does not activate
NixOS or update a profile. On unexpected candidate failure, production rollback
may reassert the disposable guest configuration; no host path is involved.

After recorder readiness the driver kills only the submitting `systemd-run`
client. The actual transient service and recorder descendant must survive, reject
a competing activation helper, finish after release and relinquish exclusion.
A separate short `Operation.run_child` timeout must kill a delayed descendant
before it can write after return; subsequent gate entry must succeed. The service
has a 30-second runtime bound/five-second stop bound; captures retain its unit
properties and journals even on failure, excluding capability/config/envelopes.

The actual guest run verified the killed process was the submitting `systemd-run`
client, distinct from the service PID. The real transient helper retained the
activation guard; its competitor reported `mutation-still-running`, and the unit
journal recorded successful deactivation. Descendant completion, timeout cleanup
and subsequent gate reuse assertions passed. The rerun also passed the explicit assertion requiring that exact competitor
rejection reason.
That original recorder-only receipt excludes Polkit, broker SO_PEERCRED admission,
protected identity, real OS activation/rollback and broad reservation workflow
acceptance; the extended packaged-broker receipt below adds kernel-peer evidence. Production
reservations remain OFF; every service/state/profile operation above is guest-only.

## Packaged broker and recovery acceptance

The extended `tests/reservation-lifetime.nix` passed using actual broker/reservation
modules, installed client, kernel peer UIDs and production private state settings.
Evidence: `/nix/store/5340x28qlgfa8hbb5qg90i6y0asd316w-vm-test-run-phoenix-reservation-lifetime/evidence`;
the driver completed in 21.79 seconds with a 180-second global bound.

Two task capabilities acquired owned/queued generations through the broker; an
outsider admitted by socket permissions and a forged operator envelope were denied.
After submitting-client death the recorder retained the activation guard. Management
remained responsive; a real two-second renewed lease expired and promoted task two,
without stopping the recorder, overlapping mutation or triggering rollback. The
promoted task's independently bound competitor still hit the held guard. The exact
installed recovery helper revoked its generation; normal-helper recovery and wrong
operator identity failed. A fresh task then completed recorder activation, retained
its runtime-validation lease, passed the existing child-timeout/gate-reuse checks
and explicitly released. All issued capabilities were absent from the guest journal.

The trial exposed missing dynamic-import dependencies: plain `toString` repository
paths did not retain engine/adapter in the closure. Those files are now individually
packaged and shared by broker/deployment clients; both native and sandbox deployment
client derivation closures retain the adapter. No whole-source dependency was added.
The fixture recreates a consumed competitor envelope with the promoted capability;
it never replaces the active helper's envelope or reuses revoked authority.

A later disruption inspection extension adds independent cases to this same
factory; its current full-gate status is described in [disruption evidence](disruption.md#partial-isolated-systemd-evidence).
The reservation receipt above remains the passed checkpoint.

Activation remains a recorder and provenance synthetic. The real immutable operator
helper and root socket run, but `PKEXEC_UID` is explicitly doubled: native Polkit
session authentication/dialogs are not proved. This is not real NixOS activation,
protected OpenShell, model or broad host workflow acceptance. Production
reservations remain OFF.
