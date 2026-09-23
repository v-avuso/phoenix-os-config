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

## 2026-05-14 - Configure The Live Checkout Path In User Config

- **Decision**: `config/user.nix` owns the local checkout path as
  `repoDirectory`; interactive helper functions use it as the default
  `PHOENIX_REPO_ROOT`, while allowing explicit override.
- **Reason**: Nix flake evaluation sees a `/nix/store` copy, not the mutable
  checkout path passed to `nixos-rebuild --flake`. Keeping the path in one user
  config file makes forks and per-machine path changes explicit.
- **Consequence**: `phoenix-switch` works from any directory when the repo uses
  the configured path. Machines with a different checkout location should update
  `config/user.nix`; temporary sessions can set `PHOENIX_REPO_ROOT`.

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

## 2026-09-23 - OpenSnitch Learns Before Enforcing

- **Decision**: Keep OpenSnitch in default-allow learning mode for roughly one
  month, with connection prompts disabled and structured connection events sent
  to the local system log.
- **Reason**: During the Windows-to-NixOS migration, first observe normal
  application traffic without interrupting work or breaking connectivity.
- **Consequence**: Preserve the declarative allowlist as a future baseline.
  After the learning period, review the collected data with Codex, group normal
  traffic by application/process and destination, then generate and refine
  allow rules. Consider default-deny only after reviewing the resulting rules
  and confirming essential workflows. OpenSnitch event data includes useful
  process and network attribution: executable/process arguments, destination
  hostname when available, destination IP, port, protocol, and a record for
  each observed event. Timestamps use UTC with microsecond precision, allowing
  connection frequency to be derived from repeated records. Events are sent
  through the local syslog logger to journald, whose existing retention is
  capped at 30 days and 1 GB, so high event volume can shorten the available
  history. Review/export the local journal before its retention window expires,
  for example with `journalctl -t opensnitchd --since '30 days ago' -o cat`.
