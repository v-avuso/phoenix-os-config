# Decisions

## 2026-05-08 - NixOS Configuration Is The Project

- **Decision**: Project PhoeNix OS is a NixOS configuration repo.
- **Reason**: The repository exists to define and rebuild the NixOS system.
- **Consequence**: Windows bootstrap/recovery scaffolding does not belong here.

## 2026-05-08 - Use Explicit Flake Host Targets

- **Decision**: Use `hosts/vm` and `hosts/metal`, with shared config in `modules/`.
- **Reason**: VM and bare-metal installs need different hardware and host-local config.
- **Consequence**: Rebuild with explicit targets such as `.#vm` or `.#metal`; metal is the default target.

## 2026-05-08 - Secrets Stay Out Of Plaintext Repo

- **Decision**: Secrets are documented but not committed.
- **Reason**: Nix config repos are often copied, reviewed, and shared.
- **Consequence**: A dedicated encrypted secrets workflow is needed later.

## 2026-05-08 - Public Repo Excludes Private State

- **Decision**: This repo defines the public system layer only.
- **Reason**: User data, Syncthing identity, browser profiles, KeePass databases,
  private notes, and app state are not reproducible system config.
- **Consequence**: Recovery depends on separate trusted restore paths for private
  state.

## 2026-05-08 - Detect Host Target Outside The Flake

- **Decision**: Helper scripts detect `vm` vs `metal` before calling Nix with an explicit target.
- **Reason**: This keeps flake evaluation pure while avoiding per-machine tracked file edits.
- **Consequence**: Use `phoenix-switch`/`phoenix-test` for normal work; keep explicit `.#vm`/`.#metal` as fallback.

## 2026-05-14 - Use A Conventional Live Checkout Path For Helpers

- **Decision**: Interactive helper functions default `PHOENIX_REPO_ROOT` to
  `$HOME/repos/code/phoenix-os-config`, while allowing explicit override.
- **Reason**: Nix flake evaluation sees a `/nix/store` copy, not the mutable
  checkout path passed to `nixos-rebuild --flake`.
- **Consequence**: `phoenix-switch` works from any directory when the repo uses
  the conventional path. Machines with a different checkout location must set
  `PHOENIX_REPO_ROOT`.

## 2026-05-08 - Agents Do Not Activate The Live System

- **Decision**: Coding agents may edit this repo and run safe checks, but humans
  review diffs and activate NixOS changes.
- **Reason**: The live operating system, secrets, and publishing steps remain
  higher-trust operations.
- **Consequence**: Agent work should end with a clear diff, validation notes, and
  rebuild commands for manual use.

## 2026-05-08 - Plasma Is The Fallback Desktop

- **Decision**: Hyprland/Caelestia-style Wayland configuration is the primary
  desktop target; KDE Plasma remains the fallback and repair environment.
- **Reason**: The target workflow can evolve while preserving a comfortable GUI
  when compositor, shell, theme, or display configuration breaks.
- **Consequence**: Desktop docs must distinguish current implementation from
  intended target state until Hyprland/Caelestia modules exist.
