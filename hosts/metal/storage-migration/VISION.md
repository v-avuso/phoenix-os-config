# Optional storage-migration improvements

## Intentions

Reduce operator work and catch runtime failures before touching physical disks.
Keep the source intact, destination identity explicit, failure handling safe and
the implementation small. This is a backlog, not an approved implementation plan.
The completed Phoenix migration does not require these changes.

- **One reviewed authorization:** Present the exact source, destination, retained
  identities and writes once. After authorization and necessary LUKS authentication,
  run unattended within that plan; stop on a changed identity or unexplained state.
  Investigate supported ways to bind authorization to the complete execution.
- **Readable progress:** Show the current phase, meaningful byte/file progress,
  verification status and a clear outcome. Keep detailed errors and command output
  in a durable separate log, including failures before home restoration begins.
- **Dedicated migration image:** Evaluate a pinned bootable NixOS image with
  graphical drive selection, LUKS unlocking and automated execution. Compare its
  maintenance cost with the existing portable launcher before adopting it.
- **Configurable profiles:** Describe source/target layouts and state policy as
  reviewed migration profiles. Discover native identities and subvolumes, then
  validate them against the selected profile. Avoid a general framework until a
  second real layout demonstrates the need.
- **Realistic integration tests:** Use disposable NixOS VMs with separate source,
  encrypted destination and excluded backup disks. Exercise actual mount options,
  fixed-width device identities, SQLite WAL/SHM, online seeding, cold completion,
  Nix import, EFI installation, reboot and failure recovery. Unit fixtures remain
  useful but cannot establish this workflow.
- **Upstream mechanisms first:** Prefer NixOS installation, supported Nix stores,
  rsync, cryptsetup, Btrfs and systemd interfaces. Keep project code responsible for
  plan validation, state selection and sequencing. Preserve simple recovery paths;
  avoid carrying private copies of upstream storage/install mechanisms.
- **Extremely low priority — CoolerControl UI password:** Identify the narrow
  persistent password state if a future migration should retain it. The migrated
  application worked after setting a new control password; no change is needed now.
- **Only if it recurs — authorization:** One suspend request was rejected before
  the first local `phoenix-switch`. Preserve that observation without expanding
  the authorization surface or investigating an isolated, nonblocking failure.

Any future work needs its own acceptance limits, representative end-to-end trial,
cost budget and operator authorization. Never experiment on the retained old SSD.
