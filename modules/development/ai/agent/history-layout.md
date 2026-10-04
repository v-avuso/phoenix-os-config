# Shared task history handoff

The integration stays in the existing separate-history mode until an explicit
cold handoff publishes readiness. The running Native app keeps its current data
locations. Do not enable sharing while it owns this conversation.

## Upstream layout

Codex 0.159 supports `sqlite_home` and `CODEX_SQLITE_HOME`; configuration takes
precedence over the environment. `CODEX_HOME` independently owns rollouts and
cross-process writer locks. Both clients must see the same absolute rollout
paths and the same lock directory; SQLite sharing alone is insufficient.

The conditional Native wrappers and sandbox launcher use `/home/v/.codex` as
`CODEX_HOME` and a credential-free SQLite directory under
`~/.local/state/phoenix-openshell/history`. The sandbox's canonical `.codex`
parent remains private image state. Only Native `sessions`, `archived_sessions`,
`thread-writer-locks`, and shared SQLite are bound. Native authentication,
configuration, desktop/browser profiles, and OAuth refresh ownership stay
separate. Both sandbox transports receive the same location settings.

`history-runtime.py` validates the exact marker locations, known database names,
required database/rollout paths, and rejects Native `sqlite_home` overrides.
Missing/invalid readiness after publication fails closed instead of starting
blank history. Reviewed Native clients and sandbox transports have a host parent
holding the shared lifecycle flock; runtime descriptor sanitation cannot drop it.
Cold enable/recovery require the exclusive nonblocking lock. A staging directory
also blocks reviewed entry points after an interrupted handoff.

## Explicit cold handoff

1. Exit every Native and sandbox Codex process in a coordinated handoff.
   `codex-history-enable` defaults to a database-read-only cold preflight and refuses
   same-user Codex processes, symlinked paths, unknown SQLite families, conflicting
   targets, missing history directories, and configuration overrides.
2. Run `codex-history-enable --apply` only while clients are stopped. Python's
   maintained SQLite backup API reads each allowlisted Native database through
   a read-only URI, including its committed WAL data. The helper verifies the
   backups, flushes the prepared tree, and atomically publishes the directory
   with its readiness marker. It rechecks processes before each backup and before
   publication. Original Native databases remain intact as recovery; no database
   schemas or rows are merged. Failed preparation cleans only its own staging
   tree and leaves source databases intact.
3. Restart both clients and verify listing, resume, archive/unarchive, and
   same-task writer exclusion. The new sandbox revision retains the old container
   unchanged. Existing Native tasks and all future sandbox tasks use the shared
   store. Old sandbox tasks remain in their retained containers; they are not
   silently imported or claimed available in the shared list.

The process check and lifecycle lock cover the reviewed launchers; they cannot
seal arbitrary direct invocations of an old executable. Keep clients stopped
through publication. A crash can leave `history.preparing`; it deliberately
blocks new clients until an administrator reviews/removes that unpublished
staging directory. `codex-history-enable --recover-staging` performs that recovery
only while cold, validates owned private staging directories and pinned filenames,
and removes only unpublished staging. Sources remain unchanged. Do not delete a
published root to retry migration; recover
its readiness or deliberately restore the separate-history configuration.

`history-plan.py` optionally inventories only allowlisted path metadata for
retained homes. It reads no database, credential, or rollout contents and changes
nothing. Preserve retained sandbox databases as well as rollouts: sidebar
metadata, attachments, goals, queued work, and paginated history may not be
reconstructible from rollout files.

## Why upstream, not an importer

No maintained database merge CLI exists in the pinned version. Startup backfill
returns immediately once the existing database's `backfill_state` is complete,
so adding rollouts does not guarantee discovery. A custom SQL merger would own
schema evolution, duplicate identities, paginated history, side tables, and crash
recovery. This bounded integration uses upstream location settings and SQLite's
backup operation. Legacy sandbox migration remains a separate reviewed recovery
operation; revisit when a maintained migration/export API exists or a concrete
task requires recovery.

Project-level `sqlite_home` overrides are unsupported in this bounded iteration:
upstream configuration can outrank the environment. Native home/profile settings
and explicit CLI overrides are rejected; project settings need separate review
before enabling sharing.

Bounded source evidence in exact 0.159: `core/src/config/mod.rs` resolves SQLite
precedence; `state/src/sqlite.rs` defines six database names;
`rollout/src/writer_lock.rs` coordinates writers under `CODEX_HOME`;
`rollout/src/state_db.rs` gates backfill; `app-server-protocol/src/protocol/v2/thread.rs`
defines explicit-path resume; `thread-store/src/local/mod.rs` tests explicit-path
resume against a stale SQLite path.
