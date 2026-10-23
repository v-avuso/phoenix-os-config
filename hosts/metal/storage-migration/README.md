# feat(storage): migrate Phoenix to 4 TB SSD

## Intentions and boundary

Preserve the complete cold `/home/v` and essential private state on the already
installed 4 TB SSD. Leave the old SSD bootable and untouched by migration writes.
Do not clone partition tables, format, repartition, replace encryption or copy
the old ESP. `metal-4tb` selects the new hardware; `metal` and `default` retain
the old UUIDs. Both use hostname `phoenix` and password-capable PAM.

## QUICKSTART

Before shutdown, save the prepared **`phoenix-migrate`** file to a writable USB
volume. Close Firefox/Codex normally and shut down cleanly.

Boot a **NixOS live USB in UEFI mode**, connect network and AC power, open a
terminal in the folder containing that file, and run:

```sh
sudo bash phoenix-migrate
```

Enter the two new SSD unlock passwords. Read the checked plan and type `RESTORE`;
after the verified copy, type `INSTALL`. Wait for **SUCCESS**, then power off and
select the 4 TB SSD in firmware. Prefer disconnecting the old SSD while powered off.
Do not boot the target after **NO-GO**.

The launcher includes the entire reviewed source and runbook. No editor, clone,
Codex or ChatGPT is needed. Network is required for tools and normal Nix downloads;
“offline installation” means the target is not running. Saved networks/Bluetooth
are optional: append `--network --bluetooth` only if their migration is wanted.
The default plan preserves home, the v password and Navidrome.

**Readiness: GO to launch the guided preflight; execution still needs the two
operator confirmations. NO-GO for first Phoenix boot until the launcher reports
SUCCESS.** No migration or activation was performed during preparation.

The final firmware selection and first-boot acceptance require the operator.
Boot order is deliberately preserved, so the old SSD may otherwise boot again.

## Tool responsibilities

| Tool | Responsibility |
| --- | --- |
| `phoenix-migrate` (exported single file) | Bootstrap pinned tools, unlock/mount, mandatory native preflight, approval prompts, restoration, target-store Phoenix build/install and bootloader setup, final checks and cleanup. Never reboot, format or partition. |
| `migrate.py` | Source for the interactive orchestrator; accepts only the documented optional state flags. |
| `restore.py` | File restoration only, with native preflight, staging, progress and checksum verification. Does not install Phoenix. |
| `checks.py` | Read-only Syncthing/EFI/identity checks; never start services or repair databases. |
| `export-launcher.py` | Export HEAD's complete Git archive and commit identity into a portable launcher; excludes untracked/working-tree edits. |

After successful execution, the new SSD contains the complete old home, selected
service state, old v password and Phoenix `metal-4tb` boot closure. Fresh machine
ID, SSH keys and root password remain; hostname is phoenix. Syncthing and automatic
updates stay held. The old installation remains the rollback. Boot/login,
applications and cooling still need real-machine acceptance.

## Native evidence, 2026-10-23

Inspected `lsblk`, mount information, Btrfs identity/root-ID ioctls, kernel
device-mapper sysfs and raw EFI variables. Names below are observations;
execution uses serial-qualified by-id paths and UUIDs.

