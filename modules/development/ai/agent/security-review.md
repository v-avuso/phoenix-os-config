# Optional deployment security review

`services.phoenixDeployment.securityReview.enable` remains off by default. Its
legacy `modelReview.enable` option is an alias. Authentication, dirty-source
freezing, exact closure binding, disruption checks, reservations and rollback
apply independently of AI. Routine updates use the deterministic validator with
zero AI and Polkit calls.

## Isolated deployment socket composition

The NixOS VM fixture `tests/deployment-peer.nix` passed at exact source
`d13dd5eca051b75d51d5f2843702a0545abab655`; evidence is under
`/nix/store/q7radgkhbndj4sa5c2jjbyc8p3gicp17-vm-test-run-phoenix-deployment-peer/evidence`.
A real socket-activated root daemon reads kernel SO_PEERCRED and runs production
request dispatch, authorization, worker and bound-verdict validation. Configured
client/operator metadata succeeds; a DAC-admitted outsider UID, operator execution
and updater `test` execution return `invalid-or-denied`. The client’s injected
adapter error returns `review-invocation-failed`, rejection returns `model-denied`,
and neither reaches activation. Three worker/model-boundary visits and one approved
activation callback are asserted, including per-failure counts.

Nix realization, reviewer subprocess/UID transition, model decision and activation
are explicit doubles; no model or host deployment occurs. This establishes socket
composition in isolation, not installed review-enabled operation, executable-specific
identity, critical-action authentication or general privileged-command AI review.
The installed shared client/operator UID remains the authority boundary while
protected identity is OFF. A controlled real reviewed deployment passed below; critical-dialog
cancellation remains unresolved;
optional identity/reservations/disruption/explanation are separate milestones.

## Controlled review-window helper

`tests/review-window.nix { flake; offClosure; onClosure; }` packages fixed,
argument-free setup/recovery/dry-run commands. Explicit closure inputs must be
canonical immutable store paths. For the already accepted pair, OFF is `nhqm...`
and temporary ON is `3ys5...` (full paths in HANDOFF); packaging does not activate
either. Build from an exact committed Git-flake source, excluding the root draft:

```nix
let f = builtins.getFlake "git+file:///PATH?rev=COMMIT";
in import (f.outPath + "/modules/development/ai/agent/tests/review-window.nix") {
  flake = f; offClosure = "/nix/store/FULL-OFF"; onClosure = "/nix/store/FULL-ON";
}
```

Exact helper source `e72a49796bc15b1f921c6d72f3b8e391c7a07d94` built successfully
as `/nix/store/mv6m57y7pgisflg7v0jxpa8cqssxhy9c-phoenix-controlled-review-window`
(five small derivations, no downloads). Its host-namespaced unprivileged dry-run
passed with `package-valid-no-state-change`. Live setup, reviewed deployment and final recovery passed below.
Run the packaged `phoenix-review-window-dry-run` unprivileged first (host tool
namespace, so immutable ownership is visible). Only the coordinator invokes the
setup through native graphical authentication. Setup requires actual OFF runtime
and boot profile, shared UID1000, absent owned units and idle existing production
locks. It arms `phoenix-controlled-review-off.timer` before ON `test`; ON is ready
only while its non-waking monotonic timer has at least150 seconds left. A queued
or too-short timer causes OFF recovery after releasing setup locks, never a reset.
Recovery signals only the exact ON controller, queues at five minutes, waits up
to8100 seconds across deployment then activation locks, and restores exact OFF
with `test`. This queues behind the bounded build/review/activation request; it
does **not** promise OFF at five minutes. Guard FDs survive into the foreground
activation child. It never changes the boot profile or existing lock permissions.
After verified OFF it stops its owned timer; transient service collection follows
exit. Check both owned units are gone/inactive and runtime/profile OFF afterward.
On validation/lock/command failure, stop and inspect static stage/code journals;
no model retry, operator override or force-kill of an in-flight deployment occurs.

Prepare the canonical OFF request from a clean main checkout, never this dirty
feature checkout. Freeze its Git-visible files/modes with the existing production
source-freezing code and prebuild the resulting exact `path:/nix/store/...-source`
metal target offline/no builders; stop on downloads or unexpected rebuilds. Bind
and record this candidate closure/source before setup. The candidate may differ
from the older accepted recovery OFF closure: a successful reviewed candidate is
then temporary; fixed recovery deliberately returns to accepted OFF afterward.
Do not cancel recovery merely because the reviewed candidate has review disabled.
After explicit readiness for the single identifiable Cancel dialog, use the newly
installed ON-policy native `ai-broker` (resolve `/etc/profiles/per-user/v/bin/ai-broker`
after activation), `--task ... --reason ... -- phoenix-test --worktree /CLEAN/MAIN`.
An old immutable OFF client fails policy preflight; do not bypass it. Verify real
review/checkpoint/audit and candidate runtime, then final fixed OFF recovery.
No concurrent deployment/update/human rebuild belongs in this coordinated window.

