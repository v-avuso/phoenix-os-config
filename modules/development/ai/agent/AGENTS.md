# Agent containment and deployment

- Deployment security review is optional; its reusable option defaults OFF. Keep all review
  authority, prompts, cache and override UI behind `securityReview.enable`.
  Authenticated deployment, immutable source/closure binding and rollback are
  independent safeguards; disabling AI must not grant unattended root access.
  Explicit trust-active seeding needs fresh native authentication, only the actual
  runtime source/closure and a final locked recheck; it is never per-generation
  automatic approval. See [security review usage](security-review.md).
- Review the frozen repository diff for security, not code quality or distributor
  package contents. Request only relevant bounded context; never automatically
  send the entire repository or create dependency-review batches. Define cost
  limits and exercise the actual controller workflow before enabling on a live host.
- Freeze Git-visible working-tree changes before builds, including new files and
  deletions. A clean commit is not an activation prerequisite. Ignore branch names
  as authority; only root-owned exact source/closure/policy checkpoints authorize reuse.
- Before declaring final integration/updater readiness, synchronize intended tracked
  content with the activated/staged approved source: new documentation commits also
  change that boundary. Report the final binding in the journal/operator handoff;
  do not start a new tracked receipt edit merely to refresh its own source hash.
- When changing the review boundary, exercise controller → worker → adapter →
  checkpoint together in `tests/agent-deployment.py`, not only mocked worker
  envelopes. Keep fixture ownership/store/build/model/activation stubs explicit;
  passing fixtures do not establish retained-auth or live OS acceptance. Run the
  packaged offline fixture as the actual protected UID before model use; keep
  request-parent locks inside its owned temporary tree, not shared `/tmp`. Check
  incremental context against the smallest content/mode diff among independently
  approved same-policy/target checkpoints across branches, not an assumed latest
  approval. A merged/combined new source still requires residual integration review.
- Keep operator authentication/migration ownership separate from broker caller UID.
  When changing agent identity, test distinct UIDs: operator-owned retained auth
  and critical override must remain operator authority; pending requests retain
  their original configured client owner. Prove mapped launch paths before
  restricting broker callers. Use explicit pipes/DEVNULL for noninteractive
  guest probes and test PTY behavior separately, so inherited driver terminals do
  not confound admission tests. Emit bounded nonsecret synthetic failure state
  before assertions in VM build logs; failed-build artifacts may be inaccessible.
- Disruption guarding is default off and protects concrete immutable active unit
  artifacts only. Query/layout uncertainty requires a fresh exact operator exception;
  never describe it as proof against arbitrary activation shell effects. Read
  `disruption.md` for its boundary; keep security approval independent and repeat
  inspection inside the actual helper under its existing activation guard.
- Protected identity remains off until distinct-UID launcher → OpenShell → broker,
  retained model auth, GUI/TTY and workspace/history acceptance pass in isolation.
  Its first mode requires the existing active history handoff; never copy whole
  profiles or adopt operator Podman storage to repair identity access. Re-audit
  globally enabled user services/sockets when changing protected-manager composition;
  its children must retain the same home masking and storage environment.
- Retained gateway cutover requires an explicit offline/quiescent boundary;
  descriptor-relative relocation/chown cannot revoke open FDs or historical copies.
  Cross-filesystem cutover uses only the pinned DB/KEK layout through fixed cp,
  protected staging, exact streaming verification and atomic publication; retain
  original source and never generalize this to profile/container reconciliation.
- Nix may package Python entry points as individual store files. Pass helper paths
  explicitly in immutable config and test an isolated entry point; do not assume
  sibling files exist in its store directory. For checkpoint fingerprints, package
  embedded helper content individually: whole-repository source prefixes otherwise
  invalidate reuse on unrelated changes. Test relocation and actual helper changes;
  retain helper-byte hashing rather than normalizing away changed authority.
- Pass generated gateway configuration directly by immutable store path. OpenShell
  0.1.2 preflight rejects symlinks (including NixOS `/etc` links); preserve that
  strict check rather than copying configuration or skipping preflight.
- OpenShell 0.1.2 nonterminal gRPC exec buffers stdin until EOF. Give probes
  requiring no input explicit DEVNULL/`</dev/null`; otherwise a blocked probe
  does not establish readiness or authentication failure. Fully redirect all
  descriptors of background capture groups so they cannot retain driver pipes.
- Preserve retained authentication. Diagnose readiness and typed failure stages
  before asking for sign-in; compare the recorded instance to the installed
  launcher revision before attributing an old startup failure to current auth.
  Never log tokens, account responses or raw auth stderr.
- For missing desktop projects, compare typed native/local metadata with declared
  workspace eligibility and the import marker before changing access. Import only
  newly seen eligible metadata under the GUI lifetime lock; preserve sandbox-owned
  edits/removals and let the pinned desktop own its app-server migration.
- Probe readiness through `inspect_layout` on actual supported paths before a cold window; it reads bounded config and layout only, not writer quiescence or database integrity.
  Keep non-symlink history rules; allow exact upstream coordination files as auxiliary inputs, never copied database payloads.
- When sharing desktop metadata, mount its directory for atomic replacements and
  hold one host GUI lifetime lock across both reviewed entry points before exposing
  it. History's shared lifecycle lock permits concurrent clients and cannot protect
  whole-map GUI writers. Keep native fallback independent; test private worker
  parent mounts and exact CLI history read/resume without treating them as live GUI
  or model-turn acceptance.
