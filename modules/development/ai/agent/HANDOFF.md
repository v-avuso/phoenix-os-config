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

- Approved sharing promotion `fb761b9` was built, merged into main and authenticated
  through explicit `ai-broker` for persistent switch. Current runtime and next-boot
  profile both resolve to
  `/nix/store/v8jxcw5jy5nc7lhdlx65lmrcq69qh3mm-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
  Sharing is ON. All six experimental controls remain OFF. Clean-source GUI on/off
  evaluation passed; installed Sandbox entry point uses the shared GUI-state guard.
  Published shared-history readiness remains authoritative; never restore originals.
- The operator clarified that human Phoenix commands must retain terminal
  `nixos-rebuild --sudo` authentication and output. Only explicit `ai-broker`
  requests should enter the controller pipeline. The correction separates these
  routes without changing updater ownership. All 24 focused tests, ShellCheck,
  Bash/Nix parsing, actual Nix command-packaging fixture and the full system build
  passed. Controller switch returned success; runtime and next-boot paths match.
  Installed `phoenix-switch --print` emits `nixos-rebuild --sudo switch --flake ...`;
  installed agent mappings point directly to the immutable deployment client.
  No extra activation or live terminal fingerprint prompt was run merely to test.
- The 2026-10-15 cold handoff published readiness and the sharing-ON trial was
  temporarily activated. Its accepted temporary closure was
  `/nix/store/4c7agrmk05mpidgan14xcig0vgjnzv94-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
  The operator confirmed this exact conversation resumed and a reply was sent
  in Sandbox, then returned to Native. Do not rerun migration or restore stale
  Native originals over the shared store. The accepted setting is now persistent.
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
  not all filesystem/network denials. Subsequent automatic-default acceptance
  and the focused nonsecret mount check are recorded below.
- Timezone repair `15ac5e1` was built and temporarily installed through native
  authentication. The updated worker returned `CEST +0200` through the supported
  sandbox-exec launcher. GUI timezone settings are packaged; visual confirmation
  awaits the next normal GUI launch. No clock or Native configuration changed.
- A nonsecret live fixture through sandbox-exec confirmed repository README
  readability while a temporary host-only /tmp canary was invisible; probe exited
  zero and the host fixture was removed. This is a focused mount-isolation check,
  not exhaustive personal-data, credential, egress or broker acceptance.
- Automatic permission selection is accepted after correction `6c1847c`: the
  operator opened Sandbox, observed Custom preselected, resumed this same chat and
  ran `pwd`, which returned `/home/v/repos/code/phoenix-os-config`. They returned
  to Native; supplied effective context is workspace-write/auto_review. This closes
  the primary automatic-default/shared-chat/command/Native-return trial.
- The immutable Sandbox adapter namespaces four permission preference keys.
  Current restricted/named/unknown profiles outrank stale host-wide preferences;
  explicit current-chat picker actions remain upstream. Exact pinned decoder-to-
  request characterization covers Approve for me (`guardian-approvals`) and the
  Custom worker policy. Native's permission code remains unmodified. One earlier
  transient Native least-permissive display remains unexplained and was not
  reproduced in the accepted return; do not claim its cause or a dedicated fix.
- The operator explicitly approved making GUI sharing persistent after the choice
  between temporary use and retaining it after reboot was explained. Earlier
  automatic-review rejections are superseded by this direct approval, not bypassed.
  Source now promotes only the accepted trial's
  `phoenix.agent.gui.sharedState.enable = true` in `modules/development/ai/default.nix`;
  the reusable option remains default off. Clean-source build, integration and
  authenticated persistent installation succeeded. Preserve published readiness and shared
  history: no migration, profile copy, extra sign-in or GUI restart is part of this
  source promotion. Identity, reservations, disruption, shutdown ordering,
  AI security review and authorization explanation remain off.
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

## Base broker and next lifecycle correction

