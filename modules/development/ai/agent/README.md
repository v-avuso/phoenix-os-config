# Agent containment and deployment

For operator setup and testing, see the short [shared chats trial guide](USER_GUIDE.md).
For technical continuation and evidence limits, see [HANDOFF.md](HANDOFF.md).
For remaining epic scope, rough completion/complexity estimates and switch gaps, see [BACKLOG.md](BACKLOG.md).

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

The repository enables the accepted one-active GUI sharing workflow with explicit
operator approval for persistence. The reusable module option still defaults off.
In the 2026-10-15 trial, Sandbox preselected Custom, `pwd` returned
`/home/v/repos/code/phoenix-os-config`, and Native resumed with
workspace-write/auto_review. This establishes the primary shared-chat/tool flow,
not every archive/pin action or optional broker control. The accepted configuration
is installed in both the running system and next-boot profile. See
[the checkpoint](HANDOFF.md). Native GUI and CLI remain independent OpenShell
recovery paths; the sandbox GUI retains its contained backend.

The Codex package exports one exact kernel executable identity for OpenShell's
provider and network policies. Policy builds run the packaged app-server locally
and check `/proc/<pid>/exe`; a changed upstream wrapper layout fails the build
rather than silently losing model egress. This check does not contact a provider
or establish live model-turn acceptance.

The sandbox desktop defaults new chats and resumed ordinary workspace chats
(including **Approve for me**) to **Custom (config.toml)** using its existing worker settings: `danger-full-access`,
`on-request`, and `auto_review`. OpenShell
remains the filesystem/network boundary; Codex adds no inner workspace/read-only
sandbox, and actions permitted by that outer boundary do not acquire automatic
command review. **Approve for me** supplies a workspace-write override, whose
nested Bubblewrap user namespace OpenShell denies. The immutable Sandbox desktop
adapter uses separate permission preference keys;
Native's package and saved preferences remain unchanged. A chat's current explicit
or restricted policy outranks stale host-wide preferences; deliberate picker
changes still apply to that chat. Named/unknown profiles are not automatically
widened. Read-only
still requires an unsupported nested sandbox here and needs an operator decision.
Shared chats retain upstream thread permission history, so verify effective Native
permissions on return; preference isolation alone is not runtime acceptance.

The worker image and sandbox GUI use `time.timeZone` with pinned Nixpkgs timezone
data (UTC when unset). The worker's immutable `/etc/localtime` also handles SSH
sessions that discard timezone environment variables. This changes local time
rendering, not the host clock or Native configuration.

## Backend integration choice

- **Current boundary:** The sandbox desktop uses OpenShell's SSH proxy already;
  its extra adapters reconcile desktop account/routing behavior with opaque
  worker credentials. Nix-Bwrapper owns frontend permissions independently.
