# Optional deployment security review

`services.phoenixDeployment.securityReview.enable` remains off by default. Its
legacy `modelReview.enable` option is an alias. Authentication, dirty-source
freezing, exact closure binding, disruption checks, reservations and rollback
apply independently of AI. Routine updates use the deterministic validator with
zero AI and Polkit calls.

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
untouched; review remains OFF. Full root-to-worker/new-build review, activation
and fallback authentication remain pending, rather than implied by this receipt.


## Root process integration trial (prepared, not executed)

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
0444 and traversable for the configured builder/reviewer. Real production process,
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
therefore fails closed before another CLI invocation. Protected-UID gate traversal
still needs the actual trial; offline tests prove normal mode ownership layout,
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

The supported Polkit integration invocation reached its 180-second deadline
(exit 124, no helper receipt). Immediately before expiry, process inspection
showed only the waiting pkexec and no trial Python process: the fixture/reviewer
had not started, so this attempt made no model invocation or activation. Do not
retry automatically. When the operator is available, recheck active baseline,
profile and cached candidate, then reissue the same immutable integration entry
through native Polkit. No new sign-in, source reconstruction or implementation
workaround is needed. Earlier protected-adapter and zero-AI root-checkpoint
receipts remain valid within their documented narrower scopes.
