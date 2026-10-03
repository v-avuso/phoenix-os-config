# Agent sandbox acceptance

See [the operating guide](AGENT_SANDBOX.md) for lasting behavior and rationale.

## Current status — 2026-10-03

**First iteration still requires live acceptance.** New committed adapters replace
the custom GUI wrapper with pinned Nix-Bwrapper/Flatpak manifest import and add
retained-authentication desktop routing plus independently reviewed unattended
test/switch. Focused fixtures, combined metal/VM evaluation and a candidate build
pass. These results do not establish interactive GUI or passwordless deployment.
`main` music changes are merged into `codex/agent-sandbox-broker`; the currently
installed runtime below is still the earlier temporary test generation.

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
| Real reviewer/deployment | Retained login; GPT-6.1 Sol / medium approved committed source `55ac611` for `test`; helper built the exact frozen source and completed graphical Polkit activation |
| GUI/backend end-to-end | Saved sandbox login reused; GPT-6 Luna / high model turn succeeded; full-duplex app-server initialization passed; sandboxed window opened; interactive GUI turn blocked by desktop routing/auth mediation gap |
| Persistence/recovery | Pending login/reboot and installed rollback |

Sandbox, reviewer and Native authentication remain separate. Sandbox refresh
material is retained in the private gateway; reviewer authentication is retained
in its dedicated private state. Neither runtime test required another browser
sign-in. Ordinary sandbox launches never start OAuth; repeated sandbox login
commands reuse existing state. Only the public workspace UUID is visible to the
worker for Codex routing; bearer and refresh credentials remain hidden.

Currently installed test system (source commit `55ac611`):
`/nix/store/hw6yd5czl1zg2hqabj4cv529n976vcb6-nixos-system-phoenix-26.05.20260924.c508844`.
The source baseline is the reviewed frozen Git snapshot; later documentation-only
commits do not change this recorded runtime result.

## Remaining live acceptance

1. Install a clean, freshly reviewed candidate with graphical Polkit, then run
   one-time protected reviewer bootstrap using retained authentication. Confirm
   migration and ordinary launches need no repeated OAuth.
2. Verify real worker HTTP credential injection under the narrow Python API
   policy, actual account/routing and interactive sandboxed GUI model/tool use.
3. Verify the Nix-Bwrapper namespace, filtered bus, portal Settings.Read, profile
   persistence, no native CLI fallback and launcher ordering. File selection
   depends on upstream portal identity compatibility; test it separately.
4. Request reviewed test and switch from the sandbox, prove no additional Polkit,
   and verify source/closure binding, boot profile, bounded audit and recovery.
5. Confirm service/session persistence; reboot and destructive rollback tests
   require explicit scheduling, not assumed acceptance.

Application-specific broker identity, complete command auditing and isolated
GUI networking remain possible improvements, not implemented claims. Same-UID
host callers can request the narrow broker/deployment operations, and model
review is fallible. The user accepts that residual risk and authorizes task-related
activation without reminders to save temporary desktop experiment settings.
