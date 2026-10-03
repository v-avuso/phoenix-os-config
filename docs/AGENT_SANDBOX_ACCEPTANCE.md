# Agent sandbox acceptance

Updated 2026-10-04. [Operating guide](AGENT_SANDBOX.md) records lasting behavior;
this checkpoint distinguishes candidate tests from installed acceptance.

## Outcome

**CLI containment, bounded diagnostics and reviewed unattended test/switch work.
The corrected GUI candidate renders tasks and closes/reopens normally. Final
installation and installed-GUI acceptance remain pending protected review.**
Native remains the repair route. Music and engineering guidance from `main` are
merged; no Native profile or previous implementation was discarded.

## Installed baseline

The latest approved persistent switch is commit `7c169d7`:

- Source `/nix/store/3ip2bx7a2jsq5k3gsh62sykrz6cxrc98-source`.
- Next boot `/nix/store/yamlcrh41pagdr1bbjfc1rpr4kc56gg6-nixos-system-phoenix-26.05.20260924.c508844`.

Protected temporary activation of `59ccb3d` succeeded without Polkit:

- Runtime source `/nix/store/5a688xsz8cjjhfnh8r598cmrmbpsbi1n-source`.
- Runtime `/nix/store/wfjdjf0lfdzv9zh04yjmjzsjg47368f7-nixos-system-phoenix-26.05.20260924.c508844`.

It did not update next boot. The corrected desktop candidates are not installed.

## Evidence

| Workflow | Actual result |
| --- | --- |
| Build/evaluation | Corrected GUI builds; metal/VM/default evaluation passes. VM bootability is untested |
| Containment | Real OpenShell worker is rootless; approved repository visible; Native SSH/Pictures/auth omitted; `/etc` write and unexpected network destination denied |
| Broker | Allowlisted service/kernel diagnostics and restored xHCI round-trip pass; arbitrary root and unlisted operations denied |
| Deployment | Real worker requested protected switch without Polkit; controller froze source, built unprivileged, reviewed exact source/base/closure and updated runtime plus boot profile |
| GUI workflow | Maintained desktop 26.930.31730 renders an actual model/tool/final task and clears Stop; normal Codex window/project, saved account, no onboarding/profile warnings |
| GUI lifecycle | Guarded sandbox-only normal quit passes twice: exit 0, all 30 captured processes stop, debug closes, lock released; reopen retains login/project/mode; Native untouched |
| GUI boundary | Private home/workspaces and fixed relays; no Native auth/private profiles or host control sockets. Portal Settings.Read passes; host systemd bus denied |
| Launcher | Actual sandbox favourite set, Native not favourited; final fuzzy-search order needs user confirmation |

Focused broker, launcher, preference, deployment/reviewer, HTTP, socket, GUI and
Node streaming/cancellation fixtures pass. Lifecycle fixtures also verify other
windows/platforms do not quit and changed wiring causes no write. These do not
replace runtime acceptance. Prior sandbox tasks remain readable through supported
RPC; retained task rendering after final installation still needs a GUI check.

## Protected review gates

Candidate `0653216` built but review denied its unexamined Native dependency
upgrade. `93ad9d5` retains Native's exact activated lock and executable while
separately pinning the tested contained GUI. Its review accepted that scope but
requires the new package/launcher/runtime source in the payload. Neither denied
request activated or changed next boot. [Dependency evidence](reviews/agent-desktop-664436c7.md)
is source material for a fresh bound review, never an approval or gate input.

The local desktop task queue is preserved as private state outside tracked NixOS
source. The first narrowed request used a clean temporary committed checkout.

## Remaining acceptance and later work

1. Obtain fresh protected review and persistently install the exact committed source.
2. Run one actual task through the installed GUI; close/reopen retaining that task,
   login and preferences, then remove all debug endpoints/trial processes.
3. Record exact installed source/runtime/boot profile and user-visible result.

Later: actual reboot/rollback, portal file selection, long-build cancellation,
application-specific broker identity, full command auditing, GUI egress isolation,
older-instance session recovery, and independent backup/restore testing.
Same-UID host programs can call fixed broker capabilities; model review is fallible.
Permitted traffic can disclose accessible workspace data. Generation rollback does
not restore workspace/private-state writes; see [recovery](RECOVERY_RUNBOOK.md).
