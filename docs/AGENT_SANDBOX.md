# Agent containment and reviewed deployment

The declarations are in `modules/development/ai/agent`. Installation and runtime
status are recorded separately in [acceptance](AGENT_SANDBOX_ACCEPTANCE.md).
A successful build does not install these services or launcher entries.
The CLI and diagnostic broker have runtime acceptance. Earlier model-reviewed
deployment acceptance is historical; mandatory AI review is now suspended. The installed GUI completes interactive tasks and
retains them across normal close/reopen. Exact source and runtime evidence are
recorded in acceptance; component tests alone are insufficient.

## Everyday use

| Entry | Purpose |
| --- | --- |
| **ChatGPT Community (Sandboxed)** | Private GUI connected to the OpenShell app-server and mediated backend |
| **ChatGPT Community (Native)** | Existing host GUI and profile; deliberate repair/administration |
| `codex` / **Codex CLI (Sandboxed)** | Persistent OpenShell CLI |
| `codex-native` / **Codex CLI (Native)** | Direct host CLI |
| `codex-sandbox-login` | One-time sandbox sign-in; existing login is reused |
| `codex-sandbox-exec COMMAND...` | Tool execution inside the managed sandbox |
| `phoenix-review-login` | One-time reviewer sign-in; existing login reports saved status |
| `phoenix-deploy-bootstrap` | One-time graphical installation of protected reviewer authentication |
| `phoenix-deploy-review --target metal --reason "…" --action test` | Authenticate/build a frozen working-tree snapshot and activate now |
| `phoenix-deploy-review --target metal --reason "…" --action switch` | Authenticate/build a working-tree snapshot and activate now plus next boot |

Launchers start their required services automatically. The current declaration favours the
sandboxed GUI entry; fuzzy matching and usage history still affect search order.
Native remains available for repair. There is no automatic native fallback.

Native keeps the known-good `codex-desktop-linux` lock revision. The contained
GUI uses the separately pinned `codex-desktop-sandbox` package from the same
upstream, sharing its existing dependencies. Its newer desktop protocol does not
update Native or import another NixOS module. Review Native upgrades separately;
the Flatpak/Bubblewrap framework remains shared.

The sandbox GUI requests a normal quit when its last primary window closes.
Its current Chromium runtime
reports tray readiness even when the filtered bus prevents registration; hiding
would leave the profile locked behind an unreachable window. A checked patch in
the sandbox copy disables tray hiding/keepalive on Linux and requests normal quit
after upstream tracked-primary cleanup, even with a hidden service window.
It preserves close/quit confirmations, saved bounds and normal shutdown cleanup.
Remove it once maintained upstream close/reopen works under the same policy.
Reopening retains the private profile and existing login. Normal shutdown can
take several seconds while upstream flushes state; a duplicate launch never starts another
writer to that profile.

Sandbox and Native browser profiles are separate. Chromium uses profile locks
and process-singleton routing; sharing that directory can redirect a sandbox
launch to the existing Native window. This is distinct from Codex task storage,
which upstream supports sharing with SQLite WAL and per-thread writer locks.
Native task history stays separate until the explicit cold handoff below; this
is a migration constraint, not an anonymity requirement. The GUI
profile and sandbox/reviewer logins require initial user participation. Saved
credentials survive launches; diagnostic failures do not trigger another login.
The gateway remains the sole owner of sandbox OAuth refresh. A fixed HTTP
adapter runs inside OpenShell and receives opaque handles; credential injection
happens on egress. The sandbox-only immutable desktop bootstrap forwards its
authenticated backend fetches to that adapter. Real account metadata supplies
workspace routing and a public identity selector; no reusable bearer reaches the
GUI. Public asset requests retain the upstream transport.

At first configured launch, a host-only adapter imports selected existing
onboarding/display preferences and project roots inside the declared workspaces.
It preserves other sandbox state and clears maximization on valid imported window
bounds. This import runs once; later Native global-state changes are not
synchronized. It never copies
the whole global-state map, draft/resume tokens, history or authentication.
Separately, each GUI app-server launch reads only typed model/effort/tier and
four supported desktop preferences from Native `config.toml`; these become fixed
scalar Codex overrides. Permission modes, endpoints, commands, MCP servers and
plugins are excluded. The worker never receives or mounts that Native file.
The CLI TUI retains its own configuration; this is selective GUI settings reuse,
not shared browser profiles. Task history sharing is enabled separately below. Sandbox tasks persist in the
managed OpenShell instance across GUI close/reopen; the GUI retains its own private
display state. Changing the sandbox declaration can select a new instance rather
than import earlier tasks. Native scalar model/display settings are reread each
time the GUI starts an app-server, not continuously synchronized while it runs.

