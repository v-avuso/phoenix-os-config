# Shared task history handoff

Technical documentation; user setup and testing: [USER_GUIDE.md](USER_GUIDE.md).

The integration stays in the existing separate-history mode until an explicit
cold handoff publishes readiness. Before readiness, reviewed Native entry points keep their original locations. Do not enable sharing while it owns this conversation.

## Upstream layout

Codex 0.160 supports `sqlite_home` and `CODEX_SQLITE_HOME`; configuration takes
precedence over the environment. `CODEX_HOME` independently owns rollouts and
cross-process writer locks. Both clients must see the same absolute rollout
paths and the same lock directory; SQLite sharing alone is insufficient.

The always-present Native history wrappers and readiness-aware sandbox launcher use `/home/v/.codex` as
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
published root to retry migration: preserve it and recover validated readiness.
Disabling GUI sharing does not reverse this history handoff.

`history-plan.py` optionally inventories only allowlisted path metadata for
retained homes. It reads no database, credential, or rollout contents and changes
nothing. Preserve retained sandbox databases as well as rollouts: sidebar
metadata, attachments, goals, queued work, and paginated history may not be
reconstructible from rollout files.

## Bounded live GUI-sharing trial

Production sharing stays off. Use the registered clean trial checkout
`/home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config`, not the development
checkout with its pending root instructions. The coordinator adds only
`phoenix.agent.gui.sharedState.enable = true;` in `modules/development/ai/default.nix`.
Identity, reservations, shutdown ordering, disruption guard, AI review and the
experimental authorization explanation stay off. A fixture-extended configuration
is packaging evidence, not a deployment source; use this real checkout's normal
metal output rather than another trial-system output.

1. **Prepare before closing apps.** The coordinator evaluates/builds the trial and
   current OFF source, inspects their generated wrappers and records immutable
   paths. Keep a native operator terminal open: this conversation cannot continue
   inside a GUI that must close. Inventory/retain old sandbox-only state using the
   metadata-only planner; do not merge, delete or replace retained containers.

   ```sh
   trial_repo=/home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config
   off_repo=/home/v/repos/code/phoenix-os-config
   off_system="$(nix build --no-write-lock-file --no-link --print-out-paths "git+file://$off_repo#nixosConfigurations.metal.config.system.build.toplevel")"
   trial_system="$(nix build --no-write-lock-file --no-link --print-out-paths "git+file://$trial_repo#nixosConfigurations.metal.config.system.build.toplevel")"
   broker="$(readlink -f /etc/profiles/per-user/v/bin/ai-broker)"
   test -x "$broker"
   ```

   These paths are preparation evidence, not activation permission. Verify
   `$off_system/sw/bin/{codex-history-enable,codex-native,codex-desktop}`
   and their fixed helper/config paths before the cold window; retain `off_system`
   and the verified immutable `broker` path in the terminal. The broker is a Home
   Manager user package, not a system `sw/bin` entry. Do not substitute an old
   unwrapped executable.
2. **Cold handoff in the operator terminal.** Close every Native and
   sandbox Codex GUI/CLI normally, including this chat. Do not force termination.
   With no writers, run each command only after the previous one succeeds:

   ```sh
   "$off_system/sw/bin/codex-history-enable"
   "$off_system/sw/bin/codex-history-enable" --apply
   "$off_system/sw/bin/codex-native" --version
   "$off_system/sw/bin/codex-desktop"
   ```

   The first command is cold preflight; apply backs up known databases and
   publishes readiness before GUI acceptance. Initially inspect only saved chats
   and pins in Native: no new task/model turn. Close Native again before activation.
   If it fails, retain the terminal and captured authenticated broker/controller
   path; stop the trial and preserve history. Native CLI also follows readiness
   and can fail closed if published history is damaged. Do not open an old app
   against stale databases.
3. **Temporary authenticated activation.** From that native terminal, use the
   existing immutable deployment boundary; never directly invoke
   `switch-to-configuration` on the packaging build:

   ```sh
   "$broker" --task gui-sharing-trial --reason 'Temporarily validate shared GUI state and graceful switching' -- phoenix-test --worktree "$trial_repo"
   active_trial="$(readlink -f /run/current-system)"
   ```

   Stop on any failure; do not run the second line or bypass preflight/authentication.
   The helper's successful result supplies the actual frozen source/closure;
   verify `active_trial` matches that reported closure. It can differ from the
   earlier Git-flake packaging build. `test` leaves the persistent boot profile
   unchanged; no switch/boot action is part of this trial.
