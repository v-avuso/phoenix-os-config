# Recovery Runbook

Use this after a broken system, fresh install, or disk replacement.

## 1. Install NixOS

- Boot NixOS installer.
- Partition and mount disks.
- Generate hardware config with `nixos-generate-config`.
- Confirm filesystems and bootloader target match the machine.

## 2. Restore This Repo

Clone or copy `phoenix-os-config` onto the machine.

Example:

```bash
git clone <repo-url> ~/phoenix-os-config
cd ~/phoenix-os-config
```

If Git is not available yet, copy the repo from external media.

## 3. Review Hardware Config

Compare generated hardware config with this repo’s `hardware-configuration.nix`.

Check carefully:

- filesystem UUIDs
- boot device
- encrypted disk setup, if any
- swap devices
- GPU/kernel modules

Do not blindly reuse stale hardware config on changed disks.

## 4. Apply Configuration

Copy or link the config into `/etc/nixos`, depending on the workflow in use.

Basic direct workflow:

```bash
sudo cp configuration.nix /etc/nixos/configuration.nix
sudo cp hardware-configuration.nix /etc/nixos/hardware-configuration.nix
sudo nixos-rebuild test
sudo nixos-rebuild switch
```

If `test` fails, fix the config before running `switch`.

## 5. Restore Secrets

Restore secrets only from trusted encrypted sources.

Examples:

- SSH private keys
- Git signing keys
- service tokens
- password manager access

Never paste secrets into committed Nix files.

## 6. Restore User State

Restore personal data and application state from the backup system chosen outside this repo.

Skip caches and build outputs.

## 7. Verify

Minimum checks:

- system boots
- network works
- user can log in
- expected desktop/shell works
- expected packages exist
- important services run
- Git/SSH work

Record any manual fixes in `docs/MANUAL_STEPS.md`.
