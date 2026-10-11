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

### Planned interface and testing reservation (not implemented)

- Extend the shared Phoenix dispatcher, rather than duplicating wrappers, to resolve
  an optional branch/worktree selector. Resolve an existing worktree explicitly so
  its uncommitted changes are included; a bare branch ref names committed content
  only. Reject ambiguous selections. Preserve the configured-checkout default until
  an explicit main-default migration is agreed; never silently switch the checkout.
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
