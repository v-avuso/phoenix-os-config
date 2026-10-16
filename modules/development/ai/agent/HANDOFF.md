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

- Lifecycle guard `33bcfce`, accepted repairs and approved sharing promotion are
  integrated into main and persistently installed. Actual `ai-broker` switch
  returned `ok=true`, action `switch`, source
  `/nix/store/l0f22687ny5zw4d9rsq2pfzqh51wwr4p-source` and closure
  `/nix/store/nhqm2dwyycw5jvfr88106afig8afsynr-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
  Both `/run/current-system` and resolved `/nix/var/nix/profiles/system` match
  that closure. Installed launcher script/config match the exact built launcher
  used for acceptance. Sharing is ON; all six experimental controls remain OFF.
  Clean-source GUI on/off evaluation passed. Published shared-history readiness
  remains authoritative; never restore originals. Sharing was first persistently
  installed in the earlier `v8jxcw` closure.
- The operator clarified that human Phoenix commands must retain terminal
  `nixos-rebuild --sudo` authentication and output. Only explicit `ai-broker`
  requests should enter the controller pipeline. The correction separates these
  routes without changing updater ownership. All 24 focused tests, ShellCheck,
  Bash/Nix parsing, actual Nix command-packaging fixture and the full system build
  passed. Controller switch returned success; runtime and next-boot paths match.
  Installed `phoenix-switch --print` emits
  `nixos-rebuild --sudo switch --flake /home/v/repos/code/phoenix-os-config#metal`;
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

## Base broker and lifecycle acceptance

Actual native broker acceptance passed with `ai-broker --task
broker-base-acceptance --reason 'Verify bounded diagnostic and audit path' --
phoenix-admin kernel-journal 1`: exit zero, one bounded output line, with kernel
content omitted from the receipt. Root audit recorded preflight and completion for
`admin.kernel-journal`, automatic decision, UID 1000 and the matching task/PID.
An unsupported `sudo true` operation was rejected by the adapter before dispatch.
This proves the installed named diagnostic path, not executable-specific caller
identity or automatic security-reviewed deployment; protected identity remains off.

