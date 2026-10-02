# Project PhoeNix OS

Reproducible NixOS configuration for a personal workstation.

Project PhoeNix OS treats the workstation as code: reproducible, auditable,
rollbackable, and recoverable. It is a personal NixOS configuration built around
my workflow, hardware, recovery model, and interest in AI-assisted system
management. It is not intended to become a general-purpose NixOS distribution.

The repository is public because the system layer should be inspectable,
versioned, and useful as a reference. Private data does not belong here.
Secrets, SSH keys, Syncthing state, browser profiles, KeePass databases,
private notes, and user data are intentionally restored from separate trusted
sources.

## Goals

- Define the workstation through NixOS config instead of manual drift.
- Make rebuilds, experiments, rollback, and recovery routine.
- Make meaningful system changes visible as diffs and commits.
- Reduce long-term OS entropy from installers, GUI mutations, forgotten tweaks,
  and leftover system state.
- Keep system intent readable for future maintenance.
- Keep private state, secrets, app data, and caches out of the repo.
- Keep coding-agent changes reviewable: agents edit config and run checks;
  humans control activation, secrets, and publishing.

## Current Direction

The `vm` target is selected when running inside a virtual machine. The `metal`
target is the fallback for this bare-metal workstation.

The desktop direction is a polished Wayland workstation based on
Hyprland/Caelestia-style configuration, with KDE Plasma kept as an intentional
fallback and repair environment. The repository is still early-stage, so some
target-state documentation is ahead of the implemented modules.

NixOS is also useful below the operating-system layer. Project-specific
development shells and future container images should make tools explicit,
disposable, and reproducible instead of permanently installing every experiment
globally.

## Repository Layout

```text
phoenix-os-config/
  flake.nix
  hosts/
    vm/
      configuration.nix
      hardware-configuration.nix
      vm.nix
    metal/
      configuration.nix
      metal.nix
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

Host files are the entrypoints:

- `hosts/vm/configuration.nix` imports VM-specific config.
- `hosts/metal/configuration.nix` imports bare-metal-specific config.
- `modules/default.nix` bundles shared modules for host imports.
- `modules/` holds shared config used by more than one host.
- `hosts/*/*.nix` holds config that belongs only to that host type.

## Helper Commands

After applying the NixOS configuration and opening a new Bash terminal, the
shell module makes these functions available from any directory. It loads the
scripts from `repoDirectory` in `config/user.nix`; set `PHOENIX_REPO_ROOT` to
your checkout if it lives elsewhere.

- `phoenix-target` prints the selected target; `phoenix-target-info` explains
  how it was selected.
- `phoenix-switch`, `phoenix-test`, and `phoenix-boot` run the matching
  `nixos-rebuild` action with `sudo`.
- `phoenix-build` and `phoenix-dry-build` build without activating the system.
- `phoenix-rebuild <action>` is the underlying command dispatcher.
- `phoenix-test-caelestia-local` and `phoenix-switch-caelestia-local` use a
  local `../caelestia-nixos` input override for development.

Target selection uses `PHOENIX_TARGET` when set, detects a VM with
`systemd-detect-virt` otherwise, and falls back to `metal`. For example,
`PHOENIX_TARGET=metal phoenix-build` explicitly builds the metal configuration.

## Direct Rebuilds

Use explicit targets from the checkout when debugging or overriding automatic
target selection:

```sh
sudo nixos-rebuild switch --flake .#vm
sudo nixos-rebuild switch --flake .#metal
```

For routine work, use `phoenix-switch`; it detects the target and evaluates the
normal Git checkout flake. Use `phoenix-build` to build without activation.

## Hardware Configuration

`hosts/metal/hardware-configuration.nix` is the generated hardware snapshot for
the current Phoenix installation and is tracked with the flake. It contains
filesystem UUIDs and ordinary hardware details, not credentials or encryption
keys. On a reinstall or storage-layout change, regenerate it for that
installation, review the diff (especially `fileSystems`), and commit the
updated generated snapshot. Do not hand-maintain generated hardware settings.

For example, after installing or changing storage on the metal host:

```sh
sudo nixos-generate-config --show-hardware-config > \
  hosts/metal/hardware-configuration.nix
```

The host imports this file directly. Phoenix helpers use the Git flake rooted
at the repository, so the generated file is included through normal Git flake
evaluation.

## Mount Pollution

`nixos-generate-config` records filesystems that are mounted when it runs.
Temporary mounts can accidentally become permanent boot/system mounts.

Review generated `fileSystems` entries and remove things that should not be
managed by NixOS, for example:

- temporary USB sticks
- temporary bind mounts
- host-shared VM folders
- ad-hoc network mounts

VM shared folders should be configured explicitly in `hosts/vm/vm.nix`, not
accidentally carried in `hardware-configuration.nix`.

## When To Regenerate Hardware Config

Regenerate or review hardware config after real storage or boot changes:

- new root or boot partition
- new permanent internal disk or partition
- swap changes
- LUKS/encryption changes
- filesystem UUID or layout changes
- boot-relevant hardware changes

Usually do not add these to hardware config:

- temporary USB stick
- temporary bind mount
- host-shared VM folder
- ad-hoc network mount

## Workflow

1. Let the helpers detect `vm` or `metal`; set `PHOENIX_TARGET` only to override.
2. Put shared behavior in `modules/`.
3. Put host-only behavior in `hosts/vm/vm.nix` or `hosts/metal/metal.nix`.
4. Regenerate hardware config only for real hardware/storage changes.
5. Rebuild with `phoenix-switch`; use explicit `.#vm` / `.#metal` targets only
   for debugging or an override.

Agents may propose and edit configuration in this repo, but they should not
directly mutate the live system. Activation stays manual: review the diff, run
the relevant rebuild command, then use NixOS generations and Git history as the
rollback path.

## Recovery Model

The recovery target is simple first:

1. Boot or install a minimal NixOS environment.
2. Clone this public system configuration.
3. Apply the pinned flake target.
4. Restore private bootstrap material separately.
5. Rehydrate selected user data from Syncthing or another backup path.
6. Re-clone code repositories from Git remotes.
7. Verify the system and document any manual gaps.

A custom recovery image with preinstalled tools or cached packages may be useful
later, but it is not required for the first reliable recovery path.

## Notes

- Secrets need a dedicated encrypted secrets workflow before they belong here.
- Manual setup gaps should be documented in `docs/MANUAL_STEPS.md`.
- Keep changes small and rebuildable; split modules when a file becomes hard to
  reason about, not just for neatness.
