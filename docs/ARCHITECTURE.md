# Architecture

## Current Layout

```text
phoenix-os-config/
  configuration.nix
  README.md
  hosts/
    vm/
      configuration.nix
      hardware-configuration.nix
      vm.nix
    metal/
      configuration.nix
      hardware-configuration.nix
      metal.nix
  modules/
    default.nix
    base.nix
    desktop.nix
  docs/
```

## File Responsibilities

| File | Purpose |
| --- | --- |
| `flake.nix` | Defines NixOS host targets |
| `hosts/vm/configuration.nix` | VM host entrypoint |
| `hosts/vm/hardware-configuration.nix` | Generated VM hardware config |
| `hosts/vm/vm.nix` | VM-only options |
| `hosts/metal/configuration.nix` | Bare-metal host entrypoint |
| `hosts/metal/hardware-configuration.nix` | Generated bare-metal hardware config, added when available |
| `hosts/metal/metal.nix` | Metal-only options |
| `modules/default.nix` | Shared module bundle imported by hosts |
| `modules/base.nix` | Shared baseline system config |
| `modules/desktop.nix` | Shared desktop config |
| `modules/codex.nix` | Shared Codex-related config |
| `bin/phoenix-target` | Detects the intended flake target |
| `bin/phoenix-rebuild` | Runs `nixos-rebuild` with an explicit target |
| `shell/phoenix-aliases.sh` | Defines interactive helper functions |
| `docs/SPEC.md` | What the project must do |
| `docs/ARCHITECTURE.md` | How the repo is structured |
| `docs/RECOVERY_RUNBOOK.md` | Fresh-install/recovery execution guide |
| `docs/MANUAL_STEPS.md` | Manual setup still outside declarative config |
| `docs/DECISIONS.md` | Lightweight decision log |

## Separation Model

| Class | Belongs In Repo? | Examples |
| --- | --- | --- |
| Declarative system config | Yes | packages, services, users, shell defaults, desktop config |
| Hardware config | Yes, but carefully | filesystems, bootloader device, kernel modules |
| User state | No | browser profiles, editor state, synced folders |
| Secrets | No plaintext | SSH private keys, tokens, passwords |
| Disposable data | No | caches, build output, logs |

## Modularization Model

Start simple. Split only when it improves local reasoning.

Current module boundaries:

- `modules/default.nix` bundles shared modules; hosts import it as `../../modules`
- `modules/base.nix` for shared boot, networking, locale, users, and Nix settings
- `modules/desktop.nix` for GUI/session/display manager config
- `modules/codex.nix` for Codex-related system integration
- `hosts/<target>/` for host-local configuration and generated hardware config

Avoid further abstraction until repeated responsibility justifies it.

## Rebuild Model

Primary feedback loop:

```bash
phoenix-test
phoenix-switch
```

Use `test` for low-risk validation before committing to the boot profile. Use `switch` once behavior is acceptable.
Explicit flake targets, such as `sudo nixos-rebuild switch --flake .#vm`, are the fallback when helpers are not loaded.

## Recovery Model

Recovery means:

1. Install NixOS.
2. Restore/clone this repo.
3. Place hardware config appropriately, reviewing disk-specific values.
4. Run `nixos-rebuild`.
5. Restore user state and secrets from separate trusted sources.
6. Verify the system.
