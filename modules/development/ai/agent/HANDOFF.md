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
  `/nix/store/4c7agrmk05mpidgan14xcig0vgjnzv94-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
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
- Diagnostic repair `6301d33` was authenticated and temporarily installed.
  It adds fixed stderr-only OS detail with unchanged RPC error frames; all 14
  focused HTTP fixtures passed and the trial system built successfully.
- The next real `pwd` GUI trial failed before tool execution with
  `workspace routing discovery failed`. New stderr included remote-disconnected;
  this alone did not identify the cause. Supported `openshell logs` then showed
  22 warnings denying the exact Codex kernel executable
  `/nix/store/np442w66n363ydl8xp92lzkmdj5bih4a-codex-0.160.0/bin/.codex-wrapped`
  in both `codex` and `_provider_phoenix_codex`. Their declarations name the
  outer `bin/codex` wrapper instead. This is concrete network-policy identity
  mismatch evidence; correcting it does not yet prove the full GUI workflow.
  No Python executable denial appeared in that bounded warning window.
- Executable repair `a1d9c80` was built and authenticated for temporary activation.
  Both policy owners now use one exact package-bound identity, guarded by a build
  check. L7 inspection, destination scopes and credentials remain unchanged.
- The next GUI/model turn reached `pwd`, but inner Bubblewrap failed to create a
  namespace. OpenShell 0.1.2 intentionally denies CLONE_NEWUSER. Do not weaken
  host sysctls, outer seccomp or accept rejected L4 credential proposals.
- The operator selected **Custom (config.toml)** in Sandbox, and the next actual
  `pwd` tool call succeeded with `/home/v/repos/code/phoenix-os-config`. The desktop
  Custom option uses backend configuration: the existing worker config delegates
  containment to OpenShell. Approve for me overrides it with workspace-write and
  recreates the incompatible inner sandbox. No RPC policy rewriting was added.
  Ordinary OpenShell-permitted commands do not trigger Codex command Auto-review;
  eligible approval requests and the separate privileged boundary remain distinct.
- Operator returned to Native; current supplied permission context is workspace-write
  with auto_review. Chat continuation and one shell command are demonstrated,
  not all filesystem/network denials. Check defaults/persistence and scoped denied
  access with nonsecret fixtures before declaring everyday acceptance complete.
- Timezone repair `15ac5e1` was built and temporarily installed through native
  authentication. The updated worker returned `CEST +0200` through the supported
  sandbox-exec launcher. GUI timezone settings are packaged; visual confirmation
  awaits the next normal GUI launch. No clock or Native configuration changed.
- A nonsecret live fixture through sandbox-exec confirmed repository README
  readability while a temporary host-only /tmp canary was invisible; probe exited
  zero and the host fixture was removed. This is a focused mount-isolation check,
  not exhaustive personal-data, credential, egress or broker acceptance.
- Automatic permission selection is now implemented in an immutable Sandbox-only
  desktop adapter (`76e7871`, corrected by `f8b93cc`). The full trial built and
  authenticated temporary installation succeeded; real GUI acceptance remains. It namespaces
  all four identified permission preference keys and defaults absent ordinary
  workspace/new-chat choices to Custom. Explicit selections, read-only and named/
  unknown profiles retain their semantics. Native's package/settings are untouched.
  Current chat policy is checked before stale saved host preferences; added cross-
  product tests cover saved Custom/Auto/Full access against restrictive/unknown
  current profiles and modes. The initial build was temporarily installed before
  this final precedence defect was caught, then replaced before any requested GUI
  trial. Exact pinned bundle guards and focused resolver/reconciliation fixtures cover the
  source seams; they do not establish effective Native permissions after a shared
  chat resumes. Requirements-only filtering was rejected because Codex 0.160 requires
  explicit allowed-mode lists to include read-only, retaining the nested-sandbox gap.
  No managed requirements or RPC policy rewriting was added.
- Actual automatic-mode acceptance FAILED after the corrected installation:
  Native appeared to change from Approve for me to the least permissive option;
  operator restored Approve for me, closed Native, then opened Sandbox. Sandbox
  still showed Approve for me instead of Custom. No Sandbox command was run;
  operator returned to Native. The apparent Native mode change has no established
  cause. Read-only inspection confirmed the installed Sandbox bundle contains the
  patch and Native's bundle retains the original permission resolver. The four
  Sandbox preference keys were absent; Native's restored mode and selection were
  `guardian-approvals`. The pinned decoder maps workspace-write/on-request with
  auto_review to that mode, labelled Approve for me. The adapter mistakenly treated
  it as a distinct explicit policy and preserved it before selecting Custom. The
  next correction handles ordinary workspace guardian mode like auto, while keeping
  restrictive profiles and explicit Sandbox selections. Tests must start from the
  actual decoder and cover outgoing Custom policy, not only an assumed mode name.
  This explains Sandbox's failed default, not Native's earlier transient display.
  Correction `6c1847c` passed decoder-to-outgoing-request characterization and the
  full system build; authenticated temporary deployment succeeded and the runtime
  path matches the closure above. Repeat real GUI acceptance is still pending;
  the persistent next-boot profile remains unchanged.
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

## Shutdown investigation checkpoint

Read-only refresh against exact v0.1.2 release source confirmed supervisor/driver
hashes. `supervisor/lib.rs:1159-1181` performs signal, five-second wait, terminate,
a second wait, then boundary termination. The second wait at 1167 can prevent
boundary termination at 1176: `sandbox-backend/runtime.rs:1314-1337` has no idle
timeout. Control RPCs separately have 30-second deadlines (46, 506-523,
1261-1306). Terminal output drain is bounded to two seconds
(`sandbox/main_session.rs:211,489-505`); log push is detached
(`supervisor/main.rs:328-342`), so an awaited log-flush stall is not established.
Podman driver stops supervisor before workload (`driver.rs:1400-1435`); gateway
compute cleanup precedes final session cleanup (`gateway/lib.rs:997-1013`).
These are candidate blocking paths, not identification of the observed stall.

Host-level read-only inspection confirmed `/dev/kvm` exists; its absence inside
the command sandbox was not evidence of host absence. No installed/cached VM
runner was found. The repository has no maintained disposable NixOS test-driver
fixture; its VMware host configuration is not suitable. Reuse the NixOS driver or
a prepared disposable guest, but budget the new guest/TLS/isolated gateway and
Podman/image setup as a separate integration step. Follow
[shutdown-acceptance.md](shutdown-acceptance.md): active workload plus policy log
stream; compare ordinary stop against combined gateway/scope shutdown. Cooperative
pass is under ten seconds; retain the 45-second safety net and a 50-second harness
stop. Stop after the first reproduced stall and identify entered/completed phases
before proposing a Rust cleanup change. No production stop or shutdown code change
was performed; ordering remains experimental and disabled.

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
2. Finish the checked automatic-mode trial: install through the authenticated
   deployment boundary, open Sandbox normally, verify Custom without manual choice,
   resume this chat and run `pwd`; return to Native and verify Approve for me with
   workspace-write/auto_review. Preserve explicit restrictive choices. Read
   [the integration decision](README.md#backend-integration-choice) before replacing
   transport; the current path already uses SSH.
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
