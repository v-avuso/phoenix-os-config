# Recovery Runbook

Use this after a broken system, fresh install, or disk replacement.

This runbook restores the public system layer. Private bootstrap material,
secrets, Syncthing state, and user data come from separate trusted sources.

## 1. Install NixOS

- Boot the NixOS installer or another minimal/recovery NixOS environment.
- Partition and mount disks.
- Generate hardware config with `nixos-generate-config`.
- Confirm filesystems and bootloader target match the machine.

## 2. Restore This Repo

Clone or copy `phoenix-os-config` onto the machine.

Example:

```bash
mkdir -p ~/repos/code
git clone <repo-url> ~/repos/code/phoenix-os-config
cd ~/repos/code/phoenix-os-config
```

If Git is not available yet, copy the repo from external media. The installed
helper commands expect this default path unless `PHOENIX_REPO_ROOT` is set to a
different checkout location.

## 3. Review Hardware Config

Compare generated hardware config with the target host file when one already
exists:

- `hosts/vm/hardware-configuration.nix`
- `hosts/metal/hardware-configuration.nix`

Check carefully:

- filesystem UUIDs
- boot device
- encrypted disk setup, if any
- swap devices
- GPU/kernel modules

Do not blindly reuse stale hardware config on changed disks.

## 4. Apply Configuration

Use the helper commands when available. They detect VM vs metal and pass an
explicit flake target to Nix.

During first recovery, source the helpers from the checkout or use explicit
flake targets. After the config has been applied and a new terminal is opened,
`modules/shell.nix` loads the helpers automatically.

```bash
source ./shell/phoenix-aliases.sh
phoenix-test
phoenix-switch
```

Explicit fallback:

```bash
sudo nixos-rebuild test --flake .#vm
sudo nixos-rebuild switch --flake .#vm
sudo nixos-rebuild test --flake .#metal
sudo nixos-rebuild switch --flake .#metal
```

If `test` fails, fix the config before running `switch`.

## 5. Restore Private Bootstrap Material

Restore secrets and bootstrap material only from trusted encrypted sources.

Examples:

- SSH private keys
- Git signing keys
- Syncthing device identity, if restored instead of re-paired
- service tokens
- password manager access

Never paste secrets into committed Nix files.

## 6. Restore User State

Restore personal data and application state from Syncthing or the backup system
chosen outside this repo.

Typical restore targets:

- selected files and user data
- safe application profiles
- private knowledge bases
- code repositories re-cloned from Git remotes

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