The offline test checks ordering, real disposable flock contention/modes, failure
recovery and timer readiness. Packaging/dry-run/live acceptance remain separate;
this fixture introduces no production service, default enablement or general
privileged-command reviewer.

## Controlled real reviewed deployment (passed; cancellation unresolved)

The fixed helper `/nix/store/mv6m57y7pgisflg7v0jxpa8cqssxhy9c-phoenix-controlled-review-window`
completed authenticated setup (`on-ready`, exit0). The exact native ON-policy
`ai-broker` then completed `controlled-reviewed-deployment`, action `test`, exit0:
source `/nix/store/h3n90h28yzv85rwd0q3rb8p5s7f8gyby-source` (clean main `baac836`)
and closure `/nix/store/ngdi4win5kwsqknnn2bs009mdsvyg58m-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
Root journal recorded real review (`diffBytes=20473`, controller invocation limit2,
context byte limit131072) and actual activation. Runtime matched the candidate;
boot profile stayed accepted `nhqm...`. The OFF controller became active with
`/nix/store/400iw2wnq636v76dppri0v6lr1f60inr-phoenix-deployment.json`.
No per-request human approval was needed. Actual model internal API calls/token
cost were not measured. Root checkpoint publication follows this production success
path; its0700 state directory was not directly inspected using another authorization.
Final recovery passed: journal stages were `recovery-queued` → `off-restored` →
`owned-timer-stopped-service-exits`. Independent checks found timer/service
not-found/inactive/dead, Result=success; runtime and boot profile both returned
to exact accepted `nhqm...` OFF. No trial or authentication request remains running.

The separately coordinated critical absent-nonce probe produced no root-helper
output and expired after60 seconds (124). The operator reports clicking Cancel
twice without effect. This does not prove cancellation, authorization or a policy
bypass; the behavior is consistent with the source-backed authentication-agent
UX gap below, not a demonstrated review engine failure. Installed agent is unpatched `polkit-gnome0.105`, Polkit127, with
biometric→PIN→password PAM fallback. The official0.105 source hash matches locked
nixpkgs. `polkitgnomeauthenticator.c:261–268` connects delete-event/user selection
but no dialog response handler; `authenticationdialog.c:533–535` emits a Cancel
response. That response is consumed by nested `gtk_dialog_run` during selection/
password prompts (`:953`,`:1005`), while biometric show-info displays the dialog
and outer authentication waits (`authenticator.c:346–361`,`:432`). Thus an ignored
Cancel during biometric waiting has a concrete source-backed explanation; runtime
click/handler delivery was not instrumented. Window-delete uses the explicit cancel
path; it was not tested as an alternative in this trial.

Prefer a maintained agent trial over a custom C patch: locked nixpkgs already has
[hyprpolkitagent0.1.3](https://github.com/hyprwm/hyprpolkitagent/tree/v0.1.3).
Its QML Cancel always calls `setResult("fail")`, routed through Agent to
`cancelPending()`/Polkit Session cancellation independently of password-prompt
loops. Real biometric/PIN/password cancellation and completion ordering still need
one representative test before replacement. Locked0.1.3 only logs PAM show-info
messages rather than displaying them, so biometric/PIN cue readability is also
unverified. No agent/PAM change or restart occurred.
No verified GNOME upstream fix was found in the bounded search. Official sources:
[GNOME0.105 archive](https://download.gnome.org/sources/polkit-gnome/0.105/polkit-gnome-0.105.tar.xz),
[Polkit127 session cancellation](https://github.com/polkit-org/polkit/blob/127/src/polkitagent/polkitagentsession.c#L655-L668).

## Adapter and bounds

```nix
services.phoenixDeployment.securityReview = {
  enable = true; # isolated trial only until live acceptance
  adapter = "codex";
  model = "gpt-6-luna";
  effort = "high";
};
```

Only the existing isolated Codex adapter is implemented. Other adapters are
rejected. The reviewer CLI stays pinned independently of the everyday CLI.
Model/effort are requested settings; actual availability and compatibility need
an isolated retained-auth trial. No trial, sign-in, paid model call or retry occurs
when building or running the fixtures.

Every deployment freezes permitted Git-visible tracked/new/deleted content and
file modes before building. That complete snapshot is source transport, not the
AI prompt. The model receives the local security diff, exact binding and a
baseline/candidate file/line index. It can ask for one bounded explicit context
round: at most eight ranges and 128 KiB serialized context. At most two controller
CLI invocations occur. Policy, binding, diff, index and schema together have a
1 MiB serialized input limit; each invocation retains its 600-second timeout,
output bound and compaction rejection. The approximately 24,000-token warning is
advisory. Native CLI internal API calls and cumulative token cost are unknown and
not hard capped. No upstream dependency-review batches run.

## Baseline and checkpoint reuse

The first review already compares against the activated source; it does not
review the whole repository. Exact root-owned checkpoints retain source, built
closure, target and an installed policy/execution digest. The digest includes
adapter/model/effort, authorization policy and effective caller/builder/reviewer
identities. Embedded authorization/transport helpers are packaged as stable
individual store files and their bytes are hashed: unrelated repository relocation
does not invalidate approval, while actual helper changes do. Experimental
reservation settings can still contain generation-sensitive paths and conservatively
invalidate reuse when enabled; reservations remain off. At most 32 approved/pending
records retain their source/closure GC
roots. Changing policy, target, closure or source prevents stale exact approval.

With review enabled on an isolated test system, the native operator may run:

```sh
phoenix-review-trust-active
```

This fixed helper requires fresh Polkit authentication and no arguments. It
adopts only `/run/current-system` and its immutable source marker, never a caller
source/closure, another branch, or the possibly different next-boot profile. It
checks ownership/binding and the runtime closure's versioned target/source
provenance, and rechecks runtime/profile/policy while holding the existing deployment and activation locks before
publishing an exact checkpoint. It performs no model call, build or activation.
It is explicit seeding, not automatic per-generation approval and not a
prerequisite for the activated-source diff baseline.

Exact source **and closure** reuse skips AI globally across branches. New sources
still need review. Context chooses the smallest content/mode diff among the
activated source and all independently approved same-policy/target checkpoints.
Branch labels are metadata. A union/merge of approved changes is a new integration
state: the remaining diff needs review; approvals are never blindly combined.
An explicit fresh human override advances only its protected exact pending
source/closure/action binding, even if activation later fails.

## Failures and evidence

The trust helper emits bounded stage/code diagnostics, including
`baseline-authentication-required`, `baseline-provenance-missing`,
`baseline-provenance-invalid`, `baseline-target-mismatch`,
`baseline-runtime-mismatch`, `baseline-state-changed` and
`baseline-verification-failed`. Existing generations without provenance cannot
be explicitly seeded; ordinary activated-source diff review remains available.
Provenance records the installed target/source correspondence; it does not prove
code safety. Fresh operator authentication explicitly trusts the current active
state. No Nix graph reconstruction, IFD or original Git metadata is required. Review failures retain existing typed authentication, input,
context, compaction, schema and binding errors; unsupported adapter execution is
`review-adapter-unsupported`. CLI incompatibility, model availability, rate-limit and
network failures have static `*-suspected` categories: stderr patterns are
diagnostics, not proof of cause. Raw Nix/model stderr is never an authorization log.

`tests/agent-deployment.py` exercises controller → worker → adapter → checkpoint,
explicit trust, dirty diff, global reuse, integration review and exact human
fallback using explicit OS/store/build/model stubs. `tests/security-review.nix`
checks enabled-only native packaging and option defaults. These are fixture and
configuration evidence. The bounded protected-UID real-adapter trial below passed;
root checkpoint ownership, activation and production fallback authentication remain
separate pending acceptance.

## Opt-in real-adapter fixture (production review stays off)

`tests/agent-review-live.py` reuses the disposable controller/worker/checkpoint
fixture with the real production adapter. Ordinary `tests/agent-deployment.py`
remains offline, including adapter doubles exercising the opt-in branch. A live
run requires separate authorization for model use and must already execute as
`phoenix-deploy-review`, never root or the Native user. It uses only the protected
existing `/var/lib/phoenix-deploy-review` through the production adapter; no auth
is copied, printed, inspected by the fixture, or replaced with Native credentials.
Missing retained authentication fails closed: do not sign in or migrate for this
trial. Keep production review OFF and run only one trial at a time.

First run `python3 -I tests/agent-review-live.py --dry-run` from this module;
without opt-in it refuses execution. The actual source must be a reviewed immutable
repository tree (including `tests/agent-deployment.py` and its sibling modules,
policies, authorization library and transport JSON); it needs no `.git` directory.
Before a paid trial, run these selected offline cases from that exact packaged
immutable tree (no authentication or model):

```sh
python3 -I /nix/store/SOURCE/modules/development/ai/agent/tests/agent-deployment.py \
  DeploymentTests.test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow \
  DeploymentTests.test_optin_integration_branch_with_offline_adapter_double
