# Agent containment and deployment

- **Containment:** OpenShell CLI and desktop launchers restrict filesystem/network
  access and keep reusable credentials outside workers. See the
  [operating guide](../../../../docs/AGENT_SANDBOX.md) for launchers and boundaries.
- **Bounded diagnostics:** A separately authorized broker exposes named diagnostic
  operations rather than arbitrary privileged commands. Workspace visibility does
  not grant broker authority. Each request requires `--reason`; audits retain
  only its hash, never its text. See the operating guide and [GUI diagnostics](gui-diagnostics.md).
- **Authenticated immutable deployment:** The deployment client freezes permitted
  Git-visible worktree changes; the protected controller binds authentication,
  exact source, closure and current baseline before activation. Dirty content is
  supported. See the operating guide for deployment and rollback.
- **Optional security review:** `securityReview.enable` is disabled by default.
  AI judgment supplements authenticated deployment when enabled; the current
  optional-review workflow has no live runtime acceptance. See
  [acceptance evidence](../../../../docs/AGENT_SANDBOX_ACCEPTANCE.md) and
  [review policy](review-policy.md).
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
