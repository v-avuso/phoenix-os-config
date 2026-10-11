# Agent containment and deployment

- Deployment security review is optional and disabled by default. Keep all review
  authority, prompts, cache and override UI behind `securityReview.enable`.
  Authenticated deployment, immutable source/closure binding and rollback are
  independent safeguards; disabling AI must not grant unattended root access.
- Review the frozen repository diff for security, not code quality or distributor
  package contents. Request only relevant bounded context; never automatically
  send the entire repository or create dependency-review batches. Define cost
  limits and exercise the actual controller workflow before enabling on a live host.
- Freeze Git-visible working-tree changes before builds, including new files and
  deletions. A clean commit is not an activation prerequisite. Ignore branch names
  as authority; only root-owned exact source/closure/policy checkpoints authorize reuse.
- When changing the review boundary, exercise controller → worker → adapter →
  checkpoint together in `tests/agent-deployment.py`, not only mocked worker
  envelopes. Keep fixture ownership/store/build/model/activation stubs explicit;
  passing fixtures do not establish retained-auth or live OS acceptance. Check
  incremental context against the smallest-diff checkpoint heuristic, not an
  assumed latest approval.
- Preserve retained authentication. Diagnose readiness and typed failure stages
  before asking for sign-in; never log tokens, account responses or raw auth stderr.
- New containment/shutdown behavior stays opt-in until active workload cleanup,
  final log delivery and real GUI/model workflows pass isolated acceptance.

## Workspace access and deployment coordination

- Configure agent-visible project directories through `phoenix.agent.workspaces`;
  OpenShell filesystem policy and mounts enforce that boundary. Keep personal home
  data outside those mounts. Broker caller authorization is a separate boundary;
  workspace access does not grant privileged operations.
- Agents requesting deployment must provide the task, intended action and reason,
  plus the source worktree. Prefer `test` during development and `switch` after
  integration into main. Reasons and branch labels are context, never authority.
- Freeze the selected worktree before review/build and activate only the resulting
  approved immutable source/closure. Include permitted uncommitted changes; later
  edits must not alter a reviewed deployment. Reviewer Git branches are unnecessary.

### Source selection

- `phoenix-build --branch NAME` (also dry-build/test/switch/boot) or
  `phoenix-rebuild --worktree /absolute/path --print build` selects an existing
  worktree of the configured repository without switching the user's checkout.
  Put dispatcher selectors before forwarded nixos-rebuild options. Keep the
  configured `repoDirectory` / `PHOENIX_REPO_ROOT` default when no selector is given.
- `--branch NAME` must match exactly one existing local-branch worktree;
  unknown, unmounted and ambiguous branches fail. `--worktree PATH` must name a
  registered worktree of the configured repository. No checkout is created.
  Dirty tracked content is included; ordinary Git-flake builds omit untracked
  files until staged. Never use `path:.` to work around this.
- For authenticated immutable deployment, use
  `phoenix-deploy-review --worktree /absolute/path --target metal --action test --reason "authorized task purpose"`
  (or `--branch NAME`). Its existing snapshot
  includes permitted Git-visible dirty/new content. With the deployment module,
  `phoenix-test --reason "authorized task purpose"` (also switch/boot) uses that
  same frozen authenticated client. These actions reject nixos-rebuild option
  tails; build/dry-build still forward them. Without the deployment module the
  packaged wrappers explicitly retain the legacy nixos-rebuild route. A missing
  or failed configured helper never falls back. Branch labels confer no authority.
- OpenShell packages the same commands and deployment client, with its existing
  deployment socket mount. Sources must be in configured mounted workspaces;
  external managed worktrees under `~/.codex/worktrees` are not mounted by
  default and cannot be selected from OpenShell. Disabled AI requires native host Polkit authentication;
  sandbox activation rejects with host guidance because host wrappers/D-Bus are
  not mounted. Do not mount authentication or bypass containment to fix this.
  Enabled-review socket routing is packaged, but live runtime acceptance remains
  unverified; identity and testing reservations remain later work.
- `phoenix-admin --reason "authorized diagnostic purpose" OPERATION ...` requires
  a bounded nonempty reason without control characters. The broker verifies it
  before dispatch and audits its hash only. Never include secrets in reasons.

### Planned testing reservation (not implemented)

- Add a host-wide broker-owned testing reservation spanning activation and runtime
  validation, not just the deployment command. Agents acquire it before testing,
  report completion and release it afterward. Competing test/switch/boot/rollback
  operations must respect the same reservation; builds without activation may proceed.
- Bind reservations to authenticated callers and individual task/session tokens,
  not branch names or shared UID alone. Include bounded expiry/renewal and explicit
  operator recovery for crashes; expiry must not automatically switch or roll back
  the live system. Reject stale owners and changed activation baselines.
- Keep reservation coordination separate from AI security judgment. Reviewer failure
  requires explicit authenticated human approval, never unattended fallback. An
  approved request still requires disruption checks and a valid reservation.
- Before enabling, test two competing agents, completion/release, owner loss/expiry,
  stale requests, human recovery and edits after snapshot creation. Keep experimental
  controls disabled on the daily-driver system until their actual workflow is verified.