- **Reuse alternative:** [Codex Remote SSH](https://learn.chatgpt.com/docs/remote-connections)
  and [NVIDIA's pinned app-server example](https://github.com/NVIDIA/OpenShell/blob/v0.1.2/examples/codex-app-server/README.md)
  provide maintained building blocks, not a verified equivalent of this combined
  desktop/history setup. Remote SSH selects a remote host; selection alone does
  not prevent local task execution. Its persistent server bootstrap also needs
  the existing history/authentication initialization and lifecycle guarantees.
- **Decision:** Retain the accepted bridge path: Sandbox automatically selects
  Custom, actual `pwd` succeeded, and return to Native was accepted. It already
  uses SSH; there is no current known routing failure. Reassess if future repair
  requires substantial new mediation. Any replacement needs a small
  isolated proof of retained login, an actual remote task, chat continuation and
  outage behavior before migration or supporting infrastructure.
- **Cost boundary:** Prioritize one usable sandbox desktop with native CLI as a
  repair lifeline. Further simultaneous-GUI parity and optional reviewer controls
  remain separate work beyond the accepted primary GUI workflow.

## Active-client replacement guard

Supported Sandbox CLI/app-server clients retain a separate instance-use lock for
their transport lifetime. Revision-changing launches require exclusive ownership
before replacing a backend and fail busy while another supported client uses it.
Same-version clients remain concurrent; Native GUI/history locks are independent.
Transport supervision preserves terminal descriptors, normal exit codes and signal
forwarding using the existing parent-death cleanup.

First adoption requires a quiescent operator cutover: older launchers and manual
OpenShell clients do not hold this lock. Isolated process tests cover locking and
transport behavior. The guard is persistently installed after a quiescent cutover,
real nonsecret home-canary/repository access checks and held/released lifetime-lock
acceptance; installed launcher and runtime/boot closure were verified. See
[installed evidence](HANDOFF.md#recorded-installation-checkpoints). It is
not a guarantee against older/manual launchers, manual lifecycle operations or
atomic cleanup after SIGKILL.

## Shared desktop state (primary GUI workflow accepted)

`modules/development/ai/default.nix` enables
`phoenix.agent.gui.sharedState.enable = true` for this repository. Its reusable
option remains default off. The accepted setting is persistently installed under
explicit operator approval. A new installation still needs
the coordinated [cold handoff](history-layout.md#explicit-cold-handoff). Do not
repeat it on this already prepared shared store.
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

## Architecture and dependencies

The AI composition module selects repository defaults; these owners retain distinct
containment, decision and execution responsibilities.

| Responsibility | Owner | Dependencies and boundary |
| --- | --- | --- |
| Authorization | `authorization/` | Installed decision policy and shared request library; consumes security-review selection and declared caller/operator identities. |
| Diagnostics | `broker.nix`, `admin.py` | Authorization policy/library, fixed root socket dispatcher and native Polkit helpers; seven typed operations. |
| Deployment and security review | `deployment.nix`, `deployment.py`, `security-review.nix` | Authorization, immutable source/build binding, activation/rollback helpers; optional isolated reviewer and exact approval checkpoints. |
| Frozen source format | [`source-manifest.py`](source-manifest.md) | Preserves regular files and safe internal file links across snapshot, review, transport and store verification; documents old-validator recovery. |
| OpenShell runtime | `default.nix`, `image.nix`, `launch.py` | Pinned OpenShell and Podman, workspace/network policy, history and broker clients; enforces the worker boundary. |
| Bubblewrap GUI | `gui.nix`, `gui-*.py` | nix-bwrapper desktop preset and pinned Flatpak manifest; CLI/HTTP relays enter OpenShell, with separately controlled GUI state sharing. |
| Experimental controls | `identity.nix`, `reservations.nix`, `shutdown-ordering.nix`, deployment disruption guard and authorization explanation | Optional runtime identity/lifetime, deployment coordination/inspection and native presentation extensions; remain off independently of enabled security review and GUI sharing. |

## Current behavior

- **Containment:** OpenShell CLI and desktop launchers restrict filesystem/network
  access and keep reusable credentials outside workers. See the
  [operating guide](../../../../docs/AGENT_SANDBOX.md) for launchers and boundaries.
- **Protected identity (experimental):** Optional `identity.enable` separates the
  OpenShell service/workload host UID from Native Codex, with fixed authenticated
  launch transport and offline retained-state preparation. Disabled by default;
  see [identity usage, compatibility and acceptance](identity.md).
- **Bounded diagnostics:** A separately authorized broker exposes named diagnostic
  operations rather than arbitrary privileged commands. `phoenix-authorize` is the
  neutral public gate; `ai-broker` remains a compatible alias. The separate default-off
  [exact command registry](authorization/README.md#exact-registered-commands-experimental-off)
  adds fixed installed ELF operations through the capable deployment controller;
  no live entries or general shell are installed. Workspace visibility does
  not grant broker authority. Each request requires a nonsecret bounded `--reason`.
  The [authorization module](authorization/README.md) owns installed decisions,
  native human authentication and structured root audit metadata. Its default-off
  explanation adds a readable native question only for opted-in broker requests
  requiring human authentication; isolated GUI acceptance remains pending. See also
  [GUI diagnostics](gui-diagnostics.md).
- **Authenticated immutable deployment:** The deployment client freezes permitted
  Git-visible worktree changes; the protected controller binds authentication,
  exact source, closure and current baseline before activation. Dirty content is
  supported. See the operating guide for deployment and rollback.
- **Optional security review:** the reusable `securityReview.enable` option defaults
  OFF; this repository explicitly selects ON after controlled live review/recovery
  acceptance. Persistent installation was verified at checkpoint `efcd866`
  (`cq08hmp...`); use runtime/profile, activated provenance and root journal for
  the latest binding rather than treating this receipt as a moving generation.
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
  candidate reuse skips AI. Context uses the smallest diff among independently
  approved same-policy/target snapshots across
  branches, which need not be the latest approval. Branch labels grant no authority. Review denial or
  error blocks activation and returns an exact pending decision; explicit
  `phoenix-deploy-review --security-override PENDING_NONCE` requires separate
  authentication and accepts only that protected source/closure/action. Approval
  remains reusable after an activation failure; current baseline/profile checks
  still apply. Never include secrets in task reasons.
  Activation alone grants no review-context trust; absent a matching protected
  checkpoint, deployment stops with `approved-checkpoint-required`. See the
  [reviewed recovery transition](source-manifest.md#one-time-recovery-from-an-older-validator).
- **Acceptance limits:** Offline fixtures cover controller/worker/checkpoint and
  failure composition with explicit stubs. Actual protected retained-auth review,
  root process/build/worker/adapter/checkpoint reuse, and recorder-based reservation
  systemd lifetime and actual guest activation/failure-rollback trials passed; see [review evidence](security-review.md) and
  [reservation evidence](reservations.md). The isolated deployment socket VM also passed
  kernel peer admission and denial cases with model/activation doubles. Controlled host
  reviewed deployment/recovery passed; critical fallback authentication and optional
  control workflows retain separate acceptance limits. Optional
  controls stay OFF; these bounded trials do not establish full live readiness.
- **Explicit source selection:** Shared rebuild commands and the authenticated
  deployment client accept branch/worktree selectors without switching checkouts.
  Human Phoenix activation retains terminal `nixos-rebuild --sudo` and option
  forwarding. Agents use the [bounded `ai-broker` interface](authorization/README.md#command-interface),
  which directly submits frozen requests to the immutable deployment client. It
  rejects rebuild-option tails and never falls back to the human sudo route.
  OpenShell can select only mounted workspaces. Repository composition appends
  `~/.codex/worktrees` to the code/Projects defaults; explicit operator workspace
  lists replace those defaults. The directory must already exist and resolve
  canonically. Only that subtree is mounted, not sibling CLI profile/auth data;
  the trusted GUI frontend retains its separate shared-profile contract. Linked
  worktrees also require their common Git directory under an approved mount.
  Disposable current-UID tests cover launch cwd, common Git metadata, sibling
  isolation and dirty immutable selection; future protected-UID Git trust and
  full contained caller acceptance remain separate. Disabled AI requires native
  host Polkit; sandbox clients fail with host guidance. See [agent instructions](AGENTS.md#source-selection) for usage,
  dirty-source behavior and existing-worktree constraints.
- **Testing coordination:** Default-off reservations span activation and later runtime
  validation. Private task capabilities, a service-owned mutation/rollback gate and
  current baseline checks enforce exclusivity; see [reservations](reservations.md).
  Recorder-based systemd VM lifetime/exclusion passed; reservation-mediated real OS
  activation/rollback, Polkit/identity and full live workflow acceptance remain pending.

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
