# Phoenix authorization

This module owns the installed version 1 decision policy and the small Python
library shared by the diagnostic broker, deployment controller and their clients.
It composes the existing bounded dispatch, immutable source/build engine and
native Polkit authentication; it adds no daemon, audit database or arbitrary
privileged command interface.

## Intentions

- Keep ordinary Phoenix activation usable without a handwritten reason while retaining
  authenticated, frozen-source deployment and the installed decision policy.
- Give agent requests a separate bounded reason/task interface and fixed command set;
  reasons are audit context, never proof of a human or agent identity.
- Present a readable command, short reason and broker decision before native Polkit
  authentication. Its experimental implementation stays off until isolated native
  GUI acceptance; presentation never supplies execution authority.

## Exact registered commands (experimental, OFF)

`phoenix.authorization.commands.enable` explicitly opts into an empty-by-default
registry. Each `entries.NAME` supplies an immutable installed ELF `executable`
(for example a Nix package interpolation plus `/bin/program`), exact `arguments`,
nonempty bounded `rationale`, `mode = "automatic" | "review" | "human"`, and a
1–60 second `timeout`. Disabling the feature retains definitions but rejects all
execution and removes its Polkit actions. Enabled review entries currently require
explicit `securityReview.enable`: this reuses the existing protected provider,
not an enduring requirement to couple these responsibilities or auto-enable them.

```sh
phoenix-authorize --task bounded-operation --reason 'Requested diagnostic purpose' -- phoenix-command NAME
# Only after a rejected/unavailable review and explicit operator authorization:
phoenix-authorize --task bounded-operation --reason 'Authorized exact override' -- phoenix-command --human-override NAME
```

The caller selects only an installed identifier and context, never a program,
argv, environment, source snapshot or verdict. Existing deployment/diagnostic
routes and human Phoenix/sudo are unchanged. The existing capable root controller
owns the disjoint socket envelope; the diagnostic daemon retains CAP_SYSLOG.
No new root daemon, global sudo interception or generic shell is introduced.

Automatic entries use a reviewed deterministic grant. Human entries enter the
normal fixed native Polkit helper after a matched root decision. Review entries
use retained protected Luna/high and the existing isolated reviewer loop with a
command-specific policy; root independently validates the complete bound verdict.
Denial/error never automatically prompts or executes. Explicit override has a
separate **CRITICAL SECURITY OVERRIDE** immutable helper/action, fresh `auth_admin`
and operator UID check; the ordinary human helper cannot execute review entries.
Contained clients give an exact native route instead of mounting authentication.
Reviewer denial rationale is sanitized/bounded advisory client text; typed static
errors preserve causes without raw model stderr. Command output and model-generated explanation are excluded from
the controller authorization journal; supplied bounded nonsecret task/reason are
recorded as request context.

Root checks both declared/resolved Nix-store paths, root-owned nonwritable objects,
ELF identity and program bytes. Immutable argv[0] is preserved for multicall tools.
Scripts, known shell/interpreter/trampoline families and generic execution flags
are unsupported. This is an exact program/argv binding, **not** proof that ELF code,
all dependencies or mutable inputs are safe. Do not register operations whose
privileged effects depend on unbound mutable scripts/configuration/data. Published
root code remains trusted; this is not an adversarial root-code sandbox.

A current `/etc/phoenix-authorization/command-authority.json` publication binds the
registry, helper/controller/reviewer implementation, prompt, provider and configured
identities. Old controllers/helpers and cached approvals reject a changed current
publication, including after slow review and before execution. Root-only exact
approvals also bind program bytes, argv, caller, task/reason; TTL is 120 seconds,
at most 32 records. No automatic rule publication or persistent self-learning occurs.
Execution uses a fixed sanitized environment and owned transient systemd cgroup
with a 1–60 second runtime bound, two-second stop bound and 64 KiB combined output.
The fixed cleanup stops/resets that unit, including setsid descendants. It cannot
make arbitrary trusted root code incapable of delegating to other host services.

Command review permits at most two CLI invocations of 120 seconds, one existing
bounded context round (eight ranges/128 KiB), and a 300-second outer worker bound;
no automatic retries. Native CLI internal API requests/tokens are not hard capped.
Deployment review retains its existing 600-second per-invocation default.

