# Agent sandbox acceptance

Last updated: 2026-10-03. See [the operating guide](AGENT_SANDBOX.md) for lasting
behavior, boundaries and rationale.

## Outcome

**CLI containment, bounded diagnostics and independently reviewed unattended
activation work. GUI acceptance is still pending.** The corrected desktop account
connection works, but its first interactive launch exposed profile contention
and unwanted onboarding/maximized startup. Those are being corrected before
calling the desktop usable. Native remains the everyday repair route.
Work is paused at the user's compute-budget request; no new GUI or deployment
trial should start until the user resumes.

Music and general engineering guidance from `main` are merged into
`codex/agent-sandbox-broker`. No previous work or native profile was discarded.

## Installed evidence

The latest independently approved persistent switch records source commit
`7c169d7` in `/etc/phoenix-agent/activated-source`:

- Source: `/nix/store/3ip2bx7a2jsq5k3gsh62sykrz6cxrc98-source`.
- Runtime and system profile:
  `/nix/store/yamlcrh41pagdr1bbjfc1rpr4kc56gg6-nixos-system-phoenix-26.05.20260924.c508844`.

Later documentation commits do not change that recorded runtime source.

| Check | Actual result |
| --- | --- |
| Evaluation/build | Metal/VM/default combined evaluation and committed metal system builds pass; VM bootability is not established |
| Focused fixtures | Broker 12, launcher 10, preferences 4, deployment/reviewer 22, HTTP 10, socket connections 2; GUI concurrency/activation/boundary and Node streaming/cancellation fixtures pass |
| Reviewer bootstrap | Retained authentication migrated once to the protected reviewer account; no repeated OAuth |
| Unattended activation | Fresh protected `test` passed; real OpenShell worker requested fresh `switch`, which updated runtime and boot profile without Polkit |
| Exact-source review | Controller built as a dedicated unprivileged user and reviewed frozen source, installed diff and resulting closure; journal records approved/activated stages |
| Deployment denial | Actual worker's arbitrary-command request rejected before build/review/activation; malformed/stale/denied verdict and recovery branches covered by fixtures |
| Real worker | Rootless UID 1000; approved repository visible, Native SSH/Pictures/auth omitted, `/etc` write denied, unexpected destination fails |
| Diagnostics | Allowlisted cooler service state and xHCI wakeup read pass without authentication; unlisted service and arbitrary root operation denied |
| GUI backend | Actual account/profile/routing lookup passes; exact relay model/tool task using GPT-6 Luna/high completed with expected shell output |
| GUI isolation | Private home and declared workspaces; Native auth/SSH/Pictures and host control sockets omitted; actual portal Settings.Read passes and host systemd bus access is denied |
| Interactive GUI | Corrected public identity makes account lookup authenticated; Work denial disappeared in controlled retry, but onboarding/window behavior and existing settings reuse still need acceptance |
| Launcher | Sandboxed favourite set and Native not favourited in actual Caelestia settings; final fuzzy-search ordering needs user confirmation |

The earlier generic deployment review failure did not activate. Its installed
controller discarded the distinction between denial and API/schema failure.
The current worker/controller distinguish bounded model denial from invocation,
schema and binding errors; model text returns only to the requesting owner,
never to the journal. A separate one-time review-only diagnostic could not activate.

## Remaining core acceptance

The checkpoint contains selected preference migration, fixed scalar app-server
overrides and tray-based single-instance activation, but these changes are **not
installed**. Their fixtures pass. GUI trials and the temporary loopback debug
endpoint are stopped; temporary user relay overrides were removed. Native and
the retained gateway/reviewer login remain intact.

1. Build and independently review/install the clean committed checkpoint. Reuse
   selected existing nonsecret GUI/model/project preferences, open a normal
   movable window without onboarding or profile warnings, and run a task through
   the actual Codex GUI. No additional browser sign-in.
2. Close/reopen that GUI and verify retained settings/login and safe single-instance
   behavior; remove all temporary debug endpoints and test overrides.
3. Update this report with the exact final installed source and user-visible result.

## Later checks and improvements

Reboot, destructive rollback, portal file selection and long-build cancellation
have not been runtime tested. Recovery branches pass fixtures; this does not prove
transactional rollback. Do not reboot or induce a failure merely to claim acceptance.

Application-specific caller identity, full command auditing, isolated GUI network
and recovery of sessions retained in older sandbox instances are future work.
Same-UID host programs can call fixed broker capabilities; Python has limited
desktop API authority; permitted traffic can disclose accessible workspace data.
Model review is fallible. The user accepts these stated limits.
