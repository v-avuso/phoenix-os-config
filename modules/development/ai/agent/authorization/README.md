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
  authentication. That explanation UI is planned; this adapter does not implement it.

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

Ordinary `phoenix-test`, `phoenix-switch` and `phoenix-boot` need no handwritten
reason. Configured activation supplies neutral audit context such as
`Direct phoenix-switch invocation`; this describes the entry point, not proven
human identity. Explicit legacy `--reason`/`--task` remain compatible. Deployment
still follows the installed security-review or authenticated-human decision.

Agents should use structured arguments:

```sh
ai-broker --task config-fix --reason 'Validate the requested configuration' -- phoenix-test --branch feature
ai-broker --task usb-debug --reason 'Inspect the current kernel log' -- phoenix-admin dmesg
```

`--reason` is required, bounded to 300 characters and nonsecret; `--task` defaults
to `ai-broker` and is bounded to 100 characters. This first adapter accepts
structured argv after `--`, rather than an illustrative quoted full-command
string. It never invokes a shell or selects executables from PATH. The closed
mapping contains only installed `phoenix-test`, `phoenix-switch`, `phoenix-boot`
and `phoenix-admin` clients. Activation accepts one `--branch` or absolute
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
the authenticated deployment helper; the adapter never introduces legacy
nixos-rebuild activation. Ordinary legacy build/dry-build wrappers remain intact
when that module is disabled. A configured helper failure never falls back.

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
The current static helper messages cannot embed this arbitrary reason directly:
[pkexec's documented message variables](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html#pkexec-variables)
cover program, command line and user data. A title alone does not satisfy the
planned readable explanation. The separate explanation UI remains future work;
current clients display terminal context before their existing authentication.
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

## Audit and verification

Root authorization records use the fixed syslog identifier
`phoenix-authorization`, structured JSON, peer UID/PID, operation/task/nonsecret
reason, decision, outcome and generated ID. They exclude source, diagnostic
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
`python3 -B modules/development/ai/agent/authorization/tests/ai-broker.py` with
the module's admin/deployment/review/updater/command fixtures. These tests stub OS
authentication/execution and do not establish live Polkit, socket group migration,
activation or contained-host acceptance. Distinct client/updater UIDs are covered through the production controller
validator with mocked OS/build execution; malicious source and manual operations
are rejected, and accepted updates stage only the next boot with zero AI/Polkit.
Live protected-identity updater acceptance remains pending. Nix packages the library/policy paths
explicitly; standalone store scripts must not search for sibling files. Legacy
fixture configs without a policy use repository-only compatibility defaults;
an installed store library fails closed when its policy is absent.