- New containment/shutdown behavior stays opt-in until active workload cleanup,
  final log delivery and real GUI/model workflows pass isolated acceptance.

## Workspace access and deployment coordination

- Configure agent-visible project directories through `phoenix.agent.workspaces`;
  OpenShell filesystem policy and mounts enforce that boundary. Keep personal home
  data outside those mounts. Broker caller authorization is a separate boundary;
  workspace access does not grant privileged operations. For linked worktrees,
  retain mounted common Git metadata and test the actual selector/client route
  plus sibling-profile isolation; do not substitute the human rebuild route or
  widen Git trust globally to make a fixture pass.
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
  (or `--branch NAME`). Its existing snapshot includes permitted Git-visible dirty/new
  content. Human `phoenix-test`/`phoenix-switch`/`phoenix-boot` retain terminal
  `nixos-rebuild --sudo`, selectors and rebuild-option forwarding, with no required
  reason. Agents must use `ai-broker --task TASK --reason "authorized task purpose" -- phoenix-test ...`;
  its fixed mapping calls the authenticated immutable client directly, accepts only
  bounded selectors/reservations, and never falls back to human sudo. Reasons are
  context, not identity or privilege. Broker review/reservations do not constrain
  native administrator sudo; shared-UID instructions are not identity enforcement.
- OpenShell's explicit broker uses the sandbox deployment client and existing
  deployment socket. Sources must be in configured mounted workspaces; repository
  defaults include the narrow `~/.codex/worktrees` root, not the full profile. Disabled
  AI requires native host Polkit; sandbox clients reject with host guidance. Do not
  mount authentication or bypass containment to repair this. Identity/reservation
  live acceptance remains separate.
- Agents use `ai-broker --reason "authorized diagnostic purpose" -- phoenix-admin OPERATION ...`;
  the legacy `phoenix-admin --reason ...` interface remains compatible and requires
  a bounded nonempty reason without control characters. The broker verifies it
  before dispatch through the installed [authorization policy](authorization/README.md).
  Root authorization audits retain validated nonsecret reason metadata. Never include
  secrets in reasons.

### Testing reservations (implemented; live acceptance pending)

- The opt-in implementation is documented in `reservations.md`; keep it disabled
  until isolated live VM/Polkit/systemd acceptance passes.
- Put mutation/rollback gate ownership inside the actual transient activation helper;
  a controller flock or FD passed to systemd-run cannot bind the service lifetime.
  Exercise controller death and operation-child timeout before claiming exclusion.
- Preserve the fixed actual-service activation guard across resource mapping changes
  and reservation ON/OFF transitions. Resource-specific locks alone can split across
  generations; the first installation from an unguarded version needs quiescence.
- Integrate a host-wide broker-owned testing reservation spanning activation and runtime
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

- Keep source/JSON transport capacity in `transport.json` separate from AI context
  and cost budgets. Package its immutable path explicitly for standalone Python
  entry points; verify updater, client and controller agree before deployment.

- When service and contained client identities differ, derive narrowly named
  operation roles and the service user from one declarative account owner; do not
  derive policy by inspecting a service whose ExecStart packages that policy. Test
  combined NixOS evaluation and kernel-peer admission
  through the actual controller/validator. Socket group membership or metadata
  admission must not widen diagnostic or ordinary deployment execution rights.

- Explicit active-baseline trust must validate immutable provenance selected from
  the actual running closure; reproducing a store flake can require IFD or lose
  Git metadata. Keep provenance as identity evidence, with fresh operator trust
  supplying approval; missing old-generation provenance must fail closed.

- For exact OpenShell binary admission, authorize the kernel executable after
  package wrappers exec, not the public launcher. Keep provider and network policy
  identities centralized and verify `/proc/<pid>/exe` against the packaged launcher
  at build time; never repair wrapper mismatches with broader path globs.

- When isolating shared desktop preferences, trace the actual persisted-atom
  setters as well as picker reads/defaults. Permission selection and preferred-mode
  keys can be separate shared writers; guard pinned owners and resumed-thread
  reconciliation. Test restricted/unknown current profiles against saved host-wide
  modes; current chat policy must outrank stale preferences. Characterize the pinned
  mode decoder through outgoing permissions: Approve for me is guardian-approvals,
  not auto. Verify Native return.

- Sandbox revision replacement must hold the setup lock and a separate exclusive
  instance-use lock before stopping an old instance; retain shared use locks for
  supported CLI/app-server transport lifetimes. History/GUI locks have different
  ownership and must not block Native fallback. Test real competing processes,
  not only setup calls. First adoption requires explicit operator quiescence:
  older launchers and manual OpenShell clients do not participate in this lock.

- Once an authorized Polkit request has started, let its native dialog collect
  authentication and await the result. Do not add redundant availability or
  confirmation questions; surface expiry or failure when it occurs.
  For cancellation acceptance, establish explicit readiness and identify the
  particular critical dialog before issuing it; do not interleave approval dialogs
  with different cancel instructions that depend only on chat labels.

- Check the selected clock before guarding a systemd rollback timer. For the
  non-waking timer used here, compare `NextElapseUSecMonotonic` with
  `time.monotonic_ns()`, not `/proc/uptime` (which includes suspend). Verify the
  clock and armed deadline before a privileged trial.

- Before expanding shutdown repairs, check the pinned contracts in
  `shutdown-acceptance.md`: administrative exit-report skipping prevents hangs,
  and the gateway log tail is memory-only. Validate supported delivery semantics
  before treating a negative probe or post-restart absence as a new defect.
