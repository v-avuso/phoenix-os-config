# Project PhoeNix OS

A personal NixOS workstation configuration. Nix files describe the current
system; this README provides orientation, not a second specification. Private
data and credentials are restored separately. This is a reference configuration
for one workstation, not a general-purpose distribution.

## Current system

- **Metal:** Hyprland/Caelestia on Wayland, SDDM login, NVIDIA graphics, and
  CoolerControl with a kernel-backed firmware fan fallback. Plasma is retained
  only on the VM target.
- **VM:** historical Plasma/X11 setup, currently untested. Its tracked hardware
  file is a structural placeholder: evaluation can succeed, but deployment
  requires a real generated hardware snapshot.
- **Home Manager:** integrated into NixOS; owns user packages and selected
  settings. Some settings permit live experiments; see
  [configuration and state](docs/CONFIGURATION_STATE.md).
- **Security:** inbound firewall, AppArmor, and ClamAV scanning of Downloads.
  OpenSnitch currently allows outbound connections and records them for review;
  it does **not** enforce an outbound allowlist. Audit/auditd are disabled.

## Where changes belong

| Path | Responsibility |
| --- | --- |
| `flake.nix`, `flake.lock` | Host outputs and pinned dependencies; `default` aliases `metal` |
| `config/` | Shared user identity, canonical checkout path, and shared facts |
| `hosts/metal/`, `hosts/vm/` | Host entrypoints, hardware snapshots, host-specific behavior |
| `modules/` | Shared system services and policies |
| `home/` | User packages, desktop integration, and application settings |
| `commands/`, `home/commands.nix` | Packaged executables and user PATH registration |
| `patches/` | Targeted compatibility fixes; keep their removal conditions nearby |

Keep modules small enough to understand; introduce abstractions when actual
repetition warrants them. Comments and commit bodies preserve local rationale;
there is no exhaustive decision ledger to maintain.

## Everyday commands

Home Manager installs commands on the user's PATH for Bash, Fish, agents,
scripts, and keybinds. `config/user.nix` defines `repoDirectory`; override the
checkout temporarily with `PHOENIX_REPO_ROOT`. `phoenix-target --info` explains
automatic selection; `PHOENIX_TARGET=metal` or `vm` overrides it.
Command implementations are packaged with the system generation; rebuilds use
the selected live checkout as their flake source.

| Command | Effect |
| --- | --- |
| `phoenix-dry-build` | Evaluate the build plan without building or activating |
| `phoenix-build` | Build the system without activation |
| `phoenix-test` | Build and activate now; leave the next-boot generation unchanged |
| `phoenix-switch` | Build, activate now, and select the generation for next boot |
| `phoenix-boot` | Build and select the generation for next boot; leave the running system unchanged |
| `insomnia` | Inhibit sleep until interrupted |
| `phoenix-logout` | Leave the supported active desktop session |

`phoenix-rebuild <action>` is the dispatcher. For example:

```sh
PHOENIX_TARGET=metal phoenix-build
phoenix-rebuild --print switch
```

`test` changes the live system; it is not an evaluation check. Activation needs
authorization and interactive authentication where required. Agent workflow and
privilege rules are in [AGENTS.md](AGENTS.md).

## Hardware and recovery

Hardware snapshots are intentionally tracked. After reinstalling or changing
storage, generate a snapshot for that installation, review filesystem UUIDs,
boot devices, encryption and swap, then include it in Git. Temporary USB,
bind, network, and VM shared-folder mounts must not accidentally become boot
requirements. Helpers do not bootstrap missing hardware files.

See the [recovery runbook](docs/RECOVERY_RUNBOOK.md) for generation rollback,
fresh installation, and private-state restoration. A NixOS rollback restores
system configuration; it does not restore documents, databases, credentials,
or all mutable settings.

## Operational guides

- [Fan control](docs/FAN_CONTROL.md): safety ownership, hardware discovery,
  reconciliation, and fallback checks.
- [YubiKey PAM](docs/YUBIKEY_PAM.md): enrollment, local authentication, and
  password fallback.
- [Configuration and state](docs/CONFIGURATION_STATE.md): declarative baselines,
  live experiments, and settings persistence.
- [Validation](docs/VALIDATION.md): build checks and one combined manual
  acceptance pass after authorized activation.

OpenSnitch observation is deliberately permissive to avoid repeated connection
prompts. Review local events with
`journalctl -t opensnitchd --since '30 days ago' --all -o json`. Journald's
`MESSAGE` may be a byte array; JSON output preserves its bytes for CLI analysis.
Logs contain private process/network information. Retention is capped at
30 days and 1 GB,
so volume can shorten the available history. Review traffic and test essential
workflows before designing enforcement rules.

## Why Phoenix?

The long-term aim is a secure, recoverable workstation with explicit ownership,
backups, and stronger application isolation. Those are goals, not claims that
all are implemented. [Vision](docs/VISION.md) keeps future direction separate
from current operation; move concrete work into the backlog when ready.
