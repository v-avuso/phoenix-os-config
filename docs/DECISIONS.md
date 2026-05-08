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
