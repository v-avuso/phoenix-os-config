# Agent containment and deployment

- **Containment:** OpenShell CLI and desktop launchers restrict filesystem/network
  access and keep reusable credentials outside workers. See the
  [operating guide](../../../../docs/AGENT_SANDBOX.md) for launchers and boundaries.
- **Protected identity (experimental):** Optional `identity.enable` separates the
  OpenShell service/workload host UID from Native Codex, with fixed authenticated
  launch transport and offline retained-state preparation. Disabled by default;
  see [identity usage, compatibility and acceptance](identity.md).
- **Bounded diagnostics:** A separately authorized broker exposes named diagnostic
  operations rather than arbitrary privileged commands. Workspace visibility does
  not grant broker authority. Each request requires a nonsecret bounded `--reason`.
  The [authorization module](authorization/README.md) owns installed decisions,
  native human authentication and structured root audit metadata. See also
  [GUI diagnostics](gui-diagnostics.md).
- **Authenticated immutable deployment:** The deployment client freezes permitted
  Git-visible worktree changes; the protected controller binds authentication,
  exact source, closure and current baseline before activation. Dirty content is
  supported. See the operating guide for deployment and rollback.
- **Optional security review:** `securityReview.enable` is disabled by default.
  It reviews the frozen local diff and file/line index, with at most two controller
  CLI invocations and one explicit context round (eight ranges, 128 KiB). Input
  including policy/schema is capped at 1 MiB; output and execution are bounded.
  Native CLI internal API requests and cumulative tokens are not hard capped.
  The approximately 24,000-token diff warning is an estimate, not a gate.
  No automatic upstream dependency batches run; routine updates use zero AI.
  See
  [acceptance evidence](../../../../docs/AGENT_SANDBOX_ACCEPTANCE.md) and
  [review usage and baseline adoption](security-review.md) and
  [review policy](review-policy.md).
- **Approval reuse and fallback:** Root-owned approval records bind exact immutable
  source, closure, target and installed policy; retain at most 32 records. Exact
  candidate reuse skips AI. Context uses the smallest diff among the activated
  snapshot and all independently approved same-policy/target snapshots across
  branches, which need not be the latest approval. Branch labels grant no authority. Review denial or
  error blocks activation and returns an exact pending decision; explicit
  `phoenix-deploy-review --security-override PENDING_NONCE` requires separate
  authentication and accepts only that protected source/closure/action. Approval
  remains reusable after an activation failure; current baseline/profile checks
  still apply. Never include secrets in task reasons.
- **Acceptance limits:** `python3 -B modules/development/ai/agent/tests/agent-deployment.py` exercises the
  controller, worker, review adapter and checkpoint together with disposable state
  and explicit OS ownership/store/build/model/activation stubs. The retained login
  has moved to the protected controller; existing helpers offer no isolated
  authenticated reviewer diagnostic after migration. Real retained-auth review,
  live isolation and OS activation remain unverified. Use retained authentication
  and diagnose readiness/failure stages before requesting sign-in.
- **Explicit source selection:** Shared rebuild commands and the authenticated
  deployment client accept branch/worktree selectors without switching checkouts.
  Configured native and OpenShell Phoenix activation wrappers submit frozen
  requests through the existing deployment client, require `--reason`, and reject
  nixos-rebuild argument tails. Build/dry-build retain argument forwarding.
  OpenShell can select only mounted workspaces; managed external worktrees are
  absent by default. Disabled AI requires native host Polkit; sandbox clients fail with host guidance. See [agent instructions](AGENTS.md#source-selection) for usage,
  dirty-source behavior and existing-worktree constraints.
- **Testing coordination:** Default-off reservations span activation and later runtime
  validation. Private task capabilities, a service-owned mutation/rollback gate and
  current baseline checks enforce exclusivity; see [reservations](reservations.md).
  Live VM/Polkit/systemd acceptance remains pending.

- **Operator identity (experimental):** Dedicated account and native/OpenShell
  transport are prepared and default off. Distinct caller/operator authority and
  migration constraints are documented in [identity](identity.md); isolated live
  acceptance remains pending.
- **Protected desktop units (experimental):** Default-off
  `services.phoenixDeployment.disruptionGuard.enable` compares concrete active
  desktop/session units before dispatch and inside the actual activation helper.
  Exact fresh operator exceptions remain independent of security approval.
  Arbitrary activation shell effects are outside its proof; see [disruption](disruption.md).

- [Testing reservations](reservations.md): default-off management through the existing
  admin broker and fixed authenticated operator helpers, deployment lifetime gating
  and runtime ownership; complete live acceptance remains pending.

Source transport uses [transport.json](transport.json): at most 4MiB UTF-8 file
content and 32MiB serialized JSON, including escaping and metadata. Deployment
clients, controller and routine updater share these bounds. Capacity failures
use `source-transport` with `source-capacity-exceeded` or `wire-capacity-exceeded`;
the separate 1MiB AI input budget retains `review-context-oversized`.