Actual native broker acceptance passed with `ai-broker --task
broker-base-acceptance --reason 'Verify bounded diagnostic and audit path' --
phoenix-admin kernel-journal 1`: exit zero, one bounded output line, with kernel
content omitted from the receipt. Root audit recorded preflight and completion for
`admin.kernel-journal`, automatic decision, UID 1000 and the matching task/PID.
An unsupported `sudo true` operation was rejected by the adapter before dispatch.
This proves the installed named diagnostic path, not executable-specific caller
identity or automatic security-reviewed deployment; protected identity remains off.

The personal-home canary was NOT created or run. Installed launcher revision/image
now differs from the retained instance after real image changes. Existing launch
setup locking serializes launchers, but supported clients hold only a shared
history lock, which does not prevent another shared launcher from replacing their
backend. No instance was stopped. A separate instance-use lifecycle lock and
isolated concurrency tests are being scoped on the feature branch; keep it out of
live main until checked. Its first adoption must account for legacy clients that
do not participate in the new lock and require a quiescent operator cutover.

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
| Main/integration | `/home/v/repos/code/phoenix-os-config` | Awaiting approved sharing-ON source integration |
| Feature | `/home/v/.codex/worktrees/deployment-security-review/phoenix-os-config` | Repair committed; root `AGENTS.md` is an unrelated uncommitted operator-review draft |
| Trial (`codex/gui-sharing-trial`) | `/home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config` | Repair merged; sole uncommitted sharing-ON flag remains |

Do not include the root instructions draft in a deployment snapshot, reset it,
stash it or silently copy it into a deployment snapshot. The approved feature
source now enables the same sharing flag as the trial; the trial flag becomes
redundant after integration. Identity, reservations, shutdown ordering, disruption
guard, security review and authorization explanation remain off.

## Integration and next bounded work

Main contains the accepted repairs, separate human/agent command routing and
approved sharing promotion. Its clean-source full build and GUI-state ON/OFF
fixture passed. Effective evaluation showed sharing true; security review,
identity, reservations, shutdown ordering, disruption and explanation false.
The authenticated persistent controller workflow succeeded through the newly
separated agent adapter; runtime and boot match the built closure above.
The root instructions draft remains only in the feature worktree. The older
`gui-sharing-trial` checkout is retained for preservation, not the deployment
source: it predates subsequent command repairs. Use reviewed main/current work.

The bounded next shutdown regression plan is in
[shutdown-acceptance.md](shutdown-acceptance.md#proposed-test-implementation).
No guest, new runtime images or shutdown patch has been built or run.

## Resume order

1. Cold handoff and primary GUI acceptance are complete. Preserve readiness and
   shared writes; do not repeat one-time setup or request the same GUI trial again.
2. Persistent integration is complete. Continue bounded broker acceptance work;
   preserve disabled controls until their actual isolated workflows pass. Exclude
   the unrelated root instructions draft from future deployment snapshots.
3. Keep the ordinary Native fallback and accepted separate permission preferences.
   Investigate a concrete regression before requesting additional user interaction.
   Broader archive/pin/new-window observations may continue during normal use;
   optional identity/reservation/disruption/review/shutdown controls remain off.
4. On a scoped failure, preserve databases/WAL, rollout state and readiness.
   Disabling GUI sharing retains shared-history routing; original Native databases
   are stale after shared writes and must never replace the shared store.

No browser login, credential migration or general profile/database merger is part
of shared-history setup. On failure, stop and report the terminal error; do not repeat
migration automatically. Damaged published history may block both reviewed Native
GUI and CLI; retain the operator terminal and authenticated controller route.

## Evidence limits and separate unfinished work

- Unit/disposable fixtures demonstrate bounded behavior, not installed operation.
  Package builds demonstrate packaging, not activation or user workflow success.
  This exact shared conversation, automatic Custom selection, a real `pwd`, and
  Native return passed. Broader history/UI behavior remains observation work; these
  results do not establish all personal-data, network or privileged boundaries.
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
