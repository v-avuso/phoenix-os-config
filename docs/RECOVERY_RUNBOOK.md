# Recovery runbook

This restores the system configuration. Private keys, credentials, Syncthing
identity, application databases, and personal files require separate trusted
restore sources. The repository is not their backup.

## Recover an existing installation first

- At boot, choose a known-good NixOS generation if a newer one fails to boot or
  log in. Metal uses Hyprland only; use a working boot generation or TTY for
  repair. VM retains Plasma/X11.
- From a working session or TTY, inspect the relevant service journal and Git
  diff, correct the configuration, then build before authorizing activation.
- An older system generation does not undo arbitrary application writes,
  firmware changes, or private-state loss. Restore damaged data from backups.

## Fresh installation or disk replacement

1. Boot the NixOS installer, partition and mount the intended disks under
   `/mnt`, and generate the installation configuration. Review the disk layout
   before any destructive operation.
2. Clone or copy this repository to the path configured as `repoDirectory` in
   `config/user.nix`, or update that setting for the new machine. Review user
   identity, host-specific assumptions, and the selected `metal` or `vm` target.
3. Copy the newly generated hardware snapshot into
   `hosts/<target>/hardware-configuration.nix`. For an installer mounting the
   target at `/mnt`, the source is normally
   `/mnt/etc/nixos/hardware-configuration.nix`; for a running installation,
   generate a fresh snapshot with `nixos-generate-config --show-hardware-config`.
4. Review filesystem UUIDs, boot devices, encryption, swap, and kernel modules.
   Remove temporary mounts. These files are **tracked**, not ignored; include
   new files in the Git index so Git-flake evaluation sees them, then commit the
   reviewed snapshot. Helpers do not copy or generate hardware files.
5. Build/install the explicit target. From the mounted installer environment:

   ```sh
   sudo nixos-install --root /mnt --flake /path/to/phoenix-os-config#metal
   ```

   Substitute the actual checkout path and target. The VM placeholder must be
   replaced before using `#vm`; evaluation alone does not make it bootable.
6. Reboot into the installation. Once helper commands are available, use
   `phoenix-build` for builds and authorized `phoenix-test`/`phoenix-switch` for
   live activation. Until then, an explicit rebuild from the checkout is:

   ```sh
   nixos-rebuild build --flake .#metal
   sudo nixos-rebuild test --flake .#metal
   sudo nixos-rebuild switch --flake .#metal
   ```

   These sudo examples are for a human-operated terminal. Agents must follow
   the graphical authentication flow in [AGENTS.md](../AGENTS.md).

`test` activates immediately without changing the next-boot generation;
`switch` activates immediately and updates it. Neither is a harmless check.
Do not activate after a failed build or against stale disk identifiers.

## Restore private material and user state

- Restore SSH/Git signing keys, service tokens, and password-manager access
  from trusted encrypted sources; never put their contents in Git or chat.
- Restore or re-pair Syncthing identity, then restore selected files and
  application profiles. Syncthing synchronization is not an independent backup
  against deletion or corruption.
- Re-clone code repositories; sign into accounts as needed. Skip disposable
  caches/build outputs. Review restored files that conflict with managed config.
- Enroll YubiKey fingerprints and create the local PAM mapping using the
  [YubiKey guide](YUBIKEY_PAM.md). Keep password fallback usable.

## Verify before calling recovery complete

- Boot and log in; check network, displays, desktop logout, and password fallback.
- Check important services and ClamAV database/scanner readiness; configured
  scanning does not guarantee signatures were downloaded successfully.
- Verify firmware fan fallback and cooling using [fan control](FAN_CONTROL.md).
- Verify Git/SSH, restored data, and synchronization without exposing secrets.

Keep any newly discovered, actionable manual recovery gap here. Broader backup,
secrets automation, and recovery-image proposals belong in
[the vision](VISION.md) or the task backlog until implemented.
