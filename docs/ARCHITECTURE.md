# Architecture

## Current Layout

```text
phoenix-os-config/
  configuration.nix
  hardware-configuration.nix
  README.md
  docs/
```

## File Responsibilities

| File | Purpose |
| --- | --- |
| `configuration.nix` | Main NixOS system configuration and desired machine behavior |
| `hardware-configuration.nix` | Hardware-specific generated config: filesystems, boot devices, detected hardware |
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

Good future module boundaries:

- `modules/system/` for boot, networking, locale, nix settings
- `modules/desktop/` for GUI/session/display manager config
- `modules/dev/` for developer tools
- `modules/services/` for enabled services
- `hosts/<hostname>/` if multiple machines appear

Avoid abstraction until more than one host or repeated responsibility justifies it.

## Rebuild Model

Primary feedback loop:

```bash
sudo nixos-rebuild test
sudo nixos-rebuild switch
```

Use `test` for low-risk validation before committing to the boot profile. Use `switch` once behavior is acceptable.

## Recovery Model

Recovery means:

1. Install NixOS.
2. Restore/clone this repo.
3. Place hardware config appropriately, reviewing disk-specific values.
4. Run `nixos-rebuild`.
5. Restore user state and secrets from separate trusted sources.
6. Verify the system.
