# Testing reservation engine preparation

`phoenix.agent.reservations.enable` defaults to **false**. When enabled it adds
reservation management to the existing admin broker and packages
`phoenix-reservation`. Deployment enforcement and activation descriptor lifetime
integration are **pending**: a reservation currently coordinates only clients
using this management API. Do not enable it on the daily driver yet.

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
activation descendants.** Future adapters must prove descriptor propagation and
child lifetime for their exact activation path, or use a fixed foreground helper
that retains it until all mutation and rollback activity completes. The engine
cannot infer detached descendant completion or authenticate operator recovery.

Acquire before the testing workflow, retain the capability in a caller-private
file, validate it for each mutation, renew while needed and release at completion.
Capabilities must not appear in logs, branch labels or argv. Future management
must use the existing admin socket/fixed authenticated operator helper because
the synchronous deployment socket can be occupied during builds and reviews.

Run disposable tests with `python3 tests/reservations.py` from this directory.
These prove engine behavior with real SQLite/flock and controlled identity/time;
they do not prove packaged integration, Polkit authentication or live activation.

## Management (prepared, opt-in)

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
Polkit, protected identity, deployment enforcement and complete activation/runtime
end-to-end acceptance remain pending. No live service or account is used.