The conditional history-sharing integration uses upstream `sqlite_home`/`CODEX_SQLITE_HOME`
in a dedicated credential-free directory, plus shared sessions, archived sessions
and writer locks at identical absolute paths. This avoids a custom synchronization
or import framework. It grants access to all stored task history, including future
tasks outside the coding workspaces; project filters are not security boundaries.
Sharing remains inactive until a coordinated exit of Native and sandbox writers.
`codex-history-enable` performs a cold preflight; explicit `--apply` uses SQLite
backup to prepare credential-free databases and atomically publishes readiness.
Original Native databases and old sandbox containers remain intact; old sandbox
tasks are not merged. Browser profiles and OAuth refresh owners stay separate.
See the [handoff and rationale](../modules/development/ai/agent/history-layout.md)
for locking, interrupted preparation recovery, unsupported overrides and required
listing/resume/archive/writer-exclusion checks. Do not run the handoff from a
Native conversation that must remain alive.

## Boundaries and initial access

- **CLI files:** only `~/repos/code` and `~/Projects` are mounted writable.
  Pictures, SSH keys, private profiles, host authentication, control sockets and
  unrelated home state are omitted. Effective agent policy/source is immutable.
- **CLI network:** exact OpenAI destinations plus declared public documentation,
  Git, package registry and Nix-cache HTTPS hosts. Public GET/HEAD and GitHub
  fetch are allowed; arbitrary destinations, SSH, push and publishing are not.
- **GUI:** pinned Nix-Bwrapper imports the community ChatGPT Flatpak manifest
  and supplies Bubblewrap, filtered buses and portal integration. It gives the app a private home and process namespace,
  declared workspaces, Wayland/GPU access and a filtered portal bus. A fixed
  socket relay starts only the OpenShell app-server; the GUI gets no Podman,
  diagnostic broker or host service-control socket. GUI network is shared with
  the host; OpenShell's destination limits apply to its backend, not GUI traffic.
- **Diagnostics:** `phoenix-admin` exposes bounded kernel journal/dmesg,
  selected tracing metadata and selected service status. Kernel logs may contain
  task data or identifiers; this read capability is intentional.
- **Mutation:** only allowlisted xHCI wakeup settings can change. Metal allows
  `0000:10:00.4`; VM allows none. Cooling and recovery protections remain.
- **Development:** Nix uses an isolated store/database without the host daemon.
  Preinstalled tools are root-owned; added build outputs are writable.

GUI app-server relay frames are capped at 16 MiB including the newline, before
forwarding in either direction. Oversized frames close the connection and fixed
child with a generic diagnostic; login state is preserved. This protects against
unbounded individual frames, not every possible resource-exhaustion pattern.
The extra bridge buffers newline-delimited JSON; an unterminated stream could
otherwise grow without bound. Ordinary text does not become dangerous because
of sandboxing. The cap fixes our adapter's buffering risk, and legitimate larger
frames need a reviewed transport remedy rather than another sign-in.

The Python interpreter can use authenticated desktop API namespaces too; this
is endpoint-limited authority, not proof that a particular script is calling.
Exact workspace/destination/capability lists are in the module. Policy changes
require a reviewed declaration and host deployment, rather than a worker edit.

OpenShell 0.1.2 enforces strict Landlock, seccomp and mediated network access.
It blocks the user namespaces required by Codex's inner Bubblewrap sandbox.
Pinned Codex 0.159 therefore explicitly uses `danger-full-access` **inside
OpenShell only**; this is not unrestricted host execution. There is no retry
that silently changes containment. Codex `workspace-write` fails in this outer
sandbox; GUI permission selection must be checked during acceptance.

The upstream Codex Auto-review policy is retained with `on-request` approvals.
It reviews eligible requests, not commands already allowed by OpenShell. Scoped
worker instructions explain broker use and escalation; they are not reviewer
policy or kernel enforcement. The built-in reviewer has no verified configurable
model selector; the separate deployment reviewer uses GPT-6.1 Sol / medium.

## Reviewing and deploying configuration

