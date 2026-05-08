# Decisions

## 2026-05-08 - NixOS Configuration Is The Project

- **Decision**: Project PhoeNix OS is a NixOS configuration repo.
- **Reason**: The repository exists to define and rebuild the NixOS system.
- **Consequence**: Windows bootstrap/recovery scaffolding does not belong here.

## 2026-05-08 - Keep Current Layout Simple

- **Decision**: Start with `configuration.nix` and `hardware-configuration.nix`; modularize later when useful.
- **Reason**: Small config is easier to understand in one place.
- **Consequence**: Add modules only when responsibilities become hard to review.

## 2026-05-08 - Secrets Stay Out Of Plaintext Repo

- **Decision**: Secrets are documented but not committed.
- **Reason**: Nix config repos are often copied, reviewed, and shared.
- **Consequence**: A dedicated encrypted secrets workflow is needed later.