| Device | Observed identity/layout |
| --- | --- |
| Old Samsung 970 EVO Plus 1TB | Serial `S4EWNG0M109916K`; 1,000,204,886,016 bytes; initially nvme1n1, observed as nvme2n1 after the USB attempt |
| Old ESP p1 | FAT32 `7618-BF96`; PARTUUID `5949426d-e7fe-458d-9d04-e26f062da171` |
| Old root p2 | Unencrypted Btrfs `e9d1b391-3f86-4254-9970-aa47df230474`; `/` ID 5, `home` ID 256, `nix` ID 257 |
| Old swap p3 | Unencrypted swap `51f0275d-56fd-486c-93cb-9cdd6ebcc5eb`; 71,311,671,296 bytes; active, zero used at inspection |
| New Samsung 990 PRO with Heatsink 4TB | Serial `S7DSNJ0Y411212Z`; 4,000,787,030,016 bytes; currently nvme0n1 |
| New ESP p1 | 1 GiB FAT32 `B4E3-63E5`; PARTUUID `d1a46384-039f-42f2-9ccd-13ec17dd2250` |
| New root p2 | 3,928,399,486,976 bytes; LUKS UUID `d9756988-1532-4903-b6d9-6e89735248f7`; PARTUUID `2e71962c-9167-4224-a4cd-41aeb445ec8b` |
| New decrypted root | Btrfs `b1756a78-0da5-47a3-a73c-38112d1ac945`; mounted top-level ID 5 at `/run/media/v/root`; root-ID ioctls confirm `home` 256 and `nix` 257 |
| New swap p3 | 71,311,667,200 bytes; LUKS UUID `8c5388a9-cb79-4c29-8de1-65cf542437e1`; PARTUUID `9828605f-2fec-4ee3-adeb-34cca577b07b` |
| Separate 2TB Windows/NTFS SSD | Serial `S4J4NZ0R303233H`; outside this migration |

Kernel dm-0/dm-1 report **LUKS2**, backed by new p2/p3 respectively. Mounted
Btrfs supplies the inner root UUID. Raw devices and privileged Btrfs enumeration
are unavailable in this agent sandbox; the installed broker has no storage
diagnostic. **Pending:** direct signature/header reads, inner swap type/UUID,
Btrfs default/enumeration and ESP loader files. The live-USB script requires
all these checks, including actual EFI executables/kernel/initrd files and an
active firmware entry for the new ESP and loader, before restoration.
Generated inventory is not a substitute.

The fresh installation's regular `/etc/nixos/{hardware-configuration,
configuration}.nix` files declare the new encrypted root/home/nix, new ESP and
separate encrypted swap unlock. Its boot settings are systemd-boot, writable EFI
variables, hostname `nixos`, stateVersion `26.05`, v UID/GID `1000:100`.
Reading its own store-backed fstab confirms the new device paths. Beware offline
absolute symlinks: `cat /run/media/v/root/etc/fstab` follows `/etc/static` into
the running host. Resolve every absolute link inside the mounted target instead.

Raw firmware entries: Boot0001/0005 reference the old ESP, Boot0004/0007 the new
ESP. BootCurrent is 0001; BootOrder is 0001,0005,0004,0007,0002,0000. Recheck GUIDs
at execution; entry numbers are mutable. The new target disables EFI-variable
updates, retaining order while allowing installation onto its own mounted ESP.

### Serial preflight compatibility

The first USB log (`/home/v/log-phoenix-migrate.txt`, bundle `fc88829`) stops at
the initial serial gate, before unlocking or restoration. It does not record the
returned serial, so the precise presentation used in that session is unknown.
Both actual NVMe serial fields contain five trailing spaces. The exact USB
`lsblk` 2.42.3 binary reproduces a false mismatch when using its native sysfs
fallback: `--raw` renders those spaces as literal `\x20`, which Python `.strip()`
does not remove. The [upstream implementation](https://github.com/util-linux/util-linux/blob/v2.42.3/misc-utils/lsblk.c#L1021-L1028)
selects udev properties or the sysfs field, so its display is not an identity API.

Both preflight gates now follow the by-id link with `stat`, require a block device,
and read `/sys/dev/block/MAJOR:MINOR/device/serial`. Only trailing ASCII spaces and
newlines are removed; the entire remaining serial must match exactly. Missing
identity, wrong serial, extra characters and regular-file aliases still stop.
Mismatch errors include the alias, expected/observed serial and native field path.
Actual source/destination serials and capacities pass this check; observed outer
partition UUIDs/types still match. New encrypted filesystems remain locked and raw
signature reads require root, so complete native layout checks remain mandatory
on USB. No identity constants, approvals or write boundaries were relaxed.

## Restoration strategy and state selection

Use offline `rsync -aHAXS --numeric-ids` into a staging directory on the new home
subvolume. Include **all** dotfiles, caches, repositories/worktrees, rootless
containers, `.mozilla`, `.codex`, `.config/Codex`, sandbox profiles, keyrings,
`.config/Yubico/u2f_keys`, GNOME Keyring under `.local/share/keyrings`, Syncthing
state and personal data; no exclusions.
Both accounts are `1000:100`; subordinate ranges must be `v:100000:65536`.
The existing YubiKey mapping is owner v, mode 0600. Keeping `phoenix` preserves
its default `pam://phoenix` origin. No re-enrollment is proposed. Login/YubiKey
authentication is separate from the two new LUKS passphrases.