Lifecycle guard `33bcfce` is integrated into main. Its exact full system build
succeeded with closure
`/nix/store/nhqm2dwyycw5jvfr88106afig8afsynr-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
The operator confirmed Sandbox tasks were closed; the exact built launcher then
reconciled the idle backend without OS activation. The live personal-home canary
probe exited zero: the owned nonsecret file was absent/unreadable inside the worker
and the repository README remained readable. The owned fixture was cleaned up.

A corrected independent flock probe confirmed the instance-use lock was held during
the live client and released after exit; transport exited zero after 10.3 seconds.
The first probe targeted the wrong revision because active shared-history policy
selected a different revision; that attempt supplies no lock evidence. Nineteen
isolated tests additionally cover busy revision replacement, actual competing
launchers, transport lifetime/release, terminal descriptors, signal forwarding,
exit status and existing parent-death cleanup. Live canary/lock acceptance does not
replace those concurrency tests or establish shutdown cleanup.

Persistent installation of the accepted closure succeeded; runtime, next-boot
profile and installed launcher script/config were verified as recorded above.
Review and all experimental controls remain OFF. The separate instance-use lock
protects supported participating clients; older launchers and manual OpenShell
clients remain outside it. This first cutover used explicit operator quiescence,
not an inference that old clients held the new lock.

## Optional reviewer bounded acceptance

The protected real-adapter fixture passed as actual UID 989 through native Polkit
and setpriv, using source `91112be` at
`/nix/store/lc944afdgl4hamk1cjpxvswca3kfvnwk-source` and public configuration
`/nix/store/ajhmkb0js5ngcgg9wk7wmpmkl023ddgq-phoenix-review-trial.json`.
Pinned reviewer Codex 0.159.0 requested `gpt-6-luna`/`high`. Receipt:
`status=passed`, `modelInvocations=1`, `offlinePrecheck=true`, `exactReuse=true`,
`injectedFailure=true`, `stubFallbackBound=true`. Protected retained authentication
worked without sign-in/copy. Same source/closure on another branch incurred zero
extra AI. Deterministic injected failure and exact pending fallback were fixture
operations; Nix store/build, root checkpoint ownership, activation and fallback's
human authentication were stubs. Production review remains OFF; no deployment
was performed by the trial. See [review acceptance](security-review.md).

Two earlier protected attempts stopped before model use on fixture policy/lock
setup, with zero model invocations; regressions now cover those cases. Future
paid runs assert prompt scope before entering the real adapter; the placement
correction itself required no additional model call. Full privileged review
acceptance remains separate from this bounded compatibility/composition result.

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

Host KVM read/write open and API version 12 passed without creating a VM. The
maintained NixOS-driver rootless smoke subsequently passed in 21.9 seconds.
Actual OpenShell guest imports and TLS/gateway readiness passed with verified
Docker image archives, but sandbox creation timed out before workload readiness.
The bounded same-image remote API probe completed baseline create in 0.25 seconds
(exit zero), while keep-id reached 35.034 seconds/status 124; subsequent container
inspection blocked. This is a startup flag-dependent observation, not proof of UID
remapping/storage-lock cause and not a shutdown reproduction.

The small `tests/shutdown-workload.nix` Bash/curl/coreutils image was built and
its same-image create probe passed: baseline 0.264 seconds and keep-id 13.584
seconds, both exit zero. Exact runtime/supervisor pins and keep-id were retained.
The ordinary test reached the workload but failed on an invalid localhost deny
probe before attempting stop. Corrected source `82a9669` passed nonloopback policy
denial and ordinary stop returned in 1.498 seconds. TERM/FINAL markers appeared
and supervisor exited zero; runtime exited one and attached create did not
complete within five seconds. Exact 0.1.2 source supports separate terminal-delivery
and boundary status-classification gaps (references in shutdown acceptance).
Gateway log push ended gRPC 13/relay EOF; durable final flush remains unproved.
That ordinary run did not reproduce the 45-second stall; the subsequent combined
transaction below did, while preserving failure captures and current deadlines.
This deliberately tests control/log/shutdown behavior without the full Phoenix
image; that image's cold keep-id startup limitation remains unresolved. Follow
[shutdown acceptance](shutdown-acceptance.md). Keep ordering OFF, the 45-second
fallback unchanged and the five-minute guest cap; no production stop or Rust fix
has occurred. Manager shutdown and final-event delivery acceptance remain pending;
combined gateway/scope results follow.

The combined transaction from source `8307f7` now reproduces the 45-second stall:
45.409 seconds, both containers exit 137/no OOM, TERM present but FINAL absent,
attached transport pending and log reader exited one. Exact scopes had no Before
ordering. Sandbox Protocol loss froze the workload immediately; supervisor and
workload scope were killed at their 45-second limits before gateway stop completed.
This strongly supports conflicting teardown lifetimes, but does not identify the
specific pending remote Signal/Wait/Terminate call. This fixture froze the workload;
the original host report described prompt workload exit. See shutdown acceptance
for exact source references, artifact path and the proposed existing-ordering A/B.
This reproduction introduced no timeout reduction or Rust patch. Ordinary
terminal-delivery/status failures remain separate; the subsequent ordering A/B follows.

The existing module-generated ordering A/B (`089bb10`) reduced the same isolated
transaction to 1.484 seconds. Actual Before and conmon/resource cgroup separation
assertions passed; TERM/FINAL appeared and supervisor exited zero. Runtime exit one,
pending attached transport and log reader exit one remain. No production change
is accepted yet. The restart denial assertion was invalid: exact 0.1.2 GetSandboxLogs
reads only a bounded process-memory tail, not persisted history or an instance
archive. Missing old denial after gateway restart does not prove failed flush.
Use live gateway receipt for delivery and independent journal/Podman logs for
persistence; see shutdown acceptance for exact source lines and artifact path.

Ordered whole-user-manager shutdown from `fcda58b` returned zero in 1.518
seconds, manager inactive/status three, TERM/FINAL present, both containers stopped,
supervisor zero. Direct inspection succeeded without PAM/manager restart. The fixture
still failed pending transport; runtime exit one remains the known classification
gap. See shutdown acceptance for artifacts and the invalid prior background-pipe
attempt. Prompt teardown has isolated runtime evidence; full shutdown acceptance
and live enablement remain pending. Continue review integration preparation while
keeping all experimental controls off.

## Worktrees and preservation

| Purpose | Checkout | State to preserve |
| --- | --- | --- |
| Main/integration | `/home/v/repos/code/phoenix-os-config` | Accepted repairs, sharing promotion and lifecycle guard integrated and persistently installed |
| Feature | `/home/v/.codex/worktrees/deployment-security-review/phoenix-os-config` | Repair committed; root `AGENTS.md` is an unrelated uncommitted operator-review draft |
| Trial (`codex/gui-sharing-trial`) | `/home/v/.codex/worktrees/gui-sharing-trial/phoenix-os-config` | Repair merged; sole uncommitted sharing-ON flag remains |

Do not include the root instructions draft in a deployment snapshot, reset it,
stash it or silently copy it into a deployment snapshot. The approved feature
source now enables the same sharing flag as the trial; the trial flag is
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

The current shutdown procedure/evidence is in
[shutdown-acceptance.md](shutdown-acceptance.md#on-demand-smoke-and-pending-regression).
Disposable guests, the rootless smoke and small workload have been built/run;
the corrected ordinary-stop VM supplied the fast-stop/status-delivery failure
evidence above. No shutdown fix or production stop
has occurred.

## Root review integration and reservation lifetime acceptance

Native-authenticated root integration passed from corrected source `5b00339`,
package `/nix/store/sjkshddnlhsrh3bddj9y0r4lfvdgyqz4-phoenix-review-checkpoint-trial`:
`status=passed`, `modelInvocations=1`, `activation=false`, `rootCheckpoint=true`,
`exactReuse=true`, `builderUid=990`, `reviewerUid=989`, `controllerUid=0`,
`ownedRootsCleaned=true`. Actual process/source/cached build/worker/adapter/root
checkpoint and another-branch reuse passed. Activation alone was recorded under
the real guard/recheck; no OS activation occurred. Protected auth needed no copy
or sign-in; CLI internal requests/tokens/cost remain unmeasured. Production review
stays OFF. See security-review.md for exact source, candidate and retained prebuild
roots, which have separate cleanup ownership. Earlier caller-role failure and
pre-helper authentication expiries made no model calls; do not use the superseded
integration artifact.

The reservation systemd VM passed from source
`ecd35ed25e419e9f8962353a897c183e200ff6d1`, evidence
`/nix/store/cnwjwkjxy1hy0br7l94mnjhn54h69c0y-vm-test-run-phoenix-reservation-lifetime/evidence`.
Killing the verified submitting systemd-run client left the distinct real helper
service/recorder descendant alive. The competitor failed with activation guard
`mutation-still-running`; completion and unit successful deactivation, timeout
cleanup and gate reuse passed. A fixed immutable recorder substituted for OS
activation, using synthetic guest provenance. The exact rerun also passed the explicit competitor-reason assertion. Reservations stay OFF; peer admission, Polkit/identity,
real reservation-mediated OS activation/rollback, critical fallback and general
recovery remain separate; the independent non-reservation activation VM follows.

The real activation/rollback VM passed from source
`a49063faad024ae69f8639789ef79d028e11ce59`, evidence
`/nix/store/h7j0k43mp3fsjgh65acb9jlq7gz8wn7y-vm-test-run-phoenix-activation-runtime/evidence`.
Good specialisation activation returned zero in 1.460 seconds. Real failing
activation returned one in 2.127 seconds after observing marker `failing`; the
production rollback restored the previous good runtime/marker, and both cases
left the boot profile unchanged. This used actual systemd/controller/guard and
NixOS activation, with synthetic guest provenance and no model/auth. Critical
pending override, peer admission, boot/switch staging and host compatibility remain
separate; optional controls remain OFF. See security-review.md for exact bindings.

The synthetic pending/override trial passed through native authentication from
source `7a5a85519e70013731277b0ee73f42a3398af3bc`, package
`/nix/store/xl1z4sf500ik35sp51qxlaqdwmiwzk0h-phoenix-review-checkpoint-trial`.
Receipt: zero model invocations, activation=false, syntheticPending=true,
wrongOperatorRejected=true, pendingConsumed=true, replayRejected=true,
rootCheckpoint=true, controllerUid=0, ownedRootsCleaned=true; authentication was
`generic-pkexec-not-critical-action`. Host runtime/boot remained unchanged.
This supersedes the expired attempt. Supplied UID checks are not socket admission,
synthetic pending is not AI rejection, and recorded activation is not execution.
Production critical-action fresh authentication remains unproved; controls stay OFF.

## Latest controlled critical-policy window

The explicitly authorized five-minute trial used clean-main `af696bf` review-ON
overlay closure `3ys5za7ivy19kzdxpr9vyh9n7lfkzdnf`; main/default/boot stayed OFF.
Native rollback timer `phoenix-review-off-rollback-trial` was armed for exact OFF,
with bounded retries. A guard first refused safely because /proc/uptime includes
suspend; corrected CLOCK_MONOTONIC comparison and a fresh timer preceded ON.
ON activation succeeded (DBus/deployment reload, Polkit/HM restart; no reported
GUI/OpenShell restart). Exact critical action/helper registered as AUTH_ADMIN/no-keep.
The intended CANCEL probe was approved: the operator explicitly reports approving
all requests because the chat label did not clearly identify the cancel-target
dialog. Missing-pending rejection was expected after approval; no approval record,
reviewed deployment or model call occurred. Cancellation was not exercised;
precise critical-warning recognition/fresh-auth isolation remain unproved. No
PAM/cache bypass is established; the coordinator acknowledged sequencing ambiguity.
Immediate OFF restoration succeeded; runtime/profile both match accepted `nhqm...`
and critical action is absent. The initial timer-stop request expired (124); the explicit operator-authorized
retry succeeded. Independent checks found timer/service not-found, inactive/dead
and service Result=success. Cleanup is complete; runtime/profile remain accepted
OFF and critical action absent. No further authentication dialogs are requested. See security-review.md.

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

## Isolated deployment socket composition

Exact source `d13dd5eca051b75d51d5f2843702a0545abab655` passed the real socket/
SO_PEERCRED VM fixture. Evidence:
`/nix/store/q7radgkhbndj4sa5c2jjbyc8p3gicp17-vm-test-run-phoenix-deployment-peer/evidence`.
Configured metadata was admitted; outsider/operator/updater execution was rejected.
Production worker error/denial returned `review-invocation-failed`/`model-denied`
without activation; counters were three reviews/one approved activation double.
Nix/model/subprocess/activation doubles and live acceptance limits are detailed in
[security review](security-review.md#isolated-deployment-socket-composition).
Production review remains OFF; this does not establish general command AI review.

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
  security-review workflow have separate unfinished live acceptance. The protected
  reviewer adapter/auth/schema, root integration/checkpoints and recorder-based
  systemd lifetime trials, real guest activation/rollback and generic-authenticated
  synthetic pending trial and isolated real-peer socket composition above passed.
  Exact critical-action cancellation/fresh authentication and a live reviewed
  deployment remain unproved. The generic
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
