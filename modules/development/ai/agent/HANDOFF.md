# Technical recovery checkpoint

Recorded 2026-10-15. This is task context, not authorization or proof of a later
installation. Recheck actual source/runtime state before continuing deployment.
For minimal operator steps, use [USER_GUIDE.md](USER_GUIDE.md); technical ownership,
commands and limits remain in the [module README](README.md),
[history handoff](history-layout.md), [authorization](authorization/README.md) and
[operating guide](../../../../docs/AGENT_SANDBOX.md).

## Intentions and operator constraints

- Make sandbox GUI plus OpenShell CLI the everyday defaults, with native GUI and
  native CLI as independent repair/lifeline paths. Containment must not remove them.
- Share saved chats, projects and pins with low switching friction. One active GUI
  is acceptable when Keep current / graceful Close and switch preserves work;
  do not force termination or transfer running commands between backends.
- Keep the broker narrow and reasons nonsecret. Optional security review inspects
  deployment diffs; routine updates stay deterministic with zero AI. Authentication,
  immutable source binding and recovery remain independent of AI review.
- Experimental controls stay off until their real workflow acceptance. The user
  stays in Native until **this existing chat** is present and resumable in Sandbox;
  do not ask them to start a fresh chat or abandon this context.

## Recorded installed state and pending source

- Persistent repair source `60d5361` includes maintenance-lock repair `70fb232`
  and config-link repair `1b27eec`. Boot profile remains
  `/nix/store/dql2y6v7zhsszffw8gv6fw7zqa8rk18c-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
- The 2026-10-15 cold handoff published readiness and the sharing-ON trial was
  temporarily activated. Runtime is
  `/nix/store/sinx1jn6la4ghy3nf0i52j3kd5pfg76p-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
  The operator confirmed this exact conversation resumed and a reply was sent
  in Sandbox, then returned to Native. Do not rerun migration or restore stale
  Native originals over the shared store. Boot profile is still sharing OFF.
- Deployment audit completed approximately 65 seconds after readiness; the
  activation service took 3.559 seconds. Foreground launch waits for GUI exit;
  terminal lifetime is not deployment duration.
- Around 10:22:02 CEST, sandbox HTTPS diagnostics recorded two
  `backend-request/local-io` and one `routing-discovery/local-io` failures.
  They lack request correlation and underlying OS detail: association with the
  reported "Error running remote" is plausible, not proven. No root cause is
  established. Preserve credentials; these records do not establish expiry.
- Pending diagnostic repair adds fixed stderr-only OS failure detail (for example
  connection reset or denied permission), with unchanged RPC error frames. All
  14 focused HTTP fixtures pass; this repair is not installed or a root-cause fix.
  Next step: build an isolated sharing-ON source, authenticate temporary deployment
  when the operator returns, then reproduce once and inspect the safe detail.
- Committed repair `70fb232` accepts Codex 0.160's exact `.sqlite-maintenance.lock` as
  regular, non-symlink coordination state in both Native preflight and shared
  runtime status. It is not a database and is never copied during migration.
  All 17 synthetic history tests passed. Coordinator also ran the actual patched
  `inspect_layout` successfully against the real Native config/path layout, without
  migration or a writer-gate bypass. Main and trial builds passed; the installed
  helper's complete read-only layout inspection passed too.
- `inspect_layout(config)` runs the same read-only config/layout checks while GUI
  writers exist. Its success is not cold approval or database-integrity evidence.
  Actual cold preflight/apply still reject running writers.
- Existing old Sandbox chats/containers are retained separately, not merged or
  silently imported into the Native/shared baseline.

## Worktrees and preservation

| Purpose | Checkout | State to preserve |
| --- | --- | --- |
| Main/integration | `/home/v/repos/code/phoenix-os-config` | Production sharing OFF |
| Feature | `/home/v/.codex/worktrees/deployment-security-review/phoenix-os-config` | Repair committed; root `AGENTS.md` is an unrelated uncommitted operator-review draft |
| Trial (`codex/gui-sharing-trial`) | `/home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config` | Repair merged; sole uncommitted sharing-ON flag remains |