Authenticated deployment is independent from optional **deployment security review**.
`services.phoenixDeployment.securityReview.enable` is the single review switch,
false by default. The former `modelReview.enable` name is a deprecated alias of
that same option. Turning review off removes its policy, override command and
reviewer login commands; it retains authenticated deployment and protected state.
Do not enable live review until the real model, denial/override and activation
workflow passes isolated acceptance. Current fixtures are not that acceptance.

`phoenix-test` and `phoenix-switch` freeze tracked working-tree edits plus
Git-visible untracked files; ignored files are excluded. A clean commit is **not**
required. HEAD records provenance, while the immutable source and resulting
closure identify the actual contents. The unprivileged builder, source/closure
binding, current baseline/profile rechecks and rollback apply with review on or
off. Review off requires graphical Polkit authentication; it never grants the
ordinary agent socket unattended manual deployment.

When enabled, security review receives the diff and changed-file index, not the
whole repository. It checks dangerous authority, executable hooks, destructive
behavior and private-data exposure rather than code style. Distributor/package
updates do not generate automatic dependency-review batches. The controller can
invoke Codex at most twice: the first response may request up to eight frozen
baseline/candidate line ranges, totaling at most 128 KiB; the second must conclude.
There is no arbitrary shell/network context tool. These are controller invocation
bounds, not a guarantee about Codex's internal API call count or exact AI cost.

Root-owned checkpoints retain the exact approved source, built closure, target
and policy identity. Branch names only select a nearby approved comparison state;
they confer no authority. Review success is independent of successful activation.
An identical approved source/closure reuses approval; a merged candidate with a
new identity still needs review. No review branches, user Git mutations or automatic
approval propagation across merges are needed. The activated baseline is trusted
as the initial comparison state. Retention is bounded to 32 approved/pending records.

Denied or incomplete review returns a secret-safe category and protected pending
request. `phoenix-deploy-review --security-override <pending-nonce>` requires
fresh Polkit authentication with a critical warning. It accepts no caller command
or replacement source; the controller checks the exact source/closure, requester,
action, target, policy and current deployment baseline. Read the rejection before
approving. PAM determines available authentication methods, including configured
fingerprint support. This does not automatically prove a rejection was false.

Source transport has a 4 MiB file-content guard and 32 MiB wire guard; that is build
input, not AI input. Serialized AI instructions/context have a 1 MiB resource
limit, bounded output and deadlines. A roughly 24,000-token diff estimate produces
a warning rather than rejection; it is not an exact token count or bill. Safe
failure categories distinguish model denial, startup/authentication, timeout,
context and malformed output. Never expose native auth stderr or credentials.

Routine automatic updates use the separate deterministic `update` action and
stage next boot without AI or Polkit. See [automatic updates](UPDATES.md).
Existing reviewer credentials remain protected; do not reconcile or disclose them.
Changed controllers finish the current request before graceful reload; legacy
controllers need one authenticated restart during migration.

Never evaluate this checkout through `path:.`: it copies ignored artifacts and
private notes into the Nix store. Stage only owned new files for Git-flake checks.
Frozen deployment snapshots already carry new development files without requiring
premature commits. An unreviewable baseline fails closed.

### Rootless startup compatibility

The pinned OpenShell 0.1.2 driver creates its supervisor in host networking and
accepts `drivers.podman.host_gateway_ip`. Its empty default sends Podman's magic
`host-gateway` entry, which failed on the installed rootless Podman with an empty
internal IP. Configuration sets `127.0.0.1` explicitly through that native driver
option. Isolated workload networking remains unchanged. This fixes the identified
startup configuration cause. Installed gateway preflight accepts the generated
TOML, and a disposable Podman start generated both aliases as loopback. Automatic
mapping also succeeded during that later trial, so the historical empty-IP failure
was not reproduced. Rebuilding/restarting the managed gateway and checking
Ready plus retained-account model access remain runtime acceptance.

### Shutdown ordering trial

`phoenix.agent.shutdownOrdering.enable` is an independent experimental containment
option, off by default. It adds an override only to the dedicated OpenShell Podman
API: container scopes stop after the gateway, and conmon stays with that API while
workload cgroups/resource limits remain. This prevents systemd from independently
tearing down those scopes while gateway cleanup is running. The existing 45-second
stop deadline remains a final safety net.

A disposable Podman 5.8.7/crun 1.27.1 trial verified annotation propagation,
resource limits, TERM handling and a final log line with a 1.96-second concurrent
stop. It did not run the actual OpenShell supervisor/log RPC or a full shutdown;
those remain acceptance requirements. See the [disposable regression procedure](../modules/development/ai/agent/shutdown-acceptance.md). Exact pinned OpenShell 0.1.2 has unbounded
cleanup awaits; which await stalled on October 6 is still unproven. Upgrading to
0.1.3 does not establish a fix. Do not enable this option just from fixture results.

