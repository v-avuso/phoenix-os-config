# Agent sandbox acceptance

Updated 2026-10-04. [Operating guide](AGENT_SANDBOX.md) records lasting behavior;
this checkpoint records installed acceptance and remaining hardening.

## Outcome

**The first iteration is installed and usable: GUI tasks render and survive
normal close/reopen; OpenShell containment, bounded diagnostics and independent
reviewed unattended test/switch have runtime acceptance.**
Native remains the repair route. Music and engineering guidance from `main` are
merged; no Native profile or previous implementation was discarded.

## Current follow-up

Protected persistent switch of `cdb3b64` installed conditional shared-history
support and the current-event Kando detector correction without Polkit. Runtime
and next boot both match
`/nix/store/p0r9drdxzgbgs3w5r6n081vv5vf1vqqs-nixos-system-phoenix-26.05.20260924.c508844`;
source is `/nix/store/11a9f348ykp0qsmn8y8rjzdwfqaw6wkj-source`. Controller audit
records build → independent review → approval → activation. Live Kando hover/no-
confirmation/100px settings match, and its service restarted on switch. The user
confirmed no pointer jumping but the previous 200px build failed held selection;
physical acceptance of this corrected build is pending. Psysonic audible playback
is user-confirmed. The stale Caelestia shell was refreshed gracefully; live IPC
exposes idle activate/restore, while actual blank/wake remains pending.

Shared-history support is installed but inactive. Its actual cold preflight
correctly refuses the current same-user Codex writers; no data was migrated and
the current Native conversation remains alive. Enable only through the
coordinated cold handoff in [the operating guide](AGENT_SANDBOX.md), then verify
listing/resume/archive and same-task writer exclusion. Legacy sandbox containers
and Native source databases are retained rather than silently merged.

## Initial accepted source

Protected persistent switch of commit
`ed913e5497192dff0a3d8165798380856d409177` succeeded without Polkit:

- Source `/nix/store/azrjjgc03z1r4c0qxj069ipkqs4vs8h6-source`.
- Runtime and next boot both
  `/nix/store/l3hvc6gs09g1jckh6v9m9998m8zbzvbc-nixos-system-phoenix-26.05.20260924.c508844`.
- Installed GUI `/nix/store/d1mcr9l0phwl4mind1lk0ar7289h806i-codex-desktop-sandboxed/bin/codex-desktop-sandboxed`.
- Native remains exactly
  `/nix/store/7arsi88iwfa5baljss24dq2x9shc7d1q-codex-desktop-26.917.71314-codex-cli-path/bin/codex-desktop`.

The controller journal recorded build → review → approval → activation. The
public runtime, system profile and activated-source marker match its response.
Earlier approved switch `7c169d7` and temporary test `59ccb3d` are retained in
Git history; neither candidate denial activated a system.

## Evidence

| Workflow | Actual result |
| --- | --- |
| Build/evaluation | Corrected GUI builds; metal/VM/default evaluation passes. VM bootability is untested |
| Containment | Real OpenShell worker is rootless; approved repository visible; Native SSH/Pictures/auth omitted; `/etc` write and unexpected network destination denied |
| Broker | Allowlisted service/kernel diagnostics and restored xHCI round-trip pass; arbitrary root and unlisted operations denied |
| Deployment | Real worker requested protected switch without Polkit; controller froze source, built unprivileged, reviewed exact source/base/closure and updated runtime plus boot profile |
| GUI workflow | Installed desktop 26.930.31730 renders an actual model/tool/final task and clears Stop; normal tiled Codex/project window, retained account, no onboarding/profile warnings |
| GUI lifecycle | Candidate and installed normal quit pass: exit 0, all captured processes stop, debug closes, lock released; reopen retains login/project/mode and renders the same completed task; Native untouched |
| GUI boundary | Private home/workspaces and fixed relays; no Native auth/private profiles or host control sockets. Portal Settings.Read passes; host systemd bus denied |
| Launcher | Actual sandbox favourite set, Native not favourited; final fuzzy-search order needs user confirmation |

Focused broker, launcher, preference, deployment/reviewer, HTTP, socket, GUI and
Node streaming/cancellation fixtures pass. Lifecycle fixtures also verify other
windows/platforms do not quit and changed wiring causes no write. These do not
replace runtime acceptance. Installed task `01a10419-2ec0-7c41-bf98-c7c1933f8c02` completed one
authorized printf with exit 0 and exact output/final markers. After reopening, an
observed sidebar control selected that same task and rendered its exact final
response with Stop cleared; RPC independently confirmed the saved command result.
Older-instance task import remains separate from this close/reopen acceptance.
Final installed closes captured 30/29/29 processes and each exited normally
with zero remainder. The final check, 27.6 seconds after close, found debug port
19229 closed and Native PID 2890 alive; no additional OAuth was requested.

## Protected review gates

Candidate `0653216` was denied for an unexamined Native dependency upgrade.
`93ad9d5` narrowed the update to the sandbox desktop; review then required its
exact package/launcher/runtime code. `ed913e5` supplied bounded upstream evidence
and received a fresh source/closure-bound approval. No review rule was weakened.
The [evidence index](reviews/agent-desktop-664436c7.md) preserves the full artifact
in that approved commit and immutable source while avoiding vendor-code
duplication in every future bounded review. Reports never authorize deployment.

The local desktop task queue remains private, ignored state; the committed
snapshot excludes it. Native credentials/profile and prior work were preserved.

## Unattended follow-up

Post-acceptance relay hardening and review-capacity changes are now installed.
Focused fixtures and a fresh protected deployment pass;
[overnight notes](OVERNIGHT_VALIDATION.md) distinguish remaining physical checks
from the initial GUI acceptance evidence above.

## Later work

The required installed workflow passed. Final documentation follows the approved
implementation commit; no additional activation is needed for this report.

Later: actual reboot/rollback, portal file selection, long-build cancellation,
application-specific broker identity, full command auditing, GUI egress isolation,
older-instance session recovery, and independent backup/restore testing.
Same-UID host programs can call fixed broker capabilities; model review is fallible.
Permitted traffic can disclose accessible workspace data. Generation rollback does
not restore workspace/private-state writes; see [recovery](RECOVERY_RUNBOOK.md).
