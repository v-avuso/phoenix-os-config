# Architecture

## Current Layout

```text
phoenix-os-config/
  flake.nix
  README.md
  hosts/
    vm/
      configuration.nix
      hardware-configuration.nix
      vm.nix
    metal/
      configuration.nix
      metal.nix
      fan-control.nix
  modules/
    default.nix
    base.nix
    desktop.nix
    shell.nix
  bin/
    phoenix-target
    phoenix-rebuild
  shell/
    phoenix-aliases.sh
  docs/
```

## File Responsibilities

| File | Purpose |
| --- | --- |
| `flake.nix` | Defines NixOS host targets |
| `hosts/vm/configuration.nix` | VM host entrypoint |
| `hosts/vm/hardware-configuration.nix` | Ignored, machine-local VM hardware config |
| `hosts/vm/vm.nix` | VM-only options |
| `hosts/metal/configuration.nix` | Bare-metal host entrypoint |
| `hosts/metal/hardware-configuration.nix` | Ignored, machine-local bare-metal hardware config |
| `hosts/metal/metal.nix` | Metal-only options |
| `hosts/metal/fan-control.nix` | Metal-only CoolerControl, sensor tooling, and NCT6687D driver setup |
| `modules/default.nix` | Shared module bundle imported by hosts |
| `modules/base.nix` | Shared baseline system config |
| `modules/desktop.nix` | Shared desktop/fallback GUI config |
| `modules/shell.nix` | Installs Bash helper functions for interactive shells |
| `bin/phoenix-target` | Detects the intended flake target |
| `bin/phoenix-rebuild` | Runs `nixos-rebuild` with an explicit target |
| `shell/phoenix-aliases.sh` | Defines interactive helper functions |
| `docs/SPEC.md` | What the project must do |
| `docs/ARCHITECTURE.md` | How the repo is structured |
| `docs/RECOVERY_RUNBOOK.md` | Fresh-install/recovery execution guide |
| `docs/MANUAL_STEPS.md` | Manual setup still outside declarative config |
| `docs/DECISIONS.md` | Lightweight decision log |
| `docs/FAN_CONTROL.md` | Bare-metal fan policy, Windows reference mapping, and Linux discovery procedure |

## State Boundary Model

| Class | Belongs In Repo? | Examples |
| --- | --- | --- |
| Declarative system config | Yes | packages, services, users, shell defaults, desktop config |
| Hardware config | No, machine-local | filesystem UUIDs, bootloader device, kernel modules |
| Public recovery docs/scripts | Yes | runbooks, helper commands, non-secret bootstrap notes |
| Private bootstrap material | No | SSH private keys, Git signing keys, Syncthing identity |
| User state | No | browser profiles, editor state, synced folders, KeePass databases, notes |
| Secrets | No plaintext | tokens, passwords, service credentials |
| Disposable data | No | caches, build output, logs |

The repository describes the desired public system layer. It must be enough to
rebuild the workstation shape, but not enough to impersonate the user or restore
private data by itself.

## Modularization Model

Start simple. Split only when it improves local reasoning.

Current module boundaries:

- `modules/default.nix` bundles shared modules; hosts import it as `../../modules`
- `modules/base.nix` for shared boot, networking, locale, users, and Nix settings
- `modules/desktop.nix` for GUI/session/display manager config
- `hosts/<target>/` for host-local configuration and generated hardware config

Avoid further abstraction until repeated responsibility justifies it.

## Desktop Model

Target direction:

- Hyprland/Caelestia-style Wayland desktop is the intended primary workstation
  experience.
- KDE Plasma is intentionally kept as a comfortable fallback and repair
  environment.
- Current implementation is still Plasma-only in `modules/desktop.nix`; target
  desktop docs may lead implementation while this migration is early-stage.

## Rebuild Model

Primary feedback loop:

```bash
phoenix-test
phoenix-switch
```

Use `test` for low-risk validation before committing to the boot profile. Use `switch` once behavior is acceptable.
Explicit path flake targets, such as `sudo nixos-rebuild switch --flake path:.#vm`, are the fallback when helpers are not loaded and the host hardware file is already present.

`config/user.nix` defines the local checkout path as `repoDirectory`.
`modules/shell.nix` uses that value as the default `PHOENIX_REPO_ROOT` for
interactive Bash shells. Machines with a different checkout location should
change `repoDirectory` in `config/user.nix`; one-off sessions can still override
`PHOENIX_REPO_ROOT` in the shell profile. The helper functions source the live
checkout when available so helper changes are picked up without baking a stale
repo path into the Nix store.

## Recovery Model

Recovery means:

1. Install NixOS.
2. Restore/clone this repo.
3. Place hardware config appropriately, reviewing disk-specific values.
4. Apply the pinned flake target with an explicit `vm` or `metal` selection.
5. Restore secrets, bootstrap material, and user state from separate trusted
   sources.
6. Re-clone work repositories and verify the system.