An agent may propose a narrow Nix definition/rationale and publish it through the
existing independent deployment diff review. Grant broadening is an authority
change. This reviewed maintenance workflow removes a manual editing bottleneck;
it is not an automatic adaptive publisher. No recurring unsupported operation
family is evidenced yet, so the repository installs no live entries. Universal
arbitrary root requests remain outside this partial closed-registry surface.

The disposable [root/socket fixture](tests/command-root.nix) passed with real root
UID/socket admission, exact verdict/cache checks, cache expiry/revocation, old-helper
revocation, actual multicall ELF execution, bounded output and setsid cgroup cleanup.
Evidence: `/nix/store/3mm3dmvq9c1r3iv56pcvhh2yimgcbgg9-vm-test-run-phoenix-command-root/evidence`.
The final trial also checks normal-helper rejection of review entries, separate
critical-route operator checks, and structured request/decision/result audit with
validated task/reason and cache/new/critical distinctions; output canaries are absent
from the controller and authorization journals. Socket records use kernel peer UID/PID;
authenticated helper records use the checked operator UID and helper process PID.
Its reviewer and native authentication are explicit doubles. It does not prove retained
model judgment, native Polkit dialog UX, executable dependency safety or host use.
Keep OFF pending representative real-model/native-auth acceptance and explicit
approval of the caller boundary. Protected identity is still OFF: shared host UID
is a limitation, not proof that requests came from Codex or from a human.

## Future protected policy maintenance

