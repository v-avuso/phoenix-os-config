# Agent sandbox acceptance

Last updated: 2026-10-04. See [the operating guide](AGENT_SANDBOX.md) for lasting
behavior, boundaries and rationale.

## Outcome

**CLI containment, bounded diagnostics and independently reviewed unattended
activation work. The corrected GUI candidate also works; final installation is
pending.** The corrected desktop opens
normally in Codex mode with the existing project and no onboarding/profile
warnings. Updating the maintained desktop input to official 26.930.31730 also
restored actual tool/final-result rendering. Two normal close/reopen cycles pass
with saved authentication and project state. The sandbox-only lifecycle adapter
disables unavailable tray hiding and uses upstream normal quit after the last
tracked primary closes, including hidden service-window cleanup. Native remains
the everyday repair route until the final installed launcher is verified.
Work resumed after the user's compute-budget pause. Desktop acceptance remains
the current delivery gate; component success does not replace that check.

Music and general engineering guidance from `main` are merged into
`codex/agent-sandbox-broker`. No previous work or native profile was discarded.

## Installed evidence

The latest independently approved persistent switch is source commit `7c169d7`:

- Source: `/nix/store/3ip2bx7a2jsq5k3gsh62sykrz6cxrc98-source`.
- System profile (next boot):
  `/nix/store/yamlcrh41pagdr1bbjfc1rpr4kc56gg6-nixos-system-phoenix-26.05.20260924.c508844`.

A fresh protected `test` installed commit `59ccb3d` without Polkit on resume:

- Recorded runtime source: `/nix/store/5a688xsz8cjjhfnh8r598cmrmbpsbi1n-source`.
- Runtime: `/nix/store/wfjdjf0lfdzv9zh04yjmjzsjg47368f7-nixos-system-phoenix-26.05.20260924.c508844`.

That test did not update the next-boot profile. A subsequent GUI-only candidate
removes an invalid tray bus ownership pattern before further interactive checks;
it is not yet the persistently installed system. Commit `902d56f` then updates
only the maintained desktop input; the GUI-only candidate builds and renders an
actual task against the installed relay, without changing the installed system.

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
| Interactive GUI | Updated candidate shows normal window, Codex mode and approved project without onboarding/profile warnings; actual GUI model/tool markers render and Stop clears, using outer containment and on-request approval |
| GUI lifecycle | Two candidate normal close/reopen cycles exit 0, stop all 30 captured processes and release the profile lock; saved auth/project/mode retained, Native untouched. Final installed launcher remains the acceptance gate |
| Launcher | Sandboxed favourite set and Native not favourited in actual Caelestia settings; final fuzzy-search ordering needs user confirmation |

The earlier generic deployment review failure did not activate. Its installed
controller discarded the distinction between denial and API/schema failure.
The current worker/controller distinguish bounded model denial from invocation,
schema and binding errors; model text returns only to the requesting owner,
never to the journal. A separate one-time review-only diagnostic could not activate.

## Remaining core acceptance

Selected preference migration and fixed scalar app-server overrides are installed
by the protected test. The initial launcher then rejected an invalid tray bus
ownership pattern before Electron started; the corrected GUI-only candidate is
under interactive acceptance. Native and the retained gateway/reviewer login
remain intact. The maintained desktop candidate now passes task rendering and
normal close/reopen; the Linux lifecycle fixture covers normal quit gating and
no-write rejection of upstream wiring drift.

1. Independently install the corrected launcher's clean committed
   source. Reuse
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
Independent daily backups and restore testing remain separate recovery work;
generation rollback does not restore workspace or private-state writes (see
[recovery](RECOVERY_RUNBOOK.md)).
Same-UID host programs can call fixed broker capabilities; Python has limited
desktop API authority; permitted traffic can disclose accessible workspace data.
Model review is fallible. The user accepts these stated limits.
