# Functional Specification

## Purpose

Project PhoeNix OS must provide a reproducible personal NixOS workstation
configuration whose behavior is understandable from this repository.

The project defines the public system layer. Private user state, credentials,
Syncthing identity, password stores, browser profiles, private notes, and other
personal data are restored separately.

## Goals

- Define the operating system through NixOS configuration.
- Keep system behavior version-controlled and reviewable.
- Support rebuild and rollback workflows.
- Support recovery onto replacement or freshly installed machines.
- Reduce long-term OS drift by making packages, services, and system choices
  explicit.
- Keep controlled experimentation possible through reversible, pinned config
  changes.
- Keep the repo friendly to coding agents while keeping activation under human
  control.
- Distinguish declarative system config from user state, secrets, and caches.
- Document non-declarative setup until it is automated or intentionally kept manual.

## Non-Goals

- Treat the current live machine as unquestioned source of truth.
- Store secrets in plaintext.
- Back up every user file or application cache.
- Store Syncthing state, SSH keys, browser profiles, KeePass databases, private
  notes, or other private user data.
- Let agents directly activate live system changes.
- Over-modularize before the config needs it.
- Provide a custom recovery image as an initial milestone.
- Support non-NixOS operating systems from this repository.

## Requirements

- Host entrypoints under `hosts/` remain rebuildable on the target machine.
- Each host imports its machine-local `hardware-configuration.nix` unconditionally; those files stay ignored by Git.
- Rebuild helpers bootstrap a missing host file from `/etc/nixos/hardware-configuration.nix` without overwriting an existing file.
- Rebuild helpers evaluate the local checkout as a `path:` flake so ignored hardware files are included.
- Helper scripts select `vm` or `metal` without requiring tracked file edits.
- Secrets are referenced through a safe external/encrypted mechanism before automation is added.
- Private bootstrap material and user data have documented restore paths outside
  this repo.
- Manual steps are tracked in `docs/MANUAL_STEPS.md`.
- Recovery instructions are concrete enough to use after a fresh NixOS install.

## Invariants

- Repo == desired declarative system intent.
- Live machine == deployment target, not canonical truth.
- Hardware config changes require care.
- Secrets do not enter the repo unencrypted.
- Agents may edit config and run safe checks, but humans review and activate
  system changes.
- Disposable caches/build output stay out of source control.
- Configuration changes should be small enough to review.

## Success Criteria

- A fresh NixOS install can be pointed at this repo and rebuilt into the intended system.
- Important services/packages/settings are represented declaratively.
- Manual gaps are explicit.
- Recovery steps are documented.
- `nixos-rebuild` succeeds after meaningful config changes.
