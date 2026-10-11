# Testing reservation engine preparation

`reservations.py` is **not enabled or integrated**. It supplies local state and
execution exclusion for future authenticated deployment/admin adapters; it adds
no socket, daemon, executable dispatch, or OS mutation.

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
