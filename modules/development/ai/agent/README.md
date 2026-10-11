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
  not grant broker authority. Each request requires `--reason`; audits retain
  only its hash, never its text. See the operating guide and [GUI diagnostics](gui-diagnostics.md).
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
  [review policy](review-policy.md).
- **Approval reuse and fallback:** Root-owned approval records bind exact immutable
  source, closure, target and installed policy; retain at most 32 records. Exact
  candidate reuse skips AI. Context uses the smallest diff among the activated
  snapshot and same-branch approved snapshots, which need not be the latest
  approval. Branch labels select context and grant no authority. Review denial or
  error blocks activation and returns an exact pending decision; explicit
  `phoenix-deploy-review --security-override PENDING_NONCE` requires separate
  authentication and accepts only that protected source/closure/action. Approval
  remains reusable after an activation failure; current baseline/profile checks
  still apply. Never include secrets in task reasons.
- **Acceptance limits:** `python3 -B tests/agent-deployment.py` exercises the
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
- **Planned coordination:** Longer testing reservations, individual task/caller
  identity and disruption checks remain future work. The current deployment lock
  spans a command, not an agent's later runtime validation; see
  [planned coordination](AGENTS.md#planned-testing-reservation-not-implemented).

- **Operator identity prerequisite:** Immutable deployment configuration separates
  `operatorUid` (retained reviewer-login ownership and authenticated manual/critical
  override caller) from `clientUid` (kernel socket caller and pending request owner).
  Legacy immutable configurations retain their validated single UID. Both UIDs still
  resolve to the operator today; sockets and launchers retain their existing access.
  A dedicated agent account and protected native/OpenShell launch transport are not
  implemented. UID checks do not identify an executable or prevent operator malware
  from invoking an allowed launcher. A future migration must prove retained auth,
  app-server/TTY transport, workspace DAC and agent-owned rootless Podman mapping
  together before restricting broker callers.

- [Testing reservations](reservations.md): default-off management through the existing
  admin broker and fixed authenticated operator helpers; deployment enforcement and
  complete runtime acceptance remain pending.
