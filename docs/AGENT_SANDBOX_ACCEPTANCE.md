# Agent sandbox acceptance

See [the operating guide](AGENT_SANDBOX.md) for lasting behavior and rationale.

## Current status — 2026-10-03

**First iteration temporarily installed; retained-authentication CLI and independent
reviewer model requests succeeded.** Changes are on `codex/agent-sandbox-broker`.
The sandboxed desktop opens and its contained backend initializes, but cannot
switch successfully into Codex. The pinned GUI requires workspace routing and
bearer authentication outside the worker proxy; this integration is unfinished. Automatic root deployment is not implemented.
The persistent boot profile still points to the previous known-good generation.

| Validation | Evidence |
| --- | --- |
| Metal/VM/default evaluation | Combined modules passed `nix flake check --no-build --no-write-lock-file path:.`; VM bootability not claimed |
| Metal build | Clean committed Git flake built successfully; baseline matches all 100 tracked files with no Git metadata |
| Diagnostic broker fixtures | 12 passed: fixed operations/argv, bounded time/output, argument/protocol rejection, xHCI checks, symlink rejection and audit privacy |
| Launcher fixtures | 7 passed: saved-login reuse, routing selector, duplex transport, bounded setup, fail-closed lookup and no native fallback |
| Deployment review fixtures | 7 passed: immutable CA mounts, source freezing, mode changes, activated diffs, dirty/unsupported source rejection, forged/stale/rejected verdicts, process bounds, Git helper suppression and audit safety |
| GUI fixtures | Mount/argument checks and real fixed-command socket relay passed |
| Actual OpenShell runtime | Strict Landlock, rootless UID 1000; workspace access and private-home/symlink exclusions passed in earlier credential-free prototype |
| Network/runtime tools | Public Git fetch, Nix evaluation/cache/small build passed; unexpected destination and disallowed POST rejected in prototype |
| Codex nested sandbox | Actual disposable probe: workspace-write rejected because Bubblewrap cannot create a namespace; explicit outer-only mode succeeds and still cannot write `/etc` |
| Actual GUI namespace | Native auth, SSH/Pictures and host-control sockets absent; declared workspace and fixed relay socket visible |
| Portal bus | Host systemd access rejected; real Settings.Read initially exposed missing Instance metadata, corrected using NixPak’s runtime contract; isolated method call now passes |
| Native CLI protocol | Pinned app-server initialized in a disposable empty home; no authentication or model turn |
| Broker root/runtime mutation | Installed service reads passed; unlisted service rejected; metal xHCI wakeup enabled→disabled→enabled round-trip restored original state and produced audit records |
| Real reviewer | Separate retained login; GPT-6.1 Sol / medium returned a valid bound approval for the installed committed source; no build or activation authorized by this review |
| GUI/backend end-to-end | Saved sandbox login reused; GPT-6 Luna / high model turn succeeded; full-duplex app-server initialization passed; sandboxed window opened; interactive GUI turn blocked by desktop routing/auth mediation gap |
| Persistence/recovery | Pending login/reboot and installed rollback |

Sandbox, reviewer and Native authentication remain separate. Sandbox refresh
material is retained in the private gateway; reviewer authentication is retained
in its dedicated private state. Neither runtime test required another browser
sign-in. Ordinary sandbox launches never start OAuth; repeated sandbox login
commands reuse existing state. Only the public workspace UUID is visible to the
worker for Codex routing; bearer and refresh credentials remain hidden.

Currently installed test system (source commit `6d4dc9e`):
`/nix/store/qf9x83iblmkzpip91mqxyd5p5clb822s-nixos-system-phoenix-26.05.20260924.c508844`.

## Remaining acceptance and integration

1. Commit all intended source and build the clean Git flake. Never install a
   `path:.` build as the review baseline: it can contain `.git` and ignored local
   artifacts, which the review helper intentionally rejects. Keep an existing
   known-good generation and use the available graphical Polkit flow.
2. Install the reviewed system with temporary `test` first. Confirm socket
   activation, bounded broker reads, rejected malformed requests and journal
   metadata. Round-trip only metal's allowlisted `0000:10:00.4` wakeup setting,
   restoring the original value even after failure. VM has no write allowlist.
3. Reuse the saved sandbox login; verify refresh and
   installed exclusions and CLI cancellation. Open **ChatGPT Community
   (Sandboxed)** only after implementing the desktop routing/auth mediation.
   Its current synthetic email is a placeholder, not a login failure. The GUI
   requires a non-null `account/read.workspaceRouting` and performs authenticated
   HTTP through Electron, outside the worker’s credential injection. Repeating
   OAuth or adding public identity fields alone does not resolve this. Preserve
   the existing logins; do not copy Native profiles or expose worker tokens.
   Then verify contained model/tool use, permissions and launcher ordering.
4. Reuse the saved reviewer login; review a harmless committed change against
   the installed baseline. Check rejection and immutable-source building, then
   authenticated temporary activation. Source review is probabilistic and not closure analysis.
5. Check session/reboot persistence and installed rollback before persistent
   switch. Automatic root activation, application-specific broker identity,
   complete process-command auditing and isolated GUI networking remain future
   work, not capabilities of this version.

Temporary test activation, model/reviewer smoke processes and the blocked GUI
probe finished. Saved state and the managed gateway remain for reuse.

The user authorizes task-related activation without reminders to save temporary
mutable desktop settings. Authentication still requires user participation.
