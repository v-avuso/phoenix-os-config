# Protected OpenShell identity (experimental)

`phoenix.agent.identity.enable` defaults OFF. When enabled, gateway, rootless
Podman and fixed sandbox launchers run as `phoenix-agent`, default host UID/GID
980 with a separate subordinate range 300000–365535. Nix rejects declared account/group collisions and explicit overlapping ranges;
offline setup verifies the installed account plus actual root-owned subuid/subgid
allocations, including ranges allocated automatically by NixOS. Upstream
`keep-id:uid=1000,gid=1000` maps the workload to this dedicated owner.

Immutable configuration fixes the executable, environment and workspace roots.
Private HOME/state/registration live under `/var/lib/phoenix-agent`.
`/run/phoenix-agent` is root-owned; Podman has a private agent-owned child.
The system socket authenticates the operator through kernel `SO_PEERCRED` and
passes exactly three `SCM_RIGHTS` stdio descriptors to the fixed service. Exit
status uses a separate control connection; stdin/stdout/stderr remain full duplex.
Disconnect cancels the child process group. Resize/interrupt/termination/hangup
signals are forwarded and the client restores terminal settings.

The existing OpenShell SSH/mTLS app-server and exec TTY remain in use.
[systemd socket-proxyd](https://github.com/systemd/systemd/blob/v260/man/systemd-socket-proxyd.xml)
cannot forward credentials/descriptor rights; the thin custom remainder is
admission, descriptor handoff and lifetime/status handling.

## Compatibility

- Native Codex retains its operator account, auth profile and manual Polkit path.
  Diagnostic/deployment sockets admit only the agent UID when identity is enabled.
  Disabled AI still requires native human authentication; no sandbox Polkit or
  native model-auth proxy is added.
- This first mode requires the **already enabled, validated history handoff**.
  Setup/launch refuse inactive or incomplete history before migration. Native
  session directories and credential-free SQLite history stay in their original
  locations. No whole `.codex`/auth/desktop profile or Podman store is copied.
  Protected readiness avoids native `config.toml`; Native managed launchers
  retain the SQLite override check.
- CLI accepts no arguments, one literal prompt, or `resume UUID`. Fixed app-server,
  desktop HTTP and public account-selector modes are admitted. No caller
  executable/environment/provider/policy/mount/config overrides are accepted.
  `codex-sandbox-exec` and sandbox login refuse in protected mode; provider repair
  remains deliberate Native administration. Protected app-server uses sandbox
  defaults instead of importing native CLI scalar preferences. Existing selected
  desktop display preferences still use the host adapter.
- Dedicated services use `ProtectHome=tmpfs` plus only declared workspace/narrow
  history binds. Rootless user namespaces and mapping helpers remain available.
  Podman compatibility of this service namespace composition needs VM acceptance.
- Operator launcher access and residual operator malware control remain explicit.
  Existing TTY descriptor handoff retains the native terminal trust assumption;
  this is not terminal-injection isolation. The examined host has
  `dev.tty.legacy_tiocsti=0`; verify the acceptance host's actual kernel behavior.
- Scoped ACLs grant selected roots and necessary ancestor traversal. Default ACLs
  retain operator access to normally created new files; explicitly private file
  modes can reduce the ACL mask. No Podman `:U` or recursive home/profile chown.

## Offline setup and cutover

**Setup is prepared but UNEXECUTED. Identity stays OFF until isolated acceptance.**

1. Evaluate/build a disposable enabled VM. Check UID/GID/subordinate allocation,
   existing nonsymlink normalized workspace roots, and valid active managed
   history beforehand.
2. Arrange a separate offline administrator window. Old gateway, launchers,
   workloads and operator session must be quiescent. The installed fixed
   `phoenix-agent-identity-setup` refuses any operator-owned process. It cannot
   normally run through live operator Polkit: the caller's parent still belongs
   to the operator. It never logs users out or stops/restarts services. Its
   refusal check does not prevent concurrent login; the administrator must
   control the offline maintenance boundary.
3. From isolated root, run that fixed command. It verifies installed identity/ranges, account selector,
   history, workspace roots/locks and the pinned DB/KEK tree before relocating only
   `~/.local/state/phoenix-openshell/openshell/gateway` into
   `/var/lib/phoenix-agent/openshell/gateway`. Held directory FDs/nofollow opens
   prevent path substitution; links/special files are rejected. Only this subtree
   changes ownership, preserving its DB/credential encryption key. The public
   UUID selector is copied separately and known history/workspaces get ACLs.
   The readiness marker is published only on success.
4. Atomic relocation is preferred. On `EXDEV` (including separate Btrfs
   subvolumes), fixed GNU coreutils `cp --archive --no-dereference --reflink=auto`
   copies **only** validated DB/WAL/SHM and credential encryption key into a
   generated root-protected staging directory on the destination filesystem.
   Source and copy must match exact file names, sizes and streaming hashes
   (512 MiB total bound, 1 MiB buffers). The verified tree is atomically published;
   original source stays intact for rollback. Copy failure cleans up only owned
   staging and publishes no readiness marker. No whole profile/container copy or
   deletion of the retained original is performed.
5. In the controlled VM window, start the protected path. Upstream generates
   **fresh private control TLS** and fresh CLI mTLS registration; old operator
   TLS/registration is never copied. Retained provider DB/KEK preserves refresh
   material without signup, new model login or provider recreation. Sandbox
   names include identity revision, leaving old operator container records intact.

State layout is tied to
[OpenShell 0.1.2 defaults](https://github.com/NVIDIA/OpenShell/blob/v0.1.2/crates/openshell-server/src/defaults.rs);
recheck its exact implementation before changing versions. Relocation/chown
cannot revoke historical credential copies or already-open FDs. Offline
quiescence limits concurrent writes; retained auth does not guarantee
retroactive credential exclusion.

## Refusal and recovery

Failures report bounded stage/category without raw auth/exception contents.
Inspect that exact stage offline before retrying; partial destinations and an
existing readiness marker refuse automatic retry. Never delete provider state
to force a retry. Before publication, a failed copy retains original source and
can leave an empty destination `openshell` parent; verify it empty before removing
only that parent. After publication but later ACL failure, preserve the published
tree and inspect offline; no readiness marker/service start is automatic.

`identity-migration.json` records whether the command relocated or copied and
retained the source. Rollback requires both paths/services quiescent: verify that
record and the current protected tree before restoring identity OFF.
For relocation, reverse the same narrow move and restore only that subtree to
recorded operator UID/GID. For copy, original source is retained, but becomes a
stale credential snapshot after protected-provider refresh. Do not blindly
replace current auth with it: later rollback must separately review preserving
the current protected DB/KEK in the original location using the same narrow
verified-copy principle. Remove the protected readiness marker only in that
controlled rollback. Preserve history and reverse only recorded added ACL entries
if withdrawing sharing; no recursive home cleanup/blanket ACL removal exists.

## Acceptance

```sh
python3 -B modules/development/ai/agent/tests/identity-transport.py
python3 -B modules/development/ai/agent/tests/identity-setup.py
```

Transport fixtures cover real same-user peer credentials, descriptor cleanup,
duplex/EOF, stderr/status, cancellation, PTY resize/restoration, isolated-file
packaging, partial sends and safe diagnostics. Setup uses synthetic state with
privilege/installed-account/quiescence and full-workflow ACL calls mocked;
EXDEV is emulated while GNU cp and verification actually run. A separate actual
recursive ACL fixture touches only temporary directories. These fast fixtures do not prove real
distinct-account containment or retained provider/model operation.

Before enabling, a provisioned VM must prove operator launcher → fixed dedicated
service → OpenShell → diagnostic broker; reject direct operator broker access.
Verify unrelated home masking for every service, private gateway/Podman/control
credentials inaccessible to operator/workload, operator access to new workspace
edits, and history listing/resume/archive. Exercise retained model response,
desktop HTTP/app-server, interactive CLI, resize/interrupt/EOF/close cleanup and
restart. Verify Native CLI/auth/Polkit separately and no AI-disabled sandbox
activation bypass. Keep OFF until the entire workflow passes.

## Isolated distinct-UID transport and broker slice

The on-demand [identity peer VM](tests/identity-peer.nix) passed; evidence is
`/nix/store/69sjnz0v464x0dqy6647908f3y740ask-vm-test-run-phoenix-identity-peer/evidence`.
It imports the actual identity/broker modules and verifies operator UID1000 through
the fixed launcher/SCM_RIGHTS service to agent UID980 and one real bounded kernel
journal diagnostic. Direct operator/outsider broker sockets are reachable but
execution is denied with matching audit records. Actual `ProtectHome`/narrow binds,
workspace ACL/default inheritance, separate stdio/status, malformed-rights rejection,
outside-workspace refusal and cancellation/child reaping pass. Noninteractive probes
use explicit pipes/DEVNULL; real interactive PTY acceptance remains separate.

Gateway/Podman readiness and the post-transport OpenShell backend are fixed doubles.
Only the real ACL helper runs, not full migration/setup. No retained credentials,
model, actual OpenShell worker, GUI/history or host enablement are exercised. This
proves a dedicated-UID slice for OpenShell only. Exact Codex-only admission spanning
Native and contained CLI is not implemented; Native retains the operator identity
and human recovery contract. The identity option stays OFF pending the full workflow.


## Protected Podman keep-id gate

The [protected Podman VM gate](tests/identity-openshell.nix) passed with fresh
UID980 storage and the unmodified identity service User/environment, `ProtectHome`,
narrow binds and `Delegate` settings. Evidence is
`/nix/store/salj3rjbxrqik603jpwrr341i7wbvwxa-vm-test-run-phoenix-identity-openshell-podman-gate/evidence`.
The SHA/config-ID-verified cached small public workload loaded through the real
remote API, created/started with keep-id, and executed as container UID1000 with
host UID980 workspace ownership. Operator access through inherited ACLs passed;
forced removal succeeded and the named-container query was empty. No host state,
credentials, gateway, model or migration participated.

The fixture also has explicit `mode = "gateway"` with verified cached runtime and
supervisor records. The first run exposed strict OpenShell 0.1.2 preflight rejection
of the NixOS `/etc` configuration symlink. Protected and native gateways now receive
the same direct generated immutable configuration path; the strict preflight is
unchanged. The owning config is passed as `phoenixAgentGatewayConfig` to avoid a
runtime copy or divergent configuration.

Protected Podman now requires the standard UID980 user manager and uses canonical
`/run/user/980`, retaining its private API socket and persistent HOME/config/data
paths. The per-UID manager drop-in inherits the same `ProtectHome=tmpfs` and narrow
binds (including only its own real runtime directory); its healthcheck children
therefore keep the protected storage environment and home boundary. No linger or
operator-manager change is introduced. Additive `ConditionUser=!phoenix-agent`
drop-ins exclude global GCR, PipeWire/Pulse, speech-dispatcher and generic Podman
services/sockets while preserving upstream/operator conditions and D-Bus/tmpfiles.

The bounded VM passed actual manager environment/storage and unrelated-home masking,
representative desktop-unit exclusion/operator condition, dependency ordering, real
gateway readiness and synthetic TLS registration. The fixed PATH explicitly includes
systemd because Podman invokes `systemd-run --user` by name. Operator → fixed launcher
→ actual transport UID980 → real sandbox UID1000 → host-UID980 workspace write and
real broker audit UID980 passed through a fixed test exec bridge. Direct operator
and outsider socket access was denied with matching kernel-UID audit records.

Primary gateway mode defaults `healthCheckInterval = null`, matching production's
absent regular-health setting. The actual launcher/sandbox/workspace/broker chain
passes. Cleanup uses authenticated `openshell sandbox delete identity-gateway`,
keeping the gateway/attached stream alive, then independently checks captured
container UUIDs, owned timers and gateway-record disappearance. Deletion/disappearance
have one 180-second diagnostic budget, followed by separately bounded client
reap/gateway stop and script/global caps of 300/360 seconds. This is diagnostic
headroom, not acceptable ordinary-shutdown latency; the 45-second safety net is unchanged.

The current gate remains red at `cleanup-disappearance/gateway-disappearance-timeout`.
One diagnostic rerun from frozen source `9frgill8…` used primary gateway mode with
`healthCheckInterval = null`. Delete returned 0 in 0.647s; after the unchanged
180s cleanup budget, `remainingContainerCount = 0` and
`capturedGatewayIdCount = 1`. The surviving predicate is the captured gateway
record, not a captured container. The later owned-timer assertion was not reached.
The chain and broker positive/negative checks ran before cleanup; no complete
primary cleanup pass is claimed. Exact failed derivation:
`/nix/store/2wkm7v829r6s5y9fcl45d1pbh8mjw0rc-vm-test-run-phoenix-identity-openshell-gateway-gate.drv`.

Pinned CLI `run.rs::sandbox_list` prints IDs returned by ListSandboxes, so an ID
remaining in that result is not proof of a live container. Delete acknowledgement
and durable gateway-record disappearance are distinct. Pinned `run.rs` accepts
both Completed and Accepted (cleanup pending) as successful deletion;
`compute/mod.rs` leaves final store removal to the Podman removal-event watcher
when the record still exists. This explains why exit 0 alone is insufficient; it
does not establish why this captured record survived the deadline. The record's terminal/
Deleting phase and reason for retention were not captured; no upstream cause is
established. Next inspect the captured record's bounded phase plus deletion/
watcher error categories in a separately authorized isolated diagnostic. Keep the
captured-ID absence assertion and 45s safety net unchanged. The tested fixture
Nix/Python and `identity.nix` are byte-identical after advancing to merged main
`8fbee57`; this does not claim whole combined-source VM acceptance.

The optional `healthCheckInterval = 10` reproducer configures supported supervisor
regular healthchecks in this fixture only; it retains its strict timer/manual
assertions. A timer-driven `Health.Log` recorded success/healthy before manual
invocation, but the following remote manual check returned 1/unhealthy. That
optional diagnostic remains red; neither timer nor manual regular-health acceptance
is counted toward primary default acceptance. Its log is
`/nix/store/rcxzvvv5l5kd7y79jxmqjyv6irypvh89-vm-test-run-phoenix-identity-openshell-gateway-gate.drv`.
Production configuration and the default Podman-only fixture are unchanged by this
optional input.

No healthcheck, filesystem or cgroup restriction was relaxed. The fixture requests
gateway-owned deletion, then requires disappearance before stopping the gateway;
this red result does not establish full cleanup acceptance, shutdown grace or log
durability. Only workspace/broker paths and read-only Nix dependencies are requested
workload mounts; no private control credentials are mounted. The bridge replaces
Codex/history launcher semantics; the small public image is not the full Codex image.
Dependency declarations/order are queried; controlled manager-stop behavior was not
exercised. Full launcher/history, retained authentication,
GUI/PTY, migration and exact Native Codex admission remain separate and unproved.
