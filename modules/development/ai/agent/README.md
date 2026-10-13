# Agent containment and deployment

## Intentions

- Make the sandboxed GUI and CLI the everyday defaults, with a functioning user
  experience and the least necessary filesystem, network and other authority.
  Containment reduces blast radius; it does not promise anonymity or perfect isolation.
- Preserve native GUI and native CLI as independent OpenShell fallback/recovery
  paths. A failure of the contained backend must not remove the native lifeline.
- Reuse maintained Nix-Bwrapper/Flatpak foundations for desktop containment rather
  than accumulating custom sandbox machinery or state synchronization patches.
- Prefer shared chats/history and consistent preferences across variants without
  requiring perfect simultaneous synchronization. One active variant is acceptable
  when switching offers an explicit keep-current or gracefully-close-and-switch
  choice; never force termination or discard ongoing work.
- Preserve native and sandbox-owned state. Avoid whole-profile reconciliation and
  keep native credentials outside the contained CLI; share only the data needed
  for the agreed workflow.

Shared state is opt-in and disabled by default; its owner-mediated switching
implementation is prepared for isolated acceptance, not enabled on the installed system.
Real GUI sharing and switching acceptance remain pending. Native GUI uses native
CLI independently of OpenShell; sandbox GUI retains its contained backend.

## Shared desktop state (opt-in; GUI acceptance pending)

Set `phoenix.agent.gui.sharedState.enable = true` only for a planned cold trial.
Both reviewed GUI launchers require validated `codex-history-enable` readiness
and hold one host exclusive GUI lock for the process lifetime. A same-variant
launch asks the current owner to restore its window; `--new-instance`
uses the pinned app's existing new-window callback. A cross-variant launch offers
**Keep current** or **Close and switch** in the running app. Closing uses ordinary
`app.quit()`, retaining upstream active-work confirmation; cancellation or failure
keeps the current owner and prevents the new variant from starting. The guard
waits at most 45 seconds for exclusive-lock release and checks the owner nonce
before starting. It never forcibly closes an application. The private local owner
socket accepts only activation, new-window, switch and typed open-link actions.
Repeated launches forward a single `codex://` or `codex-browser-sidebar://` URI
(maximum 4096 UTF-8 bytes, no userinfo or whitespace/control characters) through the exact
pinned second-instance callback, preserving upstream link validation. Other URI
schemes, multiple links and oversized links fail explicitly without logging link
contents. Cross-variant links remain in the original startup arguments after the
old owner closes; cancelling the switch keeps the owner and starts no new app.
The socket caps JSON messages at 32 KiB, connections at four and each connection
at an absolute 45-second deadline. Native support has no OpenShell
dependency; each variant retains its separate Chromium profile.
The history shared lifecycle lock remains separate and permits CLI clients.

The sandboxed frontend mounts the native `~/.codex` **directory**, so the pinned
GUI's atomic metadata replacements share projects and chat/project pins. This
trusts the frontend with native Codex data, including native auth/config files;
it does not grant that directory to the contained CLI. Chromium profiles stay
separate. Startup metadata imports are skipped in shared mode. Native GUI keeps
its native backend, and native CLI remains the independent fallback. Backend
preferences are still separately owned; this option does not synchronize them.

Existing sandbox-only chats remain in retained containers; inventory and preserve
them before adopting the native history baseline. No database/profile merge runs.
Sharing preserves saved conversations, not running commands or provider prompt
caches. Resume requires the chat's workspace/rollout paths to exist inside the
selected backend's allowed mounts. See [cold handoff and proof](history-layout.md).

## Current behavior

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
  requests through the existing deployment client with neutral invocation context
  when no reason is supplied, and reject
  nixos-rebuild argument tails. Agents use the [bounded `ai-broker` interface](authorization/README.md#command-interface). Build/dry-build retain argument forwarding.
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
