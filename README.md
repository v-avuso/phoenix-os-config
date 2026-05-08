# Project PhoeNix OS

Reproducible NixOS configuration for a personal workstation.

Project PhoeNix OS keeps the operating system configuration declarative, version-controlled, and rebuildable. The repository is the source of truth for how the machine should be configured; the live machine is only a deployment target and feedback source.

## Mission

- Define the workstation through NixOS configuration instead of manual drift.
- Make rebuilds, experiments, and rollback routine.
- Keep system intent readable enough for future maintenance.
- Separate reproducible OS configuration from private state, secrets, and disposable data.
- Evolve toward a clean modular NixOS configuration over time.

## Philosophy

PhoeNix OS favors declarative configuration first:

- system packages, services, users, shells, fonts, networking, and desktop setup belong in NixOS config
- secrets should be handled through a dedicated encrypted secrets workflow, not plaintext repo files
- personal app data and caches are not NixOS configuration
- manual steps should be documented until they can be represented declaratively
- changes should be rebuildable, reviewable, and easy to roll back

## Current Architecture

```text
phoenix-os-config/
  README.md
  configuration.nix
  hardware-configuration.nix
  docs/
    SPEC.md
    ARCHITECTURE.md
    RECOVERY_RUNBOOK.md
    MANUAL_STEPS.md
    DECISIONS.md
```

The current repo starts from a standard NixOS configuration pair:

- `configuration.nix`: machine/system intent
- `hardware-configuration.nix`: generated hardware-specific config

Future growth should split configuration into focused Nix modules only when the current file becomes hard to reason about.

## Phases

### Phase 1 - Stabilize Current NixOS Config

- Document what the system must provide.
- Keep `configuration.nix` readable and rebuildable.
- Identify secrets and state that do not belong in the repo.
- Track manual setup that is not yet declarative.

### Phase 2 - Modularize Carefully

- Split Nix modules by responsibility when useful.
- Add home/user configuration if needed.
- Add machine profiles if more hosts appear.
- Add validation habits around `nixos-rebuild`.

### Phase 3 - Recovery Confidence

- Document fresh-install recovery.
- Keep a checklist for post-rebuild verification.
- Practice restoring from this repo on real or virtual hardware.

## Immediate Next Steps

1. Review `configuration.nix` and document current intent.
2. Decide whether to keep a single-file config for now or introduce modules.
3. Add manual setup gaps to `docs/MANUAL_STEPS.md`.
4. Run rebuild checks after each meaningful config change.