```

The fixture supplies its semantic authorization policy explicitly: installed
`/nix/store` code deliberately rejects the worktree-only compatibility fallback.
This is fixture configuration, not a change to production authorization.

The reviewed immutable public JSON configuration has exactly these fields:

```json
{
  "codex": "/nix/store/PINNED-codex-0.159.0/bin/codex",
  "bwrap": "/nix/store/PINNED-bubblewrap/bin/bwrap",
  "caBundle": "/nix/store/PINNED-cacert/etc/ssl/certs/ca-bundle.crt",
  "reviewHome": "/var/lib/phoenix-deploy-review",
  "model": "gpt-6-luna",
  "effort": "high"
}
```

Resolve `codex` from the locked package set's `callPackage ./reviewer-codex.nix {}`;
do not select another cached package solely by version. The operator authenticates
one concrete immutable command using the supported native Polkit dialog:

```sh
pkexec /nix/store/UTIL-LINUX/bin/setpriv \
  --reuid=phoenix-deploy-review --regid=phoenix-deploy-review --init-groups --reset-env \
  /nix/store/PYTHON/bin/python3 -I /nix/store/SOURCE/modules/development/ai/agent/tests/agent-review-live.py \
  --allow-paid-review --config /nix/store/PUBLIC-CONFIG.json
