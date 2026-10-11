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
deployment/reservation fixtures. Disposable tests use explicit immutable ownership,
active-manager and activation recorder stubs. Actual installed artifact inspection
is read-only; source/fixture checks do not establish live GUI, systemd or Polkit
acceptance. Sandbox denial of the user bus must remain typed inspection failure,
never a reason to broaden access merely for validation.