4. **Acceptance, one GUI at a time.** Use the activated reviewed Native/sandbox
   desktop entries. Verify same-variant restore/new-window, existing chat/project
   pins and saved chats, Keep current, then Close and switch with upstream active-work
   cancellation still honored. Continue one existing chat in sandbox and then
   Native; verify the newly saved continuation and pins in both. No extra sign-in,
   force close, running-command transfer or sandbox-only history merger is expected.
   For bounded fallback evidence, the coordinator may invoke the built `gui-client.py`
   with its exact immutable Python/script/version arguments against a fresh private
   directory's nonexistent socket, then check Native independently. This is a
   fail-closed transport probe, not proof of a real OpenShell outage. Do not stop
   the shared gateway merely to manufacture a failure.
5. **Recover OFF without losing trial history.** Close all Codex GUIs/CLIs normally.
   Restore the trial checkout's sole setting to OFF and use the same broker →
   `phoenix-test --worktree "$trial_repo"` route with a recovery reason, or deploy
   the reviewed unchanged main OFF source. Verify the returned active closure,
   then reopen its reviewed Native wrapper and check the saved continuation.
   Keep `history/ready.json`, shared SQLite plus WAL/SHM, and Native rollout/lock
   directories intact. OFF Native GUI/CLI still invoke `history-runtime.py`, which
   selects shared SQLite whenever readiness exists; OFF removes GUI sharing and
   its lifetime exclusion, not shared-history routing. Use only one GUI during
   recovery. Original Native databases are pre-handoff snapshots and become stale
   after shared writes: never restore them over the shared store, delete readiness,
   or rerun `--apply`. An interrupted unpublished staging tree alone may use the
   cold `--recover-staging` helper. Repairing published readiness or reversing the
   history layout needs separate review; there is no automatic reverse merger.

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

Bounded source evidence in exact 0.160: `core/src/config/mod.rs` resolves SQLite
precedence; `state/src/sqlite.rs` defines six database names;
`rollout/src/writer_lock.rs` coordinates writers under `CODEX_HOME`;
`rollout/src/state_db.rs` gates backfill; `app-server-protocol/src/protocol/v2/thread.rs`
defines explicit-path resume; `thread-store/src/local/mod.rs` tests explicit-path
resume against a stale SQLite path.


## Shared GUI gate and disposable acceptance

`phoenix.agent.gui.sharedState.enable` is default off. Its host GUI guard holds
an exclusive cross-variant lock plus the shared history lifecycle lock; it
validates readiness before launching either frontend. Native executable,
session-restoration and desktop/new-window entry points use the same wrapped
package. Sandboxed entry points use the same guard before their private-profile
launcher. Direct old/unwrapped executables remain outside this guarantee.
The prepared owner adapter restores same-variant windows, uses the existing
new-window callback, and forwards one bounded Codex link to the exact pinned
second-instance callback. Cross-variant switching offers Keep current or ordinary
Close and switch; upstream active-work cancellation remains authoritative.
Installed/live GUI acceptance remains pending; see [limits and usage](README.md#shared-desktop-state-opt-in-gui-acceptance-pending).

`tests/agent-gui-state.py` checks readiness, exclusion, lock retention despite
child FD closure, failure cleanup and synthetic atomic pin replacement. The
optional `tests/agent-history-0160.py --bwrap /absolute/bwrap --codex /absolute/codex`
uses installed 0.160 app-server in network-isolated disposable namespaces. It
reads/resumes a synthetic upstream-format rollout from native and private-parent
worker views, creates a persisted worker fork and reads/resumes it from a fresh
native view. It requests no model turn and reaps all processes. This establishes
local format/path compatibility, not actual OpenShell, retained auth or GUI/model
acceptance. A representative real trial must check existing and newly saved chats,
pins, permitted workspace resume, native fallback with OpenShell unavailable, and
contained CLI denial of native credentials/personal files before enabling daily use.
