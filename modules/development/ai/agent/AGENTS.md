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