Adaptive protected allowlist publication remains unimplemented. Persistent policy
and rationale remain Nix/version-tracked; only independently reviewed protected
publication may widen them. Root approval cache is not a growing rule registry.
Keep future controls explicit opt-in with dependency assertions and bounded trials.
[Sudo approval plugins](https://www.sudo.ws/docs/man/sudo_plugin.man/) run after
policy acceptance; [agent-sudo](https://github.com/Z7Lab/agent-sudo) checks the program
while passing arguments through. Neither supplies this exact argv/immutable
publication/review contract. Codex auto-review is not OS root authority.

## Public gate and deterministic diagnostics

`phoenix-authorize` is the neutral public authorization gate; `ai-broker` remains
an equivalent supported alias in the same package, including its historical default
task label. Existing launchers and human Phoenix/sudo commands are unchanged.
Both names map fixed typed argv to existing clients, never a shell. Reasons and
task labels are context, not authority.

`phoenix.authorization.automaticDiagnostics.enable` defaults to `true`, preserving
the seven deterministic automatic defaults. Set it to `false` to default every
operation to native human authentication; explicit `denied` remains denied.
An explicit per-operation `automatic` with the flag off fails a Nix assertion.
Each option's description records its bounded read or reversible-toggle rationale;
this switch expands no operation, device or service allowlist. Deployment security
review remains independently controlled, and review-off still requires human
authentication with immutable binding and rollback.

Future review/policy-publication responsibilities need explicit opt-in Nix options
and assertions for their required controller/adapter capabilities. Availability of
a dependency must never auto-enable authority. Route deployment to its existing
diff reviewer without a second generic AI pass; unsupported command families and
mutable inputs that cannot be frozen require native human fallback. No generic
hook engine is introduced; exact registered-command review is a separate opt-in feature.

Focused checks (evaluation/build only, no activation):

```sh
nix eval --impure --file modules/development/ai/agent/authorization/tests/automatic-diagnostics.nix
nix build --impure --no-link --file modules/development/ai/agent/authorization/tests/alias.nix
```

## Requests and policy

A metadata request contains exactly `version`, `operation`, `arguments`, `task`
and `reason`. Operations are named `admin.dmesg`, `admin.service-status`,
`deployment.test`, etc. Arguments are typed semantic fields (for example integer
`lines`, allowlisted `service`/`device`, and installed deployment `target`). Unknown
operations, fields, caller-selected modes/configuration and executable arguments
are rejected. Task labels are 1–100 characters; reasons are nonempty, at most 300
characters, with Unicode control/format categories rejected. Reasons are caller
context, never permission. **Do not put secrets in reasons:** validation cannot
recognize every secret, and accepted reasons appear in the authorization journal.

`phoenix.authorization.diagnostics.<name>` selects `automatic`, `human` or
`denied` for the existing closed diagnostic set. Defaults preserve automatic
bounded diagnostics. `services.phoenixDeployment.securityReview.enable` is the
single deployment decision owner: disabled means authenticated human deployment;
enabled means the existing security review engine. Its old `modelReview.enable`
option remains an alias. Ordinary deployment has no automatic setting. Routine
`deployment.update` is fixed automatic and still requires the existing deterministic
validator; it uses neither AI nor Polkit. Default experimental controls stay off.

## Command interface

Human `phoenix-test`, `phoenix-switch` and `phoenix-boot` run the original
`nixos-rebuild --sudo` route, retaining terminal sudo/fingerprint authentication,
rebuild progress and option forwarding. No reason is required. Optional legacy
`--reason`/`--task` are accepted without creating broker audit context.

Agents must use the explicit broker interface below. Its fixed mapping invokes
the immutable deployment client directly with action derived from the closed
command name and target from installed policy; it never calls the human wrapper.
Broker review/reservations protect broker-mediated requests, not administrator
sudo/rebuild. With protected identity off, human/agent instructions under one UID
are not kernel-enforced identity separation; root authentication still applies.

Agents should use structured arguments:

```sh
ai-broker --task config-fix --reason 'Validate the requested configuration' -- phoenix-test --branch feature
ai-broker --task usb-debug --reason 'Inspect the current kernel log' -- phoenix-admin dmesg
```

`--reason` is required, bounded to 300 characters and nonsecret; `--task` defaults
to `ai-broker` and is bounded to 100 characters. This first adapter accepts
structured argv after `--`, rather than an illustrative quoted full-command
string. It never invokes a shell or selects executables from PATH. The closed
mapping contains only `phoenix-test`, `phoenix-switch`, `phoenix-boot` deployment
operations bound to the installed immutable client, plus the installed
`phoenix-admin` client. Activation accepts one `--branch` or absolute
`--worktree`, plus optional absolute `--reservation-file`; diagnostic arguments
are the existing typed named operations, optionally preceded by an absolute
`--reservation-file`. Inner reason/task overrides, arbitrary
flags, commands and pipelines are rejected before execution. Inputs are capped
at 16 command arguments, 4096 characters per argument and 16 KiB combined UTF-8.
The underlying clients/controllers retain source, path, reservation and peer
validation. The authorization-owned adapter fixes library/policy/client paths at packaging;
the generic command factory has no authorization-policy dependency. No new
policy decision service or caller-selected configuration is introduced.

Native home and OpenShell tool composition include the adapter when their
installed authorization dependencies are supplied. Activation mappings require
the authenticated deployment helper; missing mappings or helper failures never
fall back to legacy activation. Human wrappers and deterministic updater controller
requests retain their separate existing ownership.

## Execution and authentication

Clients request metadata-only preflight from the existing root socket before
freezing source. Preflight checks kernel peer UID/PID, generates an audit ID and
returns only the installed decision. It never freezes source, builds or invokes
AI. Operator group membership admits the native operator to sockets when the
contained client has another UID. Ordinary operator socket admission is metadata only. The fixed installed
`updaterUid`, derived from the static account named by
`phoenix.authorization.updaterUser` (default: the operator), may execute only
`deployment.update`; other socket execution still requires the client UID.
The update service and socket membership use that same declarative account; an
assertion rejects a conflicting generated service `User` override. Callers cannot
select a role or UID. The controller reads kernel peer credentials
and rechecks the same installed predicate before execution. An operator using
native Polkit still has the existing separately authenticated human authority.

Human routes use fixed immutable Polkit helpers with native dialog messages/icons.
[pkexec's documented message variables](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html#pkexec-variables)
cover program, command line and user data, not arbitrary reason details. The
experimental explanation therefore precedes the existing Polkit dialog; it does
not replace the password agent or capture credentials. The extra Continue click
is a usability cost until a supported native authentication agent can present
rich request context directly. Ordinary Phoenix commands retain their existing
single authentication flow.
Each helper independently validates installed policy, typed arguments and the
supported `PKEXEC_UID` operator identity; it shares the same actual dispatcher or
controller. It accepts no executable/configuration selector. Direct legacy socket
requests also pass the installed policy. Human diagnostic execution preserves
reservation gates. Every deployment, including AI-disabled deployment, freezes
Git-visible dirty/new/deleted content and binds the resulting immutable source to
its build before activation; existing rollback/disruption/security override rules
remain in force.

A preflight ID is correlation context only. Executing processes generate their own
IDs and record a syntax-checked `clientPreflightId` separately; a forged well-formed
ID grants no authority. Invalid requests log only static categories. Contained
human requests return `host-authentication-required` and a fixed copyable native
host command. Authentication mounts and containment bypasses are unnecessary.

## Native explanation (experimental, default off)

`phoenix.authorization.explanation.enable` is the single presentation switch and
defaults to `false`. Off keeps ai-broker's established terminal context and native
Polkit authentication; reasons and installed decisions remain enforced. Off also
keeps unused Zenity and its GUI dependencies out of this feature's closure.

When enabled, the packaged adapter carries the fixed `--authorization-context`
flag into its existing clients. After root preflight agrees with installed policy,
only native `human` requests use one shared module-owned Zenity question dialog.
Its body shows the semantic command/operation, typed arguments, task, bounded
nonsecret reason, decision and static policy explanation; deployment additionally
shows the actual selected source path after freezing its request. Caller text is
escaped as Pango markup. The pinned [Zenity 4.2.2 question options](https://raw.githubusercontent.com/GNOME/zenity/4.2.2/src/option.c)
support custom button labels and default Cancel focus. Cancel or display failure
stops before privileged execution; Continue calls the same immutable helper with
the same already-frozen body. Display timeout is bounded to five minutes, and no
UI stdout/stderr is captured or logged. An explicit context request fails closed
when display is disabled/unavailable, without a silent terminal fallback.

Automatic diagnostics and security-review routes show no generic context dialog.
Denied policy stays denied. Critical exact-pending security/disruption overrides
retain their separate flow and cannot combine with this generic flag. Contained
human requests show a copyable native `ai-broker` command; they open no UI and
receive no authentication mounts. The flag carries no authenticated identity or
authority; the actual helper independently validates policy and frozen input.

Fixture coverage establishes rendering, escaping, cancellation, fixed helper/body
binding and default-off behavior. Real native readability, window focus, Continue
and Polkit cancellation remain isolated GUI acceptance work before enabling.

## Audit and verification

Root authorization records use the fixed syslog identifier
`phoenix-authorization`, structured JSON, peer UID/PID, operation/task/nonsecret
reason, typed semantic arguments, decision, outcome and generated ID. They exclude source, diagnostic
output, model stderr and credentials. Client validation/authentication failure or
cancellation records are explicitly `trusted=false`; they prove no root approval.
To inspect only records actually emitted as root:

```sh
journalctl SYSLOG_IDENTIFIER=phoenix-authorization _UID=0 --output=cat
```

Storage/rotation follow native journald configuration. This repository sets
`SystemMaxUse=1G`, `RuntimeMaxUse=512M` and `MaxRetentionSec=30day` in
`modules/security/default.nix`; this module does not assert a persistent journal
path or create its own retention system.

Run `python3 -B modules/development/ai/agent/authorization/tests/request.py` and
`python3 -B modules/development/ai/agent/authorization/tests/ai-broker.py` and
`python3 -B modules/development/ai/agent/authorization/tests/presentation.py` with
the module's admin/deployment/review/updater/command fixtures. These tests stub OS
authentication/execution and do not establish live Polkit, socket group migration,
activation or contained-host acceptance. Distinct client/updater UIDs are covered through the production controller
validator with mocked OS/build execution; malicious source and manual operations
are rejected, and accepted updates stage only the next boot with zero AI/Polkit.
Live protected-identity updater acceptance remains pending. Nix packages the library/policy paths
explicitly; standalone store scripts must not search for sibling files. Legacy
fixture configs without a policy use repository-only compatibility defaults;
an installed store library fails closed when its policy is absent.

The build-only `authorization/tests/presentation.nix` fixture checks off/on
packaging and exposes native client/broker/admin/config outputs without opening
a dialog. Stage owned new files before its Git-flake evaluation; no activation or
live authentication is part of that build.