Checksum/metadata dry-run verification detects changed/missing/extra files before
publication. The fresh home is retained as `.phoenix-fresh-v-before-migration`.
Rsync preserves content, IDs, modes, ACLs, xattrs, hard links, symlinks and sparse
allocation. Reflink sharing, nested Btrfs subvolume/snapshot structure, birth/ctime
and running processes/RAM are not preserved. Capacity must exceed apparent home
bytes plus 20 GiB. Any copy/verification error stops execution.

Block cloning would replace fresh encryption/layout and duplicate identities.
Btrfs send needs a suitable read-only snapshot; creating one would write the old
SSD. Selective profile exports omit private state. Rsync already owns copy and
comparison semantics; custom code only binds safety checks and publication.
Sources: [rsync](https://download.samba.org/pub/rsync/rsync.1),
[Btrfs mount rules](https://btrfs.readthedocs.io/en/latest/btrfs-man5.html),
[NixOS installation](https://nixos.org/manual/nixos/stable/).

| Outside-home state | Treatment |
| --- | --- |
| v entry in `/etc/shadow` | Essential password fallback: replace only this entry; never print the hash. Keep fresh root/service entries and back up the target shadow. Locked/empty source password stops restoration. |
| `/var/lib/navidrome` | Essential local accounts/library database, including cold WAL/SHM. Preserve any fresh state separately. Music itself is in home. Reassign to the installed service UID/GID after installation. |
| `/etc/NetworkManager/system-connections` | Optional `--network`: saved connection credentials. Review any referenced certificates/keys outside home separately. |
| `/var/lib/bluetooth` | Optional `--bluetooth`: same-controller pairings. |
| `/etc/subuid`, `/etc/subgid` | Validate matching ranges; refuse account-map merging. |
| Machine ID, random seed, root password, SSH host keys | Retain fresh identity/recovery password. No SSH daemon is enabled; revisit keys only if external clients actually require continuity. |
| CoolerControl configuration/runtime state | Reconstruct via the existing hardware-aware reconciler and firmware fallback; no blanket copy. |
| `/var/lib/nixos`, deployment/review/updater checkpoints | Regenerate. Do not transfer old trusted activation authority. |
| `/nix/store`, Nix database, boot generations | Install the pinned flake; old generations remain on the old SSD. |
| Logs, ClamAV signatures, caches outside home | Regenerate; not essential private state. |

Home links into `/nix/store` remain symlinks. Install the pinned system/Home
Manager closure before login so managed links are regenerated. Historical user
Nix profiles/ad-hoc store paths/container references may need rebuilding; exact
continuation of every historical Nix environment would require a separate approved
closure-transfer plan. Native browser/Codex files remain intact, but device-bound
credentials can require sign-in. Cold keyrings plus the old v password preserve
the existing unlock mechanism; runtime acceptance is still needed.

## Targeting and accepted decisions

The currently installed `phoenix-target --info` reports `metal`; the installed
`phoenix-switch --print` selects `#metal`, and the installed `phoenix-update`
runner JSON also selects `metal`. These are correct for the running old SSD.
The existing installed selector cannot yet select `metal-4tb`.

The prepared configuration declares `phoenix.target = "metal-4tb"`. A small
shared packaged selector identifies the actual root by stable filesystem UUID:
old root → `metal`, new root → `metal-4tb`. VM fallback requires detected
virtualization. Unknown physical roots, conflicting `PHOENIX_TARGET` values and
stale installed targets fail closed. Explicit selection is a confirmation, not
a way to override a mismatching root. Direct Nix commands still need an explicit
output; the installer is hard-bound to `#metal-4tb`.

Human switch/boot wrappers, automatic updater and agent deployment all use this
check. The protected controller checks before source work and again before
profile/activation mutation. Its installed policy must agree with the root.
The old metal and VM outputs retain their storage identities.

Accepted: complete home/keyrings/Firefox/Codex/YubiKey; selective service state;
fresh machine ID and SSH host keys; old metal for rollback. Both restoration and
final installation verify fresh identity. Syncthing state resides inside home;
Navidrome is the essential outside-home database. Saved networks/Bluetooth remain
optional flags. Know both new LUKS passphrases and the old login password without
posting them. Launching preflight alone does not approve restoration/installation.

## Nix package reuse decision

Nix 2.34.9 supports separate local stores with the same logical `/nix/store`,
`local?root=/mnt/phoenix-old&read-only=true`, and `nix copy --from ... --to
/mnt/phoenix-new PATH`. This imports store objects and adds their validity records
through Nix; it need not replace the destination database or select a system
profile. Never rsync `/nix/var/nix`, overwrite the fresh database, or use
`--profile`/activation as a reuse operation. Locally built unsigned closures may
also require explicit source trust/signature treatment.

**Use normal downloads for this migration.** No store-copy optimization is enabled.
The source is currently live; a cold read-only database/WAL and the live USB's
compatible Nix version have not been demonstrated. Read-only mode uses SQLite's
immutable access and is safe only when all writers are excluded. Adding that
version/WAL/trust/import trial is unnecessary for the primary restore milestone.
This is a bounded choice, not a claim that store-to-store copying is unsupported.
If downloads become a blocker, reassess with a disposable import trial proving
that the fresh database's existing records/profile remain intact.
Sources: [local store](https://nix.dev/manual/nix/2.34/store/types/local-store.html),
[nix copy](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-copy.html).

## Syncthing safety before any synchronization

Native configuration inspection confirms the six declared IDs/paths/markers.
The actual v2 main index maps those same IDs to six `folder.*.db` files.
Preflight requires the certificate/private-key pair to match, exact declared
folder paths and real `.stfolder` markers, matching main-index folder IDs,
existing mapped indexes, and read-only SQLite `quick_check` for every database.
It runs cold, includes WAL/SHM in the full home copy, and repeats the check on
staging before checksum verification/publication. Never create an empty marker,
reset the index or regenerate a certificate to get past a failure.

Both `syncthing.service` and `syncthing-init.service` require the root-owned
`/var/lib/phoenix-migration/syncthing-accepted` marker on the new target. It must
remain absent through installation/first boot. This prevents Nix's configuration
updater from starting synchronization indirectly. The source must be shut down;
never run two copies of the same device identity.

After first-boot data acceptance, with both units still stopped, run the read-only
check again (use the restored migration directory, with Python/OpenSSL available):

```sh
python3 checks.py --home /home/v
```

Compare the certificate fingerprint with pre-migration local output, inspect all
six real folders and their expected content, and retain their exact folder IDs.
The offline check verifies identity/index/layout and copy fidelity; it is not a
full Syncthing rescan or proof that peers were up to date. After explicit sync
approval, create the root-owned marker and start both units. Observe the first
scan/peer status; stop on unexpected missing data or mass deletions. See
[Syncthing state](https://docs.syncthing.net/users/config.html) and
[marker safety](https://docs.syncthing.net/users/faq.html#i-am-seeing-the-error-message-folder-marker-missing-what-do-i-do).

## Execution details and failure recovery

The QUICKSTART is the normal execution procedure. The launcher checks real root,
UEFI/live-USB identity, no active swap, exact disk serials/sizes/signatures, no
existing mounts/mappings and empty ordinary mountpoints. It sets the old SSD and
all partitions kernel read-only **before** mounting it `ro,rescue=nologreplay`. It opens
only the two new LUKS mappings (swap read-only), mounts the new root/ESP read-only,
then runs the complete `restore.py` preflight. The source validator requires both
`ro` and `rescue=nologreplay` in the native mount options. This uses the supported
[Btrfs rescue syntax](https://btrfs.readthedocs.io/en/latest/btrfs-man5.html#mount-options)
to suppress log replay; the USB kernel rejects the former standalone spelling.
That preflight checks native Btrfs UUIDs,
root/default/subvolume IDs, LUKS2 headers/backing devices, actual swap signature,
ESP GUID/loader images/active firmware entries, account/subordinate IDs, usable
source password, YubiKey/keyring/Syncthing state and available capacity.

Any mismatch stops. Do not format, repair, recreate markers or remove guards to
force a pass. If the live desktop has automounted either installation, unmount it
through the desktop and retry; if it activated swap, disable swap before retrying.
Those unexpected conditions need operator intervention because guessing which
external mounts/mappings to close would weaken the safety boundary.

Only `RESTORE` allows the target root to be remounted read-write and invokes the
original restoration checks again. Rsync reports progress; checksum/metadata
verification performs a second full read and may take a long time. Fresh home is
retained as `.phoenix-fresh-v-before-migration`; private target state is backed up
under `/root/phoenix-migration-before`. An interrupted copy/publication deliberately
blocks automatic restart for recovery review. Preserve both hidden home directories;
a power loss between renames can leave `/home/v` absent. Never boot then.

Only the later `INSTALL` confirmation permits mounting new home/nix/ESP and
running `nixos-install --root /mnt/phoenix-new --flake <bundled-source>#metal-4tb
--no-root-passwd --no-channel-copy --no-write-lock-file`. The bundled committed
archive is staged in a disposable RAM Git repository for flake visibility; neither
the source checkout nor the restored checkout is edited. The pinned native
installer builds in the **destination Nix store**, retains its existing database,
sets its system profile and activates the target offline to install boot files.
It can reassert managed Home Manager settings; see
[state ownership](../../../docs/CONFIGURATION_STATE.md). Home Manager collisions
are failures requiring path-specific review, never blanket deletion.
Phoenix retains `system.stateVersion = "25.11"` for restored state.

Final verification checks hostname, usable v password, Navidrome ownership,
installed system profile and its default boot entry, encrypted-root/ESP fstab entries, both Syncthing holds,
absence of the update timer, unchanged fresh identities and firmware boot
entries/order, Syncthing consistency and actual ESP loader/kernel/initrd files.
It flushes writes, unmounts only mounts it created and closes only mappings it
opened. A cleanup failure is NO-GO. No automatic reboot or live-system activation
occurs. Temporary old-disk read-only flags remain until reboot.

On failure, keep the printed phase/error and extracted runbook under
`/run/phoenix-migration.*/source/hosts/metal/storage-migration/README.md`. Do not boot
the target. The script tries cleanup; if a mount remains busy, stop and review it
in the live USB. Do not remove backups, rerun individual writes or format as a
retry. The old SSD remains bootable. Follow rollback below, or request a reviewed
recovery action for the specific failed phase. A declined installation leaves
restored files but the fresh boot closure: do not log into that fresh desktop.

## Exporting the portable launcher (preparation machine)

After committing and validating the intended migration sources:

```sh
python3 -B hosts/metal/storage-migration/export-launcher.py result-migration/phoenix-migrate
```

The exporter prints the reviewed commit and file SHA256. Copy that single file to
a writable USB volume. The launcher automatically checks its embedded payload.
It embeds the full Git
archive, release identity and a checked compressed payload; runtime tooling comes
from the exact locked nixpkgs revision. The generated file is ignored by Git.
The original installed helpers remain unchanged until the offline installation.

## Runtime acceptance and rollback

Check mounts/UUIDs with `findmnt` and `lsblk -f`, hostname phoenix, both encrypted
unlocks and swap activity. Do not assume one unlock prompt or working hibernation;
no resume-device guarantee is added. Verify cooling/fallback per
[fan guidance](../../../docs/FAN_CONTROL.md). Test login/sudo/lock by password with
the key absent, then with YubiKey. Check Firefox session tabs/history/logins, Codex
chats/resume/projects/worktrees and Native/Sandboxed launches, keyrings, rootless
environments, Syncthing identity, Navidrome accounts/playlists and selected pairings.
Do not delete backups or enable the updater before acceptance. Confirm
`phoenix-target --info` reports the new root UUID and `metal-4tb`;
`PHOENIX_TARGET=metal-4tb` may be used as an additional confirmation.
The restored Syncthing units remain
held until their root marker is deliberately created after the checks above.

After acceptance and separate commit/activation authorization, remove the new
host's forced `services.phoenixUpdates.enable = false` override. Commit that small
enablement change to the configured source branch (`main`), then install that
exact source with `PHOENIX_TARGET=metal-4tb phoenix-switch`. Confirm the installed
activated-source/system-profile baseline matches the committed source. The updater
and protected policy then both select `metal-4tb`; `phoenix-update` and its timer
can stage normal updates without changing the old `metal` configuration. Do not
manually copy old deployment approvals/checkpoints or edit protected baselines.

Rollback: cleanly shut down, reconnect/select old serial `S4EWNG0M109916K` in
firmware, and boot its existing entry/generation. Volatile read-only flags clear
at reboot. Its hardware target and EFI were preserved; do not activate `metal-4tb`
on it. The old checkout retains the committed preparation; its installed generation
is unchanged. New post-migration writes exist only on the new SSD: do not reverse-sync entire homes/databases or
run two Syncthing instances with the same identity. Retain both SSDs until accepted.

If installation fails, keep target backups under root's `phoenix-migration-before`
and hidden home directories; repair from USB or boot old. Never format/repartition
as a retry. Generation rollback does not undo copied state or Home Manager writes.

## Preparation checks and evidence limits

Run the disposable suites with Python 3, OpenSSL, rsync and ACL tools available:

```sh
python3 -B hosts/metal/storage-migration/test_restore.py
python3 -B hosts/metal/storage-migration/test_migrate.py
python3 commands/tests/commands.py
nix eval --impure --file modules/tests/target.nix
nix build --impure --file commands/tests/commands-packaging.nix --no-link
nix flake check --no-build --no-write-lock-file .
```

Restore fixtures exercise real checksum/metadata, hard-link/xattr/ACL/sparse copies,
password replacement, symlink/mount guards and throwaway Syncthing/EFI state.
Driver fixtures cover both approvals, stop-on-failure sequencing, cleanup ownership,
target-only commands and a self-contained exported Git snapshot. Packaging tests
compile the actual selector/dispatcher; controller/updater fixtures test root
mismatches before source/profile mutation. Target evaluation checks old/new/VM
policy agreement, storage declarations, both sync guards and eventual update
enablement. These checks never migrate data or activate the host.

Actual privileged native preflight, whole Phoenix system build/installation,
LUKS boot, password/YubiKey, cooling and desktop/application acceptance are still
operator checks. No fixture establishes a completed migration or bootability.
No format, restoration, deployment or activation was run during preparation;
flake.lock and the old hardware snapshot remain unchanged.