## Auditing, trust and recovery

The diagnostic broker records caller UID/PID, declared operation, duration and
outcome in the journal, without command output or arbitrary caller strings.
Successful wakeup changes include before/after state. Gateway logs and Codex
transcripts cover their respective activity; these are not a complete host
process-command audit.

The deployment controller journals bounded stages, caller UID/PID, source,
closure, target, action and reason digest. It omits task content and credentials.
Private legacy review reports are never read as approval inputs.

The broker authenticates the desktop UID using kernel credentials. Other
same-user host programs can call its fixed capabilities too: this is not
application identity. Executable store paths detect version selection, but do
not distinguish malware launching the legitimate executable. The diagnostic broker grants
no arbitrary shell, file access, service control or NixOS activation. A separate
protected deployment controller accepts deterministic boot-only updates; manual
test/switch/boot requires graphical operator authentication while AI review is
suspended. Executable hashes do not authenticate an application or its intent.

The trusted host launcher/gateway owns sandbox OAuth refresh. The worker gets
endpoint-scoped opaque handles, not reusable bearer tokens. Native, sandbox and
reviewer authentication are separate. Keep their state private and unreconciled.
Ordinary launches never initiate OAuth; a repeated sandbox login command reuses
its saved provider. Missing routing metadata needs repair, not another sign-in.
The public workspace UUID is passed separately because Codex compares it locally.
The desktop uses OpenShell’s mTLS SSH proxy for duplex app-server traffic, without
host SSH keys/configuration or remote login profiles; ordinary commands use gRPC.

The pinned desktop decodes public `chatgpt_account_id` and `chatgpt_user_id`
claims before it performs account lookup. The GUI relay supplies those required
fields, actual email/plan and routing from authenticated account/profile APIs.
An incomplete selector can therefore look like unavailable Work access even when
CLI authentication succeeds. Repair that adapter rather than starting OAuth.

Chromium's singleton socket cannot reliably coordinate separate private `/tmp`
and PID namespaces. The host launcher serializes access to the writable private
GUI profile for the wrapper's lifetime. A repeated launch starts no second
writer; use the existing window. A guarded tray-activation adapter can use only
the exact same-user immutable filtered bus proxy for this sandbox, but the
current runtime does not register a reachable tray. It never falls back to
Native. Close processes, not just visible test windows, before another isolated
trial; never reset the profile to hide lock errors.

Live writable repositories require OpenShell's unsafe host-bind opt-in and
relaxed driver resource admission. Host kernel/runtime and gateway remain
trusted. Workers can damage their workspaces or plant changes for later host
execution. With AI review suspended, operator authentication approves deployment;
it does not establish that workspace content is safe.
Allowed traffic can still disclose accessible workspace data. OpenShell is alpha.

Declaration changes create a new sandbox and retain previous state for deliberate
recovery. Native and known-good NixOS generations remain repair routes. Nix's
nested build/syscall sandbox is disabled inside OpenShell; large-build cancellation
still needs testing. Do not weaken outer enforcement to hide cleanup warnings.

## References

- [Pinned OpenShell Codex integration](https://github.com/NVIDIA/OpenShell/tree/v0.1.2/examples/codex-app-server)
  and [outer-sandbox example](https://github.com/NVIDIA/OpenShell/blob/v0.1.2/examples/agent-driven-policy-management/sandbox-agent.sh).
- [Codex Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review).
- [Bubblewrap](https://github.com/containers/bubblewrap) and
  [Flatpak sandbox permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html).

- [Pinned Nix-Bwrapper framework](https://github.com/Naxdy/nix-bwrapper/tree/d170b06fafc0703fff36ec422a64516594b39bd9)
  and [pinned community ChatGPT Flatpak baseline](https://github.com/kk-daniel/chatgpt-desktop-flatpak/blob/521efae965529d2bda3e7d59eaa83173dc89357d/com.openai.ChatGPT/com.openai.ChatGPT.yaml).
  The manifest is a permission reference, not proof that this Electron port is tested.
  Updates import applicable permissions automatically at build time; review pin
  updates and local restrictions. Upstream portal instance metadata remains a
  compatibility workaround and needs real acceptance, especially for file selection.
