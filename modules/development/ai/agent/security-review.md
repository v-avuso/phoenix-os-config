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
