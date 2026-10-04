# Agent containment and reviewed deployment

The declarations are in `modules/development/ai/agent`. Installation and runtime
status are recorded separately in [acceptance](AGENT_SANDBOX_ACCEPTANCE.md).
A successful build does not install these services or launcher entries.
The CLI, diagnostic broker and independently reviewed unattended test/switch
have runtime acceptance. The installed GUI completes interactive tasks and
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
| `phoenix-deploy-review --target metal --reason "…" --action test` | Review/build frozen committed source and activate now |
| `phoenix-deploy-review --target metal --reason "…" --action switch` | Review/build and activate now plus next boot |

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

The `phoenix-deploy-review` helper requires a clean, committed checkout
and a concrete task reason. It freezes the exact Git blobs, includes the full
source and changes since `/etc/phoenix-agent/activated-source`, and asks a fresh
isolated reviewer for a structured verdict. Repository instructions/comments are
untrusted evidence. Binary files, symlinks, submodules, oversized source and
malformed, stale, rejected or timed-out verdicts fail closed.

The declaration allows 768 KiB of complete UTF-8 tracked source, a 1 MiB wire
request and a separately bounded 1 MiB review instruction including policy,
source, diff, binding, modes and output schema. Process output remains 2 MiB;
verdicts remain 16 KiB. These are resource bounds, not token estimates. The older
installed gate still uses 512 KiB until a deliberately authorized transition.
Never omit tracked files or substitute a summary to fit the gate.

Protected reviewer metadata reports `gpt-6.1-sol` at 272,000 tokens with 95%
effective context; the larger public API window does not establish this CLI's
budget. No context override is added. Pinned Codex 0.159 non-JSON `exec` emits
`context compacted` for completed compaction; review rejects that marker before
accepting any verdict. `--color never` keeps detection exact. JSON exec drops
these events and must not replace this path. This source-dependent guard must be
rechecked on CLI upgrades; a typed app-server event adapter is the alternative
if upstream changes the marker. Byte admission does not guarantee every source
fits; model overflow or compaction fails closed. The private backend's server
internals remain outside this guarantee.

`test` and `switch` submit bounded source files and a reason through a fixed
root-owned socket; callers cannot submit commands, closures or approvals. The
controller reconstructs the snapshot, builds as an unprivileged dedicated user,
verifies the resulting closure records that exact source, then obtains a fresh
GPT-6.1 Sol / medium review under a separate protected reviewer identity. The
verdict binds source, installed baseline, closure, target, action, reason and a
nonce, stays in memory and is rechecked immediately before activation.

`test` activates now. `switch` deliberately updates the system profile and next
boot too. Neither requests routine Polkit after one-time installation/bootstrap.
Failed activation attempts restore the previous boot profile and runtime
separately; rollback is best effort, not transactional recovery. Saved reports
never authorize deployment. Codex Auto-review remains separate and does not
supply OS root privileges. Host-only legacy `review`/`build` is for initial setup;
bootstrap transfers reviewer refresh ownership to the protected service.

Install from a clean committed Git flake, so the installed baseline contains
exactly the tracked source. Never evaluate this checkout through `path:.`: it
copies ignored artifacts and private local notes into the Nix store. Stage only
owned new files before Git-flake checks; use a vetted disposable source tree
when a path source is necessary. An unreviewable baseline fails closed.

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
protected deployment controller supplies only freshly reviewed test/switch.
Same-UID host programs can request costly reviews/builds; executable hashes
do not authenticate the application or its intent.

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
execution; frozen-source review reduces this risk but remains probabilistic.
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
