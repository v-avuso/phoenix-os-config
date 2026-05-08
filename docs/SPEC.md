# Functional Specification

## Purpose

Project PhoeNix OS must provide a reproducible NixOS workstation configuration whose behavior is understandable from this repository.

## Goals

- Define the operating system through NixOS configuration.
- Keep system behavior version-controlled and reviewable.
- Support rebuild and rollback workflows.
- Distinguish declarative system config from user state, secrets, and caches.
- Document non-declarative setup until it is automated or intentionally kept manual.

## Non-Goals

- Treat the current live machine as unquestioned source of truth.
- Store secrets in plaintext.
- Back up every user file or application cache.
- Over-modularize before the config needs it.
- Support non-NixOS operating systems from this repository.

## Requirements

- `configuration.nix` remains rebuildable on the target machine.
- `hardware-configuration.nix` remains hardware-specific and generated/curated carefully.
- Secrets are referenced through a safe external/encrypted mechanism before automation is added.
- Manual steps are tracked in `docs/MANUAL_STEPS.md`.
- Recovery instructions are concrete enough to use after a fresh NixOS install.

## Invariants

- Repo == desired declarative system intent.
- Live machine == deployment target, not canonical truth.
- Hardware config changes require care.
- Secrets do not enter the repo unencrypted.
- Disposable caches/build output stay out of source control.
- Configuration changes should be small enough to review.

## Success Criteria

- A fresh NixOS install can be pointed at this repo and rebuilt into the intended system.
- Important services/packages/settings are represented declaratively.
- Manual gaps are explicit.
- Recovery steps are documented.
- `nixos-rebuild` succeeds after meaningful config changes.
