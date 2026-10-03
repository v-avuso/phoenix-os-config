# Agent containment and reviewed deployment

The declarations are in `modules/development/ai/agent`. Installation and runtime
status are recorded separately in [acceptance](AGENT_SANDBOX_ACCEPTANCE.md).
A successful build does not install these services or launcher entries.

## Everyday use

| Entry | Purpose |
| --- | --- |
| **ChatGPT Community (Sandboxed)** | Private GUI home, filtered desktop portals, OpenShell backend |
| **ChatGPT Community (Native)** | Existing host GUI and profile; deliberate repair/administration |
| `codex` / **Codex (Sandboxed)** | Persistent OpenShell CLI |
| `codex-native` | Direct host CLI |
| `codex-sandbox-login` | Separate sandbox OAuth sign-in |
| `codex-sandbox-exec COMMAND...` | Tool execution inside the managed sandbox |
| `phoenix-review-login` | Separate trusted deployment-review OAuth sign-in |
| `phoenix-deploy-review --target metal --reason "…" --action review` | Review committed source against the installed source |

Launchers start their required services automatically. Caelestia favours the
sandboxed GUI entry; fuzzy matching and usage history still affect search order.
Native remains available for repair. There is no automatic native fallback.

Sandbox and Native GUI profiles are separate. Native credentials, history and
state are not copied or reconciled. Sharing the whole profile would expose that
state and risk redirecting launches to an existing Native process. The GUI
profile and sandbox/reviewer logins require initial user participation.

## Boundaries and initial access

- **CLI files:** only `~/repos/code` and `~/Projects` are mounted writable.
  Pictures, SSH keys, private profiles, host authentication, control sockets and
  unrelated home state are omitted. Effective agent policy/source is immutable.
- **CLI network:** exact OpenAI destinations plus declared public documentation,
  Git, package registry and Nix-cache HTTPS hosts. Public GET/HEAD and GitHub
  fetch are allowed; arbitrary destinations, SSH, push and publishing are not.
- **GUI:** Bubblewrap gives the app a private home and process namespace,
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

The host-only `phoenix-deploy-review` helper requires a clean, committed checkout
and a concrete task reason. It freezes the exact Git blobs, includes the full
source and changes since `/etc/phoenix-agent/activated-source`, and asks a fresh
isolated reviewer for a structured verdict. Repository instructions/comments are
untrusted evidence. Binary files, symlinks, submodules, oversized source and
malformed, stale, rejected or timed-out verdicts fail closed.

`--action build` builds that approved immutable source; `--action test` additionally
requests normal graphical Polkit authentication for that exact closure's
`switch-to-configuration test`. Saved reports never authorize deployment.
Persistent `switch`, passwordless activation and automatic root review/brokering
are not implemented. Command Auto-review does not provide OS authentication.

Install from a clean committed Git flake, so the installed baseline contains
exactly the tracked source. `path:.` is useful for evaluating untracked work,
but may include Git metadata, ignored artifacts and private local files; its
result is unsuitable as this review baseline. A baseline that cannot be reviewed
is rejected rather than silently filtered.

## Auditing, trust and recovery

The diagnostic broker records caller UID/PID, declared operation, duration and
outcome in the journal, without command output or arbitrary caller strings.
Successful wakeup changes include before/after state. Gateway logs and Codex
transcripts cover their respective activity; these are not a complete host
process-command audit.

The broker authenticates the desktop UID using kernel credentials. Other
same-user host programs can call its fixed capabilities too: this is not
application identity. Executable store paths detect version selection, but do
not distinguish malware launching the legitimate executable. The broker grants
no arbitrary shell, file access, service control or NixOS activation.

The trusted host launcher/gateway owns sandbox OAuth refresh. The worker gets
endpoint-scoped opaque handles, not reusable bearer tokens. Native, sandbox and
reviewer authentication are separate. Keep their state private and unreconciled.

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