```

The runner validates immutable public paths and the protected UID, then runs the
selected offline integration case as that same actual UID before accessing the
protected home or live adapter. An offline failure stops with an `offline-*` stage
and zero model invocations. Fixture requests and their parent deployment lock stay
inside the owned private temporary tree; unrelated `/tmp/deployment.lock` is never
adopted or repaired. Only after that check passes does it validate the protected
home and run the live adapter. It reviews one comment-only change, checks a bound verdict,
then reuses identical source/closure across a different branch with zero extra
model calls. A deterministic injected failure exercises pending state and exact
fallback with explicit stubs. One optional context round permits at most two real
CLI invocations total, 600 seconds each, with no retries; internal API/token costs
remain uncapped. Output contains status/counts/booleans and bounded static stage/code diagnostics.
Failure reports a static stage/category and, when available, a line number from
our integration fixture only; it emits no raw model output, prompts, auth or
stderr. Stop on the first
failure and address its category; do not automatically retry.

This is real adapter compatibility plus controller composition evidence. Store,
build, root checkpoint ownership, activation and human fallback authentication
remain fixture stubs; the one Polkit launch does not prove production fallback's
fresh-auth contract. Do not describe success as live privileged deployment review
acceptance or enable production review from this result alone.

### Recorded protected-adapter acceptance

The exact immutable source `91112be`, packaged at
`/nix/store/lc944afdgl4hamk1cjpxvswca3kfvnwk-source`, passed through the native
Polkit → setpriv route as actual protected UID 989. Public configuration was
`/nix/store/ajhmkb0js5ngcgg9wk7wmpmkl023ddgq-phoenix-review-trial.json`, selecting
the independently pinned Codex 0.159.0 reviewer, `gpt-6-luna` and `high` effort.
The static receipt was:

```json
{"exactReuse":true,"injectedFailure":true,"modelInvocations":1,"offlinePrecheck":true,"status":"passed","stubFallbackBound":true}
```

Protected retained authentication, real CLI/schema/binding and the same-UID offline
precheck worked without sign-in or credential copies. Identical source/closure
under another branch reused approval with zero additional AI. Injected deterministic
adapter failure produced pending state and exact fallback binding using stubs.
Two preceding protected attempts made zero model calls: immutable fixture policy
and a request-parent lock outside the private tree failed before review; both now
have regressions. Nix store/build, root checkpoint ownership, activation and human
fallback authentication remain stubbed. No deployment occurred and production
review stays OFF. Prompt-scope guards now precede the real-adapter branch for future
runs; no additional model call was made for that assertion-placement correction.

## Zero-AI root checkpoint trial (separate narrower proof)

`tests/review-checkpoint.nix { flake = ...; }` packages two argument-free test
commands. It derives the exact production controller/config through an isolated
review-ON `extendModules` evaluation and asserts the existing ExecStart shape.
Building it neither enables nor activates review on the live system. It adds no
production exports, service, endpoint or Polkit policy. From the exact committed
Git source (never `path:.` or the unrelated root instructions draft):

```sh
nix build --no-link --print-out-paths --expr 'let
  f = builtins.getFlake "git+file:///home/v/repos/code/phoenix-os-config?rev=COMMIT";