Do not include the root instructions draft in a deployment snapshot, reset it,
stash it or silently copy it into the clean trial source. Only the trial enables
sharing; identity, reservations, shutdown ordering, disruption guard, security
review and authorization explanation remain off.

## Resume order

1. Repair installation and the cold handoff are complete. Preserve published
   readiness and shared writes; do not repeat one-time setup.
2. Diagnose the reported remote error with bounded secret-safe diagnostics.
   Read [the integration decision](README.md#backend-integration-choice) before
   adding adapters or replacing transport. The current path already uses SSH.
3. Any code repair needs focused checks/build and authenticated temporary
   installation before the next live trial. The current GUI remains untouched
   until an agreed switch; use broker → `phoenix-test`, not direct activation
   of a packaging-only closure.
4. Verify existing and archived chats/pins, resume this chat and save a reply,
   exercise same-variant restore/new-window plus Keep/Close choices, and confirm
   the reply survives Sandbox → Native continuation. No extra sign-in is expected.
   Native fallback needs real acceptance; a private failed-transport probe is
   bounded evidence, not proof of a complete OpenShell outage.
5. Fix scoped failures or disable the experiment through the same deployment
   boundary. Preserve published readiness, shared databases/WAL and rollout state.
   Disabling GUI sharing retains shared-history routing. Native originals become
   stale after shared writes: never restore them over the shared store, delete
   readiness, rerun apply, or merge browser/profile databases to repair a failure.

No browser login, credential migration or general profile/database merger is part
of shared-history setup. On failure, stop and report the terminal error; do not repeat
migration automatically. Damaged published history may block both reviewed Native
GUI and CLI; retain the operator terminal and authenticated controller route.

## Evidence limits and separate unfinished work

- Unit/disposable fixtures demonstrate bounded behavior, not installed operation.
  Package builds demonstrate packaging, not activation or user workflow success.
  This exact shared conversation was resumed in Sandbox; broad history and reliable
  tool/model workflow acceptance remain pending.
- This chat is indexed in Native and its conversation file exists in the planned
  history mounts. Exact Codex 0.160 read/resume of its private backup passed in a
  disposable network-isolated namespace, with no credentials or model turn.
  The resume response was 11,771,928 bytes, below the relay's 16 MiB frame cap.
  Original history was unchanged and processes were reaped. This proves backup
  format compatibility, not the live OpenShell/GUI/workspace workflow or future sizes.
- Protected identity, reservations, disruption protection and the full optional
  security-review workflow have separate unfinished live acceptance. The generic
  authorization explanation remains experimental/off; critical exact-pending
  override handling is a separate flow.
- On 2026-10-06 at 08:32, OpenShell 0.1.2 shutdown hit the 45-second supervisor
  timeout and SIGKILL. The exact stall is unknown. Only read-only investigation/
  proposal work exists; no fix is established and timeout shortening is not a fix.
- Music, Kando and other side tasks are delegated elsewhere and outside this scope.
  The [2026-10-04 acceptance report](../../../../docs/AGENT_SANDBOX_ACCEPTANCE.md)
  preserves historical evidence; its claims are not current acceptance of this trial.

## Private conversation backup

Coordinator recorded a point-in-time backup at:
`/home/v/.local/state/phoenix-agent-backups/01a0fe72-f176-7fb2-b116-94a49cbd4633/20261015T080753.079531Z`.
It contains `conversation.jsonl` and `manifest.json` with SHA256 metadata and
20,429 complete JSONL records. No auth, config or database files were copied.

This is not guaranteed provider prompt-cache preservation or an automatic import
into either app. Keep it private, outside Git and Nix sources; do not paste or copy
its conversation contents into this document. Its contents were not read for this
checkpoint. Resume the existing chat through the tested app/history path first;
any backup-based recovery/import needs a separate supported, reviewed procedure.
