# Protected desktop unit deployment guard

`services.phoenixDeployment.disruptionGuard.enable` defaults to **false**.
Keep it off until isolated VM/systemd/Polkit/session acceptance passes.

The installed controller owns a fixed list of display/login/session, Kando,
Timewall, OpenShell and GUI relay units. It reads active states with the installed
systemctl, including the operator's user manager through its supported local
machine transport. Query failure requires human inspection. Candidate configuration
cannot remove the installed policy. Build/dry-build and boot staging are unaffected;
routine `update` uses the existing boot-only activation action and zero AI calls.

Before activation dispatch and again inside the actual service's stable activation
lock (and reservation operation when enabled), the guard compares immutable unit
files, drop-ins and incoming/outgoing wants/requires links for active protected
names. Dependency links compare target file contents rather than generation paths.
The actual native Home Manager service must have exactly one `hm-setup-env`
ExecStart and one immutable `home-manager-generation` argument; its fixed
`home-files/.config/systemd/user` subtree supplies user units. Unsupported layouts
require inspection. A narrowly verified native display-manager no-restart case
allows changed service contents only with unchanged Unit/dependency semantics,
no drop-ins, explicit restart suppression in both generations and no reload request.
Other protected changes remain conservative.

## Human exceptions

The CLI reports the frozen source and closure fingerprints, target/action, protected
unit findings and proof limit. It never prints source text or task reason as approval
authority. A rejection creates at most 32 root-owned pending records with GC roots.
Native operators can authenticate one exact exception:

```sh
phoenix-deploy-review --disruption-override PENDING_NONCE
```

When reservations are enabled, acquire a fresh operator reservation for
`deployment.override` and supply `--reservation-file PRIVATE_FILE`. A distinct fixed
Polkit helper uses fresh `auth_admin`, never retained authentication. The CLI displays
root-owned pending metadata before authentication; the fixed warning does not
promise dynamic Polkit dialog details. Authentication binds source, closure,
target/action, caller, runtime, profile/baseline, installed policy, active state and
findings. The exception is consumed before dispatch and repeated inspection must
match it. Failed activation never leaves reusable disruption authority. Later source
edits cannot change the frozen request; a different closure requires a new request.
Changed runtime/profile/policy requires a new pending decision.

Security approval remains independent: an outstanding failed security decision
cannot be approved by a disruption exception. An authenticated security override
consumes its exact security pending record after publishing security approval,
before activation; a resulting disruption rejection requires its separate helper.
With AI disabled, ordinary native deployment still requires existing human Polkit
authentication. The guard adds no AI calls, daemon, lock namespace or activation
script execution during inspection.

## Proof limits and verification

This is a unit guard, not a complete activation planner. It does **not** detect
arbitrary activation shell commands that directly restart services, kill processes
or affect a compositor. It does not fingerprint entire closures or HM generations,
parse general shell, execute candidate dry-activation, or set `NIXOS_NO_CHECK`.
AI-disabled human authorization of the whole activation remains the hook boundary;
optional AI review retains only its security remit. Unlisted applications and
runtime effects outside concrete unit metadata are outside this protection.

Run `python3 -B modules/development/ai/agent/tests/disruption.py` and the existing
deployment/reservation fixtures. The Python fixtures use explicit immutable ownership, active-manager and
activation recorder stubs. The bounded VM evidence below exercises real ownership,
manager queries and the actual reserved activation helper with a recorder. Actual installed artifact inspection
is read-only; source/fixture checks do not establish live GUI, systemd or Polkit
acceptance. Sandbox denial of the user bus must remain typed inspection failure,
never a reason to broaden access merely for validation.

## Isolated systemd evidence

The existing reservation-lifetime VM now includes a real guest user manager and
an active idle `kando.service` stand-in. Its generated systemd artifact and synthetic
immutable HM generation use identical unit bytes; the fixed `hm-setup-env` plus
one generation argument preserves the strict metadata schema. The actual
`activate_reserved` helper, reservation operation and stable activation guard permit
unchanged artifacts and reject changed unit bytes or unsupported HM metadata before
any recorder invocation. Earlier reservation/client-death/expiry checks still ran.
No real desktop application or Home Manager migration was exercised.

The full extended reservation-lifetime gate now passes from frozen fixture source
`/nix/store/gv87hi6aa3k6b4zvgwgrgc7jna6cnzb3-source`, output
`/nix/store/lhbrki88lza1rg5s9wv0qrpx9bpjl431-vm-test-run-phoenix-reservation-lifetime`.
The guest runtime-masks `user@1000.service` before stopping it, preventing the
stdio bridge/PAM from simply restarting the manager. The exact supported query
`systemctl --user --machine=client@.host show --property=Id --property=ActiveState
-- kando.service` returns 1. Production inspection reports
`active-unit-query-unavailable`; actual `activate_reserved` returns typed
`disruption: inspection-required`, with no recorder invocation. Unmask/restart
restores the active stand-in and unchanged-artifact pass. The full reservation,
mutation-lifetime, recovery, release and capability-nondisclosure checks finish
in 23.11s under the existing 210s guest bound.

Stopping the manager alone is not a valid unavailability stimulus: the supported
bridge can restart it and validly report inactive units. The prior red attempt used
that invalid stimulus; the new pass proves the bounded query-failure gate, not a
product repair. Exact operator exception publication/consumption and native Polkit
acceptance remain pending. No live desktop, real activation or Home Manager
migration is proved by the recorder.

Deployment's dynamically imported disruption, security-review and routine-update
helpers are now individually packaged immutable files. Enabled and disabled
configuration derivation closures retain all three; metal/VM evaluation passes.
This establishes packaging, not model/updater/runtime acceptance. The guard remains
OFF and cannot detect arbitrary disruptive activation shell effects.