in import (f.outPath + "/modules/development/ai/agent/tests/review-checkpoint.nix") { flake = f; }'
```

Run `RESULT/bin/phoenix-review-checkpoint-trial-dry-run` unprivileged first; it
reads only immutable public descriptor/config and prints the zero-model/no-
activation scope. After reviewing that exact artifact, authenticate one concrete
command with `timeout 120 pkexec RESULT/bin/phoenix-review-checkpoint-trial`
(the cap includes authentication; expiry fails rather than retrying). Both wrappers
reject caller arguments. The actual helper requires root and exact authenticated
`PKEXEC_UID=operatorUid`, derives source/closure only from active runtime/provenance,
requires runtime and next-boot profile agreement, and checks existing store paths
are valid before proceeding. It performs no new build, fetch, sign-in or auth-home
access. Busy/missing/changed state stops with a bounded stage/code; never retry or
override automatically.

A root-owned temporary base contains private checkpoints and separate requests.
The helper holds the ORIGINAL global deployment lock nonblocking, while production
`trust_active` uses the DISTINCT private request-parent lock and the original
activation guard identity. This avoids self-deadlock and concurrent deployment;
it does not adopt/change/delete production cache, shared lock files or credentials.
Normal `phoenix-authorization` requested/completed audit events are emitted by
production `trust_active`; match their PID to `trialPid` in the fixture receipt.
These are private-cache trial logs, not production approval records.
Production code verifies immutable provenance and rechecks state while publishing
actual private root checkpoints and Nix GC roots. The helper verifies UID/modes,
exact root targets and cross-branch same-source/closure reuse, then removes only
its owned temporary tree/indirect-root paths. A persistent dangling auto-root
registry entry, if any, is ordinary Nix GC bookkeeping; no global cleanup runs.

This is the deliberately cheaper explicit-trust seed path: ZERO AI, no request
`process`, reviewer worker, new Nix build or activation callback is invoked. It
proved root checkpoint/provenance/guard/GC-root behavior in the actual trial
below. The earlier protected reviewer trial is separate composition evidence;
this does not prove root-to-worker review/new-build integration, temporary
activation or fresh-auth security override. A denied review is never automatically
overridden. Production security review remains OFF.

Offline checks: `python3 -B tests/review-checkpoint-test.py` tests authentication,
lock separation, record binding/modes with explicit ownership stubs, and dry-run
without auth/controller execution. Those tests do not establish root operation.

The actual authenticated root trial passed from exact source
`f02d64a4d8e58d06dd7f2e5c49ba7b9700365263`, using immutable package
`/nix/store/7wa7xdndbkb5xgachrwiig9n9mhx3hxz-phoenix-review-checkpoint-trial`:

```json
{"status":"passed","modelInvocations":0,"activation":false,"rootCheckpoint":true,"exactReuse":true,"ownedRootsCleaned":true,"trialPid":924666}
```

This used only the explicit-trust checkpoint path and cleaned its owned private
roots/tree. Production cache, credentials/sign-in, profile and activation were
untouched; review remains OFF. This receipt alone excludes root-to-worker/build
review, which the separate integration trial below subsequently exercised. Actual
activation and fallback authentication remain pending.


## Root process integration trial (bounded acceptance passed)

The same on-demand `tests/review-checkpoint.nix` package additionally provides
argument-free `phoenix-review-integration-trial-dry-run`,
`phoenix-review-integration-prebuild-plan` and `phoenix-review-integration-trial`.
The existing zero-AI entries retain their narrower behavior. Build from an exact
committed Git-flake source; never package the working tree/root instructions draft.
Production review remains OFF and this creates no service or production endpoint.

First run the dry-run (no auth/model), then the unprivileged prebuild-plan. The
latter adds a deterministic snapshot to the Nix store using only actual activated
baseline files/modes plus one fixed README HTML comment; it prints the exact
source and offline Nix build argv. Preview that argv with `--dry-run`, stop on
unexpected rebuilds or missing inputs, and explicitly prebuild within a proposed
five-minute/zero-download budget. A comment changes source provenance and thus
may require a new system closure. Keep the returned closure/source alive until
the trial. The paid entry's Nix wrapper disables downloads, local build jobs and
remote builders: any missing prebuilt output fails before review. No candidate
content/path/command is accepted from entry-point arguments.

Only after package review and explicit one-call authorization, use the supported
host Polkit flow with the exact immutable no-argument integration executable;
wrap it in an overall 180-second timeout with a ten-second kill grace. Authentication
remains native. Root validates PKEXEC_UID, unchanged runtime/profile, original
global deployment lock (nonblocking) and activation-guard identity. Private root-owned
requests/config/checkpoints stay under one owned temporary tree. Config is root
0444 and traversable for the configured builder/reviewer. The fixture supplies the configured client UID to the review-enabled daemon
entrance (`operator=False`); its separate native entry still authenticates the
operator. This synthetic caller identity does not prove SO_PEERCRED/socket admission.
Real production process,
source-store/build commands, setpriv worker, protected reviewer home, adapter and
root checkpoint/GC-root publication run; no credentials are read/copied by the
fixture. Separate private policy seeding accounts for its test wrapper identities.

The sole replaced production callback is `activate_bound`: it takes the real
activation guard, rechecks exact binding/runtime/profile and records the boundary.
It never activates, updates profiles or restarts services. The second process call
uses identical files/source with another branch and must reuse the exact checkpoint.
The receipt reports controller/builder/reviewer UIDs and activation=false. Captured
controller output/model summaries are not printed; failures expose static stage/code
and an at-most-one invocation bound. Denial never triggers an override/retry.

Two immutable test wrappers bind one trial-wide token into every adapter `/work`
namespace and consume it atomically before pinned Codex executes. The root-owned
budget directory prevents deletion by the reviewer; its reviewer-writable token
is a normal-fixture cost guard, not authority against a hostile reviewer UID.
It caps actual CLI invocations at one across context requests and repeated calls,
not CLI-internal server requests, tokens or billing. A requested context round
therefore fails closed before another CLI invocation. Protected-UID gate traversal passed in the actual trial below; offline tests also
cover normal mode ownership layout,
concurrent token exclusion and composed callback behavior with explicit doubles.

Production subprocess bounds kill/wait their child process groups on interruption;
the adapter retains bubblewrap die-with-parent. Temporary cleanup removes only
owned private checkpoints/GC-root links/config/budget after calls end. The fixture
may create production audit records labelled review-integration-trial, but no
production approval/cache. Actual activation, rollback and fresh-auth fallback
remain separate acceptance work; no full privileged acceptance is claimed here.

The exact `870d8518e916cc9e683b5f91e2ae995481fe6866` package was built:
`/nix/store/75mlqg6d1q1alp4s5sw1l31jxkiyh34c-phoenix-review-checkpoint-trial`.
Its integration dry-run passed. The prebuild plan produced
`/nix/store/j0zn5xxjvkq32br6qgprrvq5qw0y4c8s-source`; direct comparison with the
actual baseline found only README content changed. Offline prebuild completed
within the five-minute cap, without downloads, producing
`/nix/store/prn74jw821yzbw0dz3z9ia6nrzdqhima-nixos-system-phoenix-26.05.20261004.0d9e9b8`.
The closure's activated-source link matches that candidate. Owned temporary GC
roots `/tmp/phoenix-review-integration-roots.hqd6tY/{source,closure}` retain both.
Remove only those owned links/directory after the trial no longer needs them.

### Current retry artifact and authorization regression

Use corrected source `5b0033907c81c915c3fa795c123b62bb3a65e48e`, package
`/nix/store/sjkshddnlhsrh3bddj9y0r4lfvdgyqz4-phoenix-review-checkpoint-trial`.
The earlier `75ml...` integration entry is superseded: after authentication it
used `operator=True`, which production policy correctly rejects for review-enabled
requests before `process_inner`. That attempt made no reviewer invocation.
The corrected fixture retains its outer native operator authentication, then
calls normal process dispatch with the configured client UID. A nine-test suite
now exercises real authorization, contrasting the rejected operator entrance
with accepted agent dispatch. Caller UID is supplied synthetically by the fixture;
socket peer admission remains outside its proof.

Corrected package build, dry-run and prebuild-plan passed; the candidate above
was unchanged. Actual native-authenticated integration then passed using the
corrected immutable entry:

```json
{"status":"passed","modelInvocations":1,"activation":false,"rootCheckpoint":true,"exactReuse":true,"builderUid":990,"reviewerUid":989,"controllerUid":0,"ownedRootsCleaned":true}
```

This proves actual root process → frozen source/cached Nix realization as builder
990 → real reviewer worker/adapter as UID 989 → root-owned exact checkpoint and
cross-branch reuse. The one CLI invocation used pinned Codex 0.159.0 with requested
`gpt-6-luna`/`high`; internal API calls/tokens/billing were not measured. Protected
retained authentication worked without sign-in/copy. Only activation was a guarded
recording callback. Separate guest activation/rollback, socket-peer and controlled
real reviewed deployment trials passed; precise critical cancellation remains unresolved.
The fixture cleaned its private state/GC roots; separately retained prebuild roots
above require their own cleanup. Earlier authentication-only expiries made no
model calls, and the superseded caller-role failure is covered by the regression.


## On-demand real guest activation/rollback (accepted bounded slice)

`tests/activation-runtime.nix { pkgs = ...; }` is a separate maintained NixOS-driver
VM test, not a default check. Use the locked flake's pkgs from an exact committed
Git source; no checkout-path source or host activation. Two CPUs/2 GiB and a
180-second guest limit reuse cached driver infrastructure. Preview build cost;
stop for unexpected uncached large builds or a five-minute build/run budget.
Actual VM source `a49063faad024ae69f8639789ef79d028e11ce59` passed; evidence:
`/nix/store/h7j0k43mp3fsjgh65acb9jlq7gz8wn7y-vm-test-run-phoenix-activation-runtime/evidence`.
Good activation returned zero in 1.460 seconds, selected
`/nix/store/nmwbrnajcbs4nwcc8nblc2m547lzahbn-nixos-system-machine-test` and marker
`good`. Failing activation returned one in 2.127 seconds; `failure-observed`
contains `failing`, while runtime/marker returned to that good specialisation.
Both retained boot profile
`/nix/store/rd6blsfrw7vkgffmwwl1miwj9yj98j8p-nixos-system-machine-test`.
Journal confirms the real controller's candidate command failed; its production
rollback completed before that failure returned.

The guest has good and failing NixOS specialisations, sharing one immutable
synthetic `source` provenance. The driver starts the actual production `activate`
entry in transient systemd services with the real guard, source/profile binding
checks, packaged subprocess runner and real `switch-to-configuration test`.
Dependencies are individually packaged and imported during a build-time check.
No recorder, reviewer, model, authentication agent or activation callback is used.
Guest-only setup initializes the system profile to its current runtime only if
its test image omitted that profile; test activations must leave it unchanged.

Success requires the good specialisation to change the actual current runtime
and `/etc` marker. The failing specialisation changes `/etc`, records that observed
state and runs `false` in a real activation snippet; the normal NixOS error trap
returns nonzero. Production `activate()` must invoke rollback to the previous
runtime; both runtime and marker must return to the good specialisation, while
the boot profile remains unchanged. Each service is bounded independently and
journals/status/binding observations are exported even after a failure.

This tests temporary activation and its real failure rollback only. Synthetic
provenance is not review of guest configuration; root controller admission,
SO_PEERCRED, critical pending override/Polkit authentication, boot/switch staging
and production-host compatibility remain outside its proof. Production optional
controls remain OFF; this guest result does not authorize host activation or
critical security override.


## Synthetic pending/override composition (bounded acceptance passed)

The existing on-demand checkpoint package also supplies argument-free
`phoenix-review-pending-trial-dry-run` and `phoenix-review-pending-trial`.
Package from an exact committed Git source, run the dry-run unprivileged, then
use the supported native `timeout --kill-after=10 120 /run/wrappers/bin/pkexec --disable-internal-agent /nix/store/EXACT-PACKAGE/bin/phoenix-review-pending-trial`
flow only after reviewing that immutable artifact. This is generic native pkexec
authentication, not the production critical override action or its warning.
No model, new build, sign-in, credential copy or production review enablement occurs.

The fixture reuses actual active source/runtime/profile validation, the original
nonblocking deployment lock and activation guard, plus private root-owned
requests/checkpoints/GC roots. Pending mode skips trust-active approval seeding:
the cache must be empty before entry and remain unapproved after wrong-UID
rejection; only the successful override creates approval. It creates one explicitly synthetic pending failure
bound to the actual runtime/source and current policy; this is not an AI rejection.
The real production `override` must reject a wrong supplied operator UID, approve
only the exact protected binding, consume pending JSON/roots, and reject nonce
replay. Root checkpoint ownership/modes/targets and the override branch record
are verified. The sole substituted callback records activation under the real
guard/recheck and verifies runtime/profile unchanged. The outer entry authenticates
the native operator; wrong-UID probing is synthetic, not socket/peer admission.
Owned temporary roots/state are cleaned, without touching production cache/auth.

Ten offline checkpoint tests include real pending/approve/consume and guard
composition with explicit store/owner/global-path stubs. Actual native-authenticated
execution passed from source `7a5a85519e70013731277b0ee73f42a3398af3bc`, package
`/nix/store/xl1z4sf500ik35sp51qxlaqdwmiwzk0h-phoenix-review-checkpoint-trial`:

```json
{"status":"passed","modelInvocations":0,"activation":false,"syntheticPending":true,"wrongOperatorRejected":true,"pendingConsumed":true,"replayRejected":true,"rootCheckpoint":true,"controllerUid":0,"ownedRootsCleaned":true,"authentication":"generic-pkexec-not-critical-action"}
```

Host runtime/boot remained unchanged. Pending creation was synthetic, wrong UID
was supplied by the fixture rather than SO_PEERCRED, and activation was recorded
rather than executed. Authentication was generic native pkexec, not the production
critical action. Earlier expiry is superseded by this pass; no retry remains pending.
Production critical-action policy is absent while review is OFF;
its exact fresh-authentication/UX authority needs a separate isolated policy/helper
trial. A generic pkexec pass must never be described as proving that action.


A bounded inspection of locked Nixpkgs `0d9e9b8` found maintained real GUI
Polkit authentication tests in `nixos/tests/cosmic/test-script.py` and `lomiri.nix`;
no lightweight headless cancellation/fresh-auth pattern was verified in that
search. This is not a claim that none exists. A controlled live critical-policy
trial requires an operator test window and a concrete return to the retained
review-OFF closure. The controlled absent-nonce probe below is only negative policy gating; it
cannot prove the pending workflow or fresh/cancelled authentication.


## Controlled critical-policy trial (OFF restored; cancellation unvalidated)

The operator authorized a five-minute live policy window. Candidate
`/nix/store/3ys5za7ivy19kzdxpr9vyh9n7lfkzdnf-nixos-system-phoenix-26.05.20261004.0d9e9b8`
was built from clean main `af696bf57e89c892d150c310e9a422aa720c4ce2` with review ON
only as an evaluation overlay; source/default and boot remained OFF. The fixed
zero nonce was confirmed absent using the correct Coreutils test entry point.
A native five-minute `phoenix-review-off-rollback-trial` timer targeted the exact
accepted OFF closure, with ten-second failure retries limited to three per 120s.
Its first guard safely refused a mismatched uptime clock; the corrected guard
used `time.monotonic_ns()` and a freshly reset timer before ON activation.

Actual ON activation succeeded: DBus and deployment reloaded, Polkit/Home Manager
restarted, with no GUI/OpenShell restart reported. The registered action was
`org.phoenix.security-review.override`, annotated to
`/nix/store/bbw3kwadyz0drjjgxci1y0c9h630idkx-phoenix-security-review-override`,
with active `AUTH_ADMIN` (not keep). The operator subsequently confirmed approving
all authorization requests, including this one: chat labels did not clearly
identify which dialog was meant to be cancelled. The helper then rejected the
absent pending file with FileNotFoundError, as expected after approval. No approval
record or reviewed deployment occurred; this path makes no model call. Cancellation
was not exercised. Operator authentication was observed generally, but precise
critical-warning recognition and a separately isolated fresh-auth step were not
established. There is no evidence here of a PAM/cache bypass or unexplained
authorization; the coordinator acknowledged unclear dialog sequencing.

The exact OFF closure `nhqm2dwyycw5jvfr88106afig8afsynr` was restored successfully;
runtime and system profile both resolve to it and the critical action is absent.
The first owned timer-stop request expired (exit 124); the explicit operator-
authorized retry succeeded. Independent checks found both owned timer and service
not-found/inactive/dead, with service Result=success. Cleanup is complete; runtime
and profile remain accepted OFF and the critical action is absent. No trial/probe is running; repeat cancellation only in a clearly identified
operator-coordinated window. Optional
controls remain OFF; fresh-auth/cancel acceptance remains open.
