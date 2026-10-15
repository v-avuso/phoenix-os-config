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
configuration evidence; actual retained-auth CLI behavior, Polkit, live isolation
and activation acceptance remain pending.

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

The runner validates immutable public paths and the protected UID/home before
calling the fixture. It reviews one comment-only change, checks a bound verdict,
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
