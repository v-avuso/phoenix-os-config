# Agent sandbox acceptance

See [the operating guide](AGENT_SANDBOX.md) for lasting behavior and rationale.

## Current status — 2026-10-03

**First iteration implemented; installation and authenticated end-to-end use
still need acceptance.** Changes are organized on `codex/agent-sandbox-broker`.
No successful model turn or passwordless system deployment is claimed.

| Validation | Evidence |
| --- | --- |
| Metal/VM/default evaluation | Combined modules passed `nix flake check --no-build --no-write-lock-file path:.`; VM bootability not claimed |
| Metal build | Combined configuration built without activation; final committed Git-flake build recorded below |
| Diagnostic broker fixtures | 12 passed: fixed operations/argv, bounded time/output, argument/protocol rejection, xHCI checks, symlink rejection and audit privacy |
| Launcher fixtures | 4 passed: quiet stdio, bounded setup, login prerequisite and no native fallback |
| Deployment review fixtures | 6 passed: source freezing, mode changes, activated diffs, dirty/unsupported source rejection, forged/stale/rejected verdicts, process bounds, Git helper suppression and audit safety |
| GUI fixtures | Mount/argument checks and real fixed-command socket relay passed |
| Actual OpenShell runtime | Strict Landlock, rootless UID 1000; workspace access and private-home/symlink exclusions passed in earlier credential-free prototype |
| Network/runtime tools | Public Git fetch, Nix evaluation/cache/small build passed; unexpected destination and disallowed POST rejected in prototype |
| Codex nested sandbox | Actual disposable probe: workspace-write rejected because Bubblewrap cannot create a namespace; explicit outer-only mode succeeds and still cannot write `/etc` |
| Actual GUI namespace | Native auth, SSH/Pictures and host-control sockets absent; declared workspace and fixed relay socket visible |
| Portal bus | Proxy ready; portal introspection succeeded; host systemd access rejected |
| Native CLI protocol | Pinned app-server initialized in a disposable empty home; no authentication or model turn |
| Broker root/runtime mutation | Pending installed service and real sysfs write exception |
| Real reviewer | Pending separate login and model verdict; no API calls made for fixture tests |
| GUI/backend end-to-end | Pending separate sandbox login, GUI launch and real turn; GUI-selected workspace-write may need Full Access inside OpenShell |
| Persistence/recovery | Pending login/reboot and installed rollback |

Credential-free probe sandboxes, gateways, proxy processes and temporary sockets
were removed/stopped. Native authentication and profile were not migrated.
Built caches and private OpenShell registration/TLS state remain for reuse.

## Installation and remaining acceptance

1. Commit all intended source and build the clean Git flake. Never install a
   `path:.` build as the review baseline: it can contain `.git` and ignored local
   artifacts, which the review helper intentionally rejects. Keep an existing
   known-good generation and use the available graphical Polkit flow.
2. Install the reviewed system with temporary `test` first. Confirm socket
   activation, bounded broker reads, rejected malformed requests and journal
   metadata. Round-trip only metal's allowlisted `0000:10:00.4` wakeup setting,
   restoring the original value even after failure. VM has no write allowlist.
3. Complete `codex-sandbox-login`; verify a real model request and refresh,
   installed exclusions and CLI cancellation. Open **ChatGPT Community
   (Sandboxed)** and verify its separate identity, portal operation, contained
   backend and the permission selection required by OpenShell. Verify typing
   `chat` favours it while Native remains usable.
4. Complete `phoenix-review-login`; review a harmless committed change against
   the installed baseline. Check rejection and immutable-source building, then
   authenticated temporary activation. Rootless reviewer isolation needs a real
   model smoke test; source review is probabilistic and not closure analysis.
5. Check session/reboot persistence and installed rollback before persistent
   switch. Automatic root activation, application-specific broker identity,
   complete process-command auditing and isolated GUI networking remain future
   work, not capabilities of this version.

The user authorizes task-related activation without reminders to save temporary
mutable desktop settings. Authentication still requires user participation.
