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

The VM target is the current working host. The metal target is the intended
default target for a future desktop install.

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

The repo includes small shell helpers so rebuilds can use the right host target
without editing tracked files.

The NixOS config installs the Bash shell functions through `modules/shell.nix`.
After applying the config and opening a new terminal, these commands should be
available from any directory:

```sh
phoenix-target-info
phoenix-test
phoenix-switch
phoenix-boot
phoenix-build
phoenix-dry-build
phoenix-test-caelestia-local
phoenix-switch-caelestia-local
```

The shell integration points at the live checkout so helper updates take effect
without rebuilding the helper scripts into `/nix/store`. The default checkout
path is defined as `repoDirectory` in `config/user.nix`; forks and machines with
different local paths should change it there.

For a temporary override, set `PHOENIX_REPO_ROOT` before starting the shell, for
example in `~/.bashrc` or another user profile file:

```sh
export PHOENIX_REPO_ROOT=/path/to/phoenix-os-config
```

Target selection:

- `PHOENIX_TARGET=vm` or `PHOENIX_TARGET=metal` wins when set.
- otherwise, `systemd-detect-virt --vm` selects `vm` inside a VM.
- otherwise, the fallback target is `metal`.

Temporary override examples:

```sh
PHOENIX_TARGET=vm phoenix-switch
PHOENIX_TARGET=metal phoenix-switch
```

The helpers select a target, prepare its local hardware config if needed, then
pass the checkout as a `path:` flake. This includes ignored host hardware files
without adding them to Git's index.

## Direct Rebuilds

Direct commands still work and are useful when debugging:

```sh
# Run from the checkout root; choose the explicit target to inspect.
sudo nixos-rebuild switch --flake path:.#vm
sudo nixos-rebuild switch --flake path:.#metal
```

`#vm` and `#metal` select different NixOS configurations from `flake.nix`.
These direct commands are useful for debugging when the selected host already
has its local hardware file. Use `phoenix-switch` or another Phoenix helper for
normal rebuilds; it checks or bootstraps that file first. Plain
`nixos-rebuild --flake .` can be surprising because NixOS may select a
configuration by hostname.

## Hardware Configuration

Each host needs its own local `hardware-configuration.nix`. Both files are
ignored by Git because they contain machine-specific hardware and filesystem
identifiers; do not commit them. On a normal NixOS install, the rebuild helper
copies `/etc/nixos/hardware-configuration.nix` to the selected host directory
the first time it is needed. It never replaces an existing host file.

If that bootstrap source is unavailable, generate a file for the selected host:

```sh
target=vm # Set to metal for the bare-metal host.
sudo nixos-generate-config --show-hardware-config > "hosts/$target/hardware-configuration.nix"
```

Treat this file as host-local hardware and storage config:

- generated per machine by `nixos-generate-config`
- usually changed only when storage or boot-relevant hardware changes
- not meant for casual manual editing
- review the `fileSystems` section before relying on it in a rebuild

The Phoenix helpers evaluate the checkout through a `path:` flake reference so
these ignored files are included without Git index workarounds. The host
configuration imports the file unconditionally, so a missing file produces a
clear evaluation error instead of silently omitting hardware settings.

This file can expose machine-identifying details such as filesystem UUIDs,
partition layout, and hardware hints, so keep it local to its machine.

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

1. Pick the target: `vm` for the current VM, `metal` for the future desktop.
2. Put shared behavior in `modules/`.
3. Put host-only behavior in `hosts/vm/vm.nix` or `hosts/metal/metal.nix`.
4. Regenerate hardware config only for real hardware/storage changes.
5. Rebuild with `phoenix-switch` or another Phoenix helper; use explicit
   `path:.#vm` / `path:.#metal` targets for debugging.

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
