# feat(storage): migrate Phoenix to 4 TB SSD

## Intentions and boundary

Preserve the complete cold `/home/v` and essential private state on the already
installed 4 TB SSD. Leave the old SSD bootable and untouched by migration writes.
Do not clone partition tables, format, repartition, replace encryption or copy
the old ESP. `metal-4tb` selects the new hardware; `metal` and `default` retain
the old UUIDs. Both use hostname `phoenix` and password-capable PAM.

## Outcome and acceptance, 2026-10-24

**PASS for the checked migration, boot and data workflows.** The initial boot was
generation 2 on the encrypted 4 TB SSD. The operator has since successfully run
`phoenix-switch` on that SSD and accepted Firefox, Codex, Navidrome, the user
environment and authentication by password and YubiKey. Do not rerun the migration
launcher on this installation.

### Final acceptance and service release

The operator authorized release on 2026-10-24. The release configuration removes
the temporary `metal-4tb` updater disable and both Syncthing marker conditions;
normal shared service configuration now applies. No acceptance marker needs to
be created or retained. Old `metal` configuration and root-identity guards are
unchanged. The stopped Syncthing identity, seven indexes and six folder mappings
were rechecked against the first audit before release; all matched. The prior
38.9 GB personal-data checksum audit was reused, not repeated unnecessarily.
There are 29 pre-existing `sync-conflict` files; all 29 match the read-only old
SSD byte-for-byte. Preserve them and compare this baseline after startup rather
than treating historical conflicts as new migration failures.

Apply this exact reviewed source through `phoenix-authorize ... -- phoenix-switch
--worktree /home/v/repos/code/phoenix-os-config`. Verify `syncthing.service` is
running, `syncthing-init.service` succeeded, the API reports the original device
identity, all six folders are healthy, no unexpected deletions/conflicts appear
and available peers connect. Normal send/receive operation can apply legitimate
changes accumulated on peers; do not reset the restored indexes or force a
rescan/revert to suppress a discrepancy. Stop and investigate unexpected changes.

The normal updater timer is enabled declaratively, daily at **21:00 local time**,
with persistent scheduling. Check its next deadline and `metal-4tb` runner/controller
targets after activation; do not launch a full update just to validate it. Current
runtime, boot profile, active-source provenance and protected deployment journal
are the authoritative installation binding. Commit completed source without
adding a self-referential receipt edit afterward.

### Reviewer state and frozen approvals

The first reviewed release exposed two separate dependencies. The operator used
the installed `phoenix-review-trust-active` helper with fresh Polkit authentication
to approve the exact already-running 4 TB baseline. That does not approve a new
release. Normal review then reported `review-authentication-missing`: the reviewer's
retained login was outside home and had been missed by the initial migration.

On operator authorization, a narrowly scoped immutable helper verified both native
disk identities, the old cold read-only mount and absent target credentials. It
read only the old reviewer's `auth.json`, staged it on the new SSD and reused the
installed controller's authentication importer for locking, atomic publication,
new service ownership, mode 0600 and removal of only the new staging name.
The restored bytes matched; the source bytes and mtime remained unchanged. No
credential values were emitted and no security override was used. A real normal
review, rather than merely a human `phoenix-switch`, is the final readiness test.

| State | Location | Treatment |
| --- | --- | --- |
| Editable worktrees | `/home/v/.codex/worktrees/*/phoenix-os-config` | Preserved with complete home and registered Git worktrees. |
| Frozen source / system closures | `/nix/store/*-source` and system paths | Immutable objects; selected closure imported, older objects retained on old SSD. These are not Btrfs snapshots. |
| Approved/pending review records and GC roots | `/var/lib/phoenix-deploy/security-review` | Root-protected authorization state; never adopted as ordinary user profile data. |
| Reviewer login and audit history | `/var/lib/phoenix-deploy-review` | Service-owned separate profile. Only the required retained login was restored; historical audit files stay on old. |
| Legacy login staging | `/home/v/.local/state/phoenix-agent-review` | Supported importer consumes its `auth.json`; protected reviewer then owns refreshes. |

The old checkpoint inventory contains **18 approved records, all targeting `metal`**;
none matches the installed policy or is compatible with `metal-4tb`. Zero approvals
were copied. They remain intact under the old mount for historical inspection.
Records bind source, closure, target and policy; branch/worktree labels are metadata,
not independent authority. Reuse is global across matching approved states, not a
guaranteed snapshot per worktree. Mutable approval records stay outside user home
so editing one's checkout cannot forge root authorization; the separate reviewer
login also avoids sharing the desktop app's live authentication/refresh lifecycle.

CoolerControl otherwise worked but requested a new UI control password after
migration. Preserving that UI password is an extremely low-priority future idea.
`phoenix-authorize` rejected one suspend request before the first local
`phoenix-switch`; do not investigate unless it recurs. Neither observation blocks
migration acceptance. See [VISION.md](VISION.md); no such improvement is implemented.

### Old-SSD rollback after synchronization resumes

Keep old serial `S4EWNG0M109916K` unchanged through at least **2026-11-24**.
It has the **same Syncthing identity and an increasingly stale index**. Never
let that installation reconnect as the active device, even if the new system
has been shut down. Do not modify the old SSD merely to prepare rollback.

For an emergency old-SSD boot, unplug Ethernet and isolate Wi-Fi first. In the
old systemd-boot entry, press **e** and append these temporary kernel parameters
before booting (do not save changes to the ESP):

```text
systemd.mask=syncthing.service systemd.mask=syncthing-init.service systemd.mask=phoenix-updates.service systemd.mask=phoenix-updates.timer systemd.mask=NetworkManager.service
```

These [systemd runtime masks](https://www.freedesktop.org/software/systemd/man/latest/systemd-debug-generator.html)
last only for that boot and prevent the services starting in the initial boot
transaction. Verify all five units are masked/inactive **before any networking**;
if kernel editing/isolation is unavailable, use a live USB instead of booting old.
Never start a manual or user Syncthing instance there. Keep old Syncthing masked
for the entire rollback session, even if networking is later required. A permanent
rollback needs a separately reviewed identity/index/data reconciliation; do not
reuse the stale database, unpause it blindly or reverse-sync complete homes.

The source data and original boot remain available for offline recovery. Booting
old normally will write its filesystem; retention means no such boot until an
explicit recovery decision. The unchanged old sync data also remains an offline
recovery copy of the pre-release state, not a live second peer.

### Initial audit evidence (before service release)

The successful path was online seeding followed by operator-run cold completion
from USB. The retained `operation-report.json` records the unpublished 307 GB seed;
it is not a final-snapshot receipt. The initial installed system and prebuilt receipt both
identify `/nix/store/2p81i3jnylb9zajfx2qh8fggw10pq7yr-nixos-system-phoenix-26.05.20261021.da6dc0e`,
built from `f78460731ea874de809f70b0ed067de4b377fcc9`. Its initial active source was
`/nix/store/far8896yi9zqb5zakbnysjkm7rz3bcmy-source`. The complete successful USB
console log was not located; current boot/data evidence and the operator's report
establish the outcome, rather than claiming a fixture proved execution.

| Acceptance check | Evidence / limit |
| --- | --- |
| Physical destination | Samsung 990 PRO 4TB, serial `S7DSNJ0Y411212Z`; root Btrfs `b1756a78-0da5-47a3-a73c-38112d1ac945` behind the expected LUKS2 p2 mapping. |
| Filesystems | `/` default/top-level ID 5, `/home` ID 256, `/nix` ID 257; `/boot` FAT `B4E3-63E5`. Native enumeration also includes `srv`, `tmp`, `var/tmp`, `var/lib/portables` and `var/lib/machines`; no snapshot subvolumes. |
| Encrypted swap | Expected LUKS p3 mapping and inner UUID `f323eb11-c576-45a5-9e5d-af4a329c94cb`; active, initially zero used. Old unencrypted swap inactive. Hibernation/resume remains untested. |
| Target selection | Installed `phoenix-target --info` reports `metal-4tb` from root UUID; switch/boot previews select it. `PHOENIX_TARGET=metal` is rejected. Installed agent controller policy has `target=metal-4tb` and the shared root guard. Update units are absent, so no updater was executed. Focused target evaluation passes. |
| Home Manager / ownership | `home-manager-v.service` succeeded with generation `3a5lnmyk9jicv9xkczb30zcr2gmfbwa8`; its user GC root resolves. Home is `1000:100`, mode 0700; matching subordinate UID/GID ranges remain. Foreign container UIDs were retained in inspected files. |
| Identity / authentication | Fresh machine-id matches the preparation receipt and differs from old. The v password hash matches old and is unlocked; U2F file matches exactly, owner `1000:100`, mode 0600; hostname `phoenix`. Neither installation has SSH host-key files to transfer. |
| Browser / Codex / keyring | Operator runtime checks pass. Firefox key/certificate databases match old. All 20 apparently absent Codex sessions are compressed archives whose decompressed bytes match old originals. All four keyring files exist; three match, one changed after use. |
| Syncthing | Both services inactive, both installed marker conditions intact, acceptance marker absent. Old/new checks pass all seven cold SQLite indexes, six exact folder mappings and certificate/key agreement; reports and all six configuration files match. Checksum dry-run of 9,072 regular personal files / 38,867,312,543 bytes finds no content changes. No synchronization started. |
| Navidrome | Running; main database matches old byte-for-byte and old cold database passes `quick_check`. Artwork/cache retained; new WAL/SHM reflects running use. Ownership is corrected to installed `991:988` (old `991:985`). Music is the verified home `sync/music`, mounted privately into the service. Accounts/playlists still need UI acceptance. |
| Core services | Home Manager, display manager, NetworkManager, Nix daemon, Navidrome, CoolerControl, fan watchdog and agent sockets active/successful. No failed user units. Two failed system units are Polkit authentication helpers; one journal reports `No session for cookie`. No service restart/reset was attempted. Fan response/fallback needs operator verification. |
| EFI / rollback | Current EFI check passes. Old ESP was briefly mounted read-only: both loader executables and all 14 entries' kernel/initrd files exist. Old current closure's init/kernel/initrd and root-aware fstab resolve correctly. This establishes bootability in principle, not a rollback boot test. |

### Quantified storage accounting

All values below are GiB (2^30 bytes), rounded. Measurements were made natively,
with root privileges for protected files. Before reading old file trees, its
desktop read-write mount was replaced by `/mnt/phoenix-old`, mounted
`ro,noatime,rescue=nologreplay,subvolid=5`. Both installations' real subvolumes were
included, including temporary subvolumes omitted by a simple `du -x /`.
The running destination changes during measurement; these are bounded observations,
not simultaneous frozen snapshots. Small diagnostic store/cache additions occurred.

| Whole-filesystem measure | Old | New | Old minus new | Meaning |
| --- | ---: | ---: | ---: | --- |
| Btrfs used | 526.09 | 273.26 | **252.82** | Actual used data plus duplicated metadata/system blocks at the recorded sample. |
| Data, single | 515.88 | 269.04 | 246.84 | Used data extents. |
| Metadata, DUP (physical) | 10.21 | 4.22 | 5.99 | Twice the logical metadata usage. |
| Allocated chunks | 587.02 | 360.02 | 227.00 | Includes free space inside allocated chunks; not another used-file total. |

`df` initially reported 526.59 versus 273.71 GiB: its reserve accounting and live
writes differ slightly from Btrfs `Used`. Never add the `/`, `/home` and `/nix`
`df` figures: they share one filesystem. System blocks contribute less than 1 MiB.

| Major tree / measure | Old | New | Difference | Explanation |
| --- | ---: | ---: | ---: | --- |
| `/nix`, `du` allocated | 216.22 | 36.48 | 179.74 | Deliberate closure installation instead of copying the old store/history/build state. |
| `/nix/store`, unique physical extents (`compsize`) | 202.20 | 30.01 | **172.19** | Counts shared extents once; distinguishes compression from `du` block accounting. |
| `/home/v`, apparent | 333.74 | 237.85 | **95.89** | Almost entirely the operator-confirmed post-migration Trash cleanup. |
| Trash, apparent | 95.91 | <0.01 | 95.91 | Intentionally emptied on new; retained unchanged on old. Mostly discarded VM/ISO data. |
| `/home/v`, `du` allocated | 335.79 | 226.49 | 109.30 | Also affected by sparse zero runs and shared-extent accounting. |
| `/home/v`, unique physical extents (`compsize`) | 300.49 | 225.28 | **75.20** | Old sharing saves more space than new sharing; full byte totals cannot be inferred from `du` alone. |
| Retained fresh-home migration backup, `du` | 0 | 14.36 | -14.36 | Mostly the retained 14.25 GiB local Nix binary cache, plus recovery copies. |
| `/tmp`, `du` allocated | 12.09 | 0.13 | 11.96 | Old temporary build/test trees deliberately not migrated. |
| `/var/lib`, `du` allocated | 2.04 | 0.14 | 1.90 | Includes 1.49 GiB old coredumps and old regenerable signatures/state. Navidrome retained. |
| `/var/log`, `du` allocated | 0.96 | 0.03 | 0.93 | Historical logs deliberately not migrated. |
| Home `.cache`, `du` allocated | 2.91 | 2.91 | ~0 | Home caches were included in cold completion. No blanket cache omission. |

The tree rows use different, overlapping measures and must not be added. A complete
`compsize -b -x` traversal of **all eight subvolumes** reports 517.05 versus
269.91 GiB of unique physical file extents, a 247.14 GiB difference. This closely
tracks the 246.84 GiB Btrfs data difference; inline extents, block rounding and
live-destination timing prevent exact equality. The remaining approximately
5.99 GiB is the measured metadata difference. Compression saves approximately
4.09 GiB on old versus 4.39 GiB on new: only **0.29 GiB more savings**, not the
explanation for the discrepancy.

Home extent sharing was measured rather than inferred: `btrfs filesystem du -s
--raw` reports old Total/Exclusive/Set-shared = 334.21 / 292.54 / 7.27 GiB,
new = 224.69 / 224.68 / 0.003 GiB. These columns are not additive.
`compsize` referenced-minus-uncompressed-unique extents decrease from 34.76 to
0.77 GiB, so the new copy loses about 33.99 GiB of duplicate-reference savings.
Sparse allocation partly offsets that loss: two large Steam files and one VM
image retain exact full-file SHA256 matches while using 12.60 GiB fewer blocks.
Steam's complete apparent size matches exactly (115.20 GiB); its allocated size
falls by 9.87 GiB. There are no historical snapshots on either disk.
See upstream [Btrfs accounting](https://btrfs.readthedocs.io/en/latest/btrfs-filesystem.html)
and [compsize semantics](https://github.com/kilobyte/compsize).

Nix's read-only old-store query found **63,869 versus 17,632 registered paths**;
NAR sizes are 202.62 versus 33.92 GiB (logical serialized content, not disk blocks).
Current Phoenix closures are virtually equal: **25.702 versus 25.703 GiB**.
The old store has 70.31 GiB beyond its current closure in the union of retained
system profiles, plus 106.61 GiB outside that union; the new store has 8.22 GiB
outside its current closure. Native inspection finds 14 old profile links and 14
EFI entries, despite the earlier estimate of ten. Additional old GC-root links
include 48 under deployment state and several temporary build/review outputs;
recent GC does not imply that only the current system remains. Old-only Codex
desktop-related paths account for 110.67 GiB NAR and `phoenix-codex.tar.gz` paths
for 28.39 GiB; these overlap the history/build categories, not extra totals.
No GC was run. The old store was queried only while mounted read-only, using
Nix 2.34's explicit `read-only-local-store` feature and `read-only=true`.

### Missing, changed and still unverified data

The privileged inventory examined 858,313 old and 855,538 new regular-file/symlink
entries without permission errors. The old-only paths are Trash, compressed
Codex originals, replaced Codex runtime/artifact-generation files, Firefox local
storage and one GVfs metadata file; no other old-only home paths were found.
All 23 Downloads files (1.52 GB) also pass a content-checksum dry-run.
The three largest allocation differences and two additional files pass full hashes.

Firefox has 140 old-only WhatsApp cache files (270.72 MiB) and one old-only ChatGPT
IndexedDB-associated file (2.48 MiB). Its cache churn is consistent with live use,
but the small IndexedDB file's application-level significance is **unverified**;
do not claim every browser-local byte is unchanged. Preserve it on old for any
later inspection. Active browser/Codex/keyring databases naturally differ and
were not treated as cold integrity snapshots. No unexpectedly absent ordinary
personal tree or Codex conversation was identified. This was an inventory plus
targeted checksum audit, not a new checksum of every 4 TB installation file.

### Initial holds and retention

During the initial audit both components remained held. The later explicit
operator approval and declarative release are described above. Do not create a
marker for the accepted configuration: its temporary conditions have been removed.
Normal updates still require a matching installed source baseline and the existing
protected target/review mechanisms; no old deployment approvals were transferred.

The operator subsequently accepted Navidrome and authentication. Hibernation is
not established and is outside migration closure. CoolerControl's password prompt
and the earlier suspend authorization rejection are optional observations above.
No authentication policy was changed. Two native read-only services succeeded during
accounting, but later Polkit requests failed/timed out; the operator ran the final
immutable read-only diagnostics via terminal sudo.

Keep old serial `S4EWNG0M109916K` unchanged **through at least 2026-11-24**, and longer
until the operator approves retirement. Its root remains mounted read-only at
`/mnt/phoenix-old`; its ESP is unmounted and swap inactive. The separate 2 TB SSD
`S4J4NZ0R303233H` remained unmounted and received no task writes. No source-file
writes, garbage collection, firmware changes, activation or reboot were performed
during the initial accounting audit. Later targeted activation is explicitly
authorized for service release. The initial desktop read-write mount predates these checks;
no claim is made about activity before it was replaced by the read-only mount.
Rollback remains a deliberate shutdown/firmware selection of the old SSD, never
a reverse-sync of whole live profiles or concurrent use of one Syncthing identity.

Private raw evidence for this session is under `/tmp/phoenix-acceptance`
(`consolidated-audit.txt`, `extra-audit.txt`, Nix inventories, checksum reports).
That directory is temporary and may disappear at reboot; this document retains
the non-secret measurements and acceptance limits.

### Lessons and future work

The three failed native preflights happened before restoration/install approval:

1. Fixed-width NVMe serial padding was rendered by `lsblk --raw` as literal
   `\x20`, defeating string trimming. Compare the native sysfs field, removing
   only documented padding; retain exact identity checks and native regression cases.
2. The USB kernel rejected standalone `nologreplay`; the supported cold mount
   option is `rescue=nologreplay`. Validate actual mount options on the intended
   kernel as well as emitted strings.
3. Cold SQLite WAL reads can require writable SHM even with `mode=ro`. Inspect
   disposable DB/WAL copies, preserve the underlying error and never infer corrupt
   or missing indexes from a read-only access error. Actual cold databases and the
   WAL fixture reproduce the old failure; the original detailed third log is absent.

Online seeding reduced cold copying, while final offline synchronization remained
necessary for active profiles. Supported Nix cache import reused the reviewed
closure without cloning the database. Root UUID guards remain a small shared
boundary across human, updater and agent paths. Future improvements should focus
on a representative boot-to-boot trial and a pinned runtime before adding guards;
use upstream tools for storage/copy/install semantics and retain durable logs
outside a live USB's temporary home. See [VISION.md](VISION.md) for the optional
backlog; none of those enhancements is implemented by this acceptance work.

## QUICKSTART (original migration; completed)

The following procedure documents the completed migration and is retained for
recovery review. **Do not launch it against the current migrated installation.**
Any retry requires review of the actual target and retained recovery directories.

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

The original execution required both operator confirmations and a final SUCCESS
before first boot. Online preparation was an unpublished seed, not a consistent
final home; installation and bootloader changes occurred only during cold completion.

The original workflow left final firmware selection and first-boot acceptance to
the operator. Boot order was deliberately preserved; select the intended SSD.

## Tool responsibilities

| Tool | Responsibility |
| --- | --- |
| `phoenix-migrate` (exported single file) | Bootstrap pinned tools, unlock/mount, mandatory native preflight, approval prompts, restoration, target-store Phoenix build/install and bootloader setup, final checks and cleanup. Never reboot, format or partition. |
| `migrate.py` | Source for the interactive orchestrator; accepts only the documented optional state flags. |
| `restore.py` | File restoration only, with native preflight, staging, progress and checksum verification. Does not install Phoenix. |
| `online.py` | Seed eligible home files into a new private directory on the verified mounted target; defer active profiles/databases. Never publish, install or activate. |
| `checks.py` | Syncthing/EFI/identity checks; SQLite examines disposable DB/WAL copies, never starts services or changes source databases. |
| `export-launcher.py` | Export HEAD's complete Git archive and commit identity into a portable launcher; excludes untracked/working-tree edits. |

After successful execution, the new SSD contains the complete old home, selected
service state, old v password and Phoenix `metal-4tb` boot closure. Fresh machine
ID, SSH keys and root password remain; hostname is phoenix. Syncthing and automatic
updates stay held. The old installation remains the rollback. Boot/login,
applications and cooling still need real-machine acceptance.

## Completed online preparation and cold handoff

This section records the preparation state before the successful USB completion;
the old installation is no longer the running system. Paths describe that stage.

The old Phoenix was running on the 1 TB SSD. The operator authorized stopping
Syncthing/Navidrome; both were stopped before their cold-state checks. The 2 TB
backup remained unmounted and excluded. Dolphin's new root mount was the Btrfs
top level: its real `home` and `nix` subvolumes were accessible underneath it.
No extra mounts were necessary for the online seed.

The unpublished seed is `/run/media/v/root/home/v/.phoenix-migration-online/home`.
Its adjacent `manifest.json` records identities, exclusions and rsync outcome;
`online-verification.txt` records the checksum dry-run. The fresh home and all
fresh system/security state are retained. Eligible home content is approximately
307 GB logical size, including the stopped Firefox profile, YubiKey mapping,
repositories, personal files and cold Syncthing configuration/indexes. All seven
Syncthing databases pass integrity checks and preserve the same six folder mappings.
The online checksum pass found only this actively edited repository and SQLite
coordination files created by the initial old-checker inspection (empty WALs and
regenerable SHM). Other eligible files matched. The corrected checker avoids that
source-side effect; those files are retained and finalized by the cold sync.

Codex (`.codex`, `.config/Codex`, `.local/state/codex`), GNOME Keyring, dconf,
active Phoenix/Kando/Caelestia state, rootless containers, SDDM/PKI state, caches
and other database/WAL files are **deferred online**, not excluded from the final
migration. The helper documents exact filters. Any early seed copies of subsequently
identified active profiles are retained separately in `deferred-unpublished`,
outside the usable seed. Online user copying cannot establish every foreign UID;
the final root-owned rsync reasserts numeric ownership and copies every deferred path.

Navidrome's private database is unreadable to v and is deferred to the existing
offline root copy. The old v password also needs the cold privileged step. Do not
resume either service merely to validate migration. Shutdown closes the remaining
Codex/keyring/session writers; no special Codex export is needed. The same USB
command completes all deferred data, full checksum/metadata verification and,
after `INSTALL` approval, target installation.

The cold restorer adopts the verified seed by rename within the home subvolume.
It performs a final complete incremental rsync. Replaced/stale seed entries are
retained under the fresh-home backup's `seed-before-final-sync`; no source files
are deleted. The full source-to-stage checksum/metadata comparison still gates
publication. A partially published restore requires recovery review, not blind retry.

## Native evidence, 2026-10-23

Inspected `lsblk`, mount information, Btrfs identity/root-ID ioctls, kernel
device-mapper sysfs and raw EFI variables. Names below are observations;
execution uses serial-qualified by-id paths and UUIDs.

| Device | Observed identity/layout |
| --- | --- |
| Old Samsung 970 EVO Plus 1TB | Serial `S4EWNG0M109916K`; 1,000,204,886,016 bytes; native device names vary between boots |
| Old ESP p1 | FAT32 `7618-BF96`; PARTUUID `5949426d-e7fe-458d-9d04-e26f062da171` |
| Old root p2 | Unencrypted Btrfs `e9d1b391-3f86-4254-9970-aa47df230474`; `/` ID 5, `home` ID 256, `nix` ID 257 |
| Old swap p3 | Unencrypted swap `51f0275d-56fd-486c-93cb-9cdd6ebcc5eb`; 71,311,671,296 bytes; active, zero used at inspection |
| New Samsung 990 PRO with Heatsink 4TB | Serial `S7DSNJ0Y411212Z`; 4,000,787,030,016 bytes; serial-qualified by-id path is authoritative |
| New ESP p1 | 1 GiB FAT32 `B4E3-63E5`; PARTUUID `d1a46384-039f-42f2-9ccd-13ec17dd2250` |
| New root p2 | 3,928,399,486,976 bytes; LUKS UUID `d9756988-1532-4903-b6d9-6e89735248f7`; PARTUUID `2e71962c-9167-4224-a4cd-41aeb445ec8b` |
| New decrypted root | Btrfs `b1756a78-0da5-47a3-a73c-38112d1ac945`; mounted top-level ID 5 at `/run/media/v/root`; root-ID ioctls confirm `home` 256 and `nix` 257 |
| New swap p3 | 71,311,667,200 bytes; LUKS UUID `8c5388a9-cb79-4c29-8de1-65cf542437e1`; PARTUUID `9828605f-2fec-4ee3-adeb-34cca577b07b`; unlocked inner swap UUID `f323eb11-c576-45a5-9e5d-af4a329c94cb`, inactive |
| Separate 2TB Windows/NTFS SSD | Serial `S4J4NZ0R303233H`; outside this migration |

Native device-mapper/sysfs information reports **LUKS2**, backed by new p2/p3
respectively. Mounted Btrfs supplies the inner root UUID; native root-ID ioctls
confirm home 256 and nix 257. These inspections used the native mount namespace;
sandbox device/mount inventories are not authoritative. Privileged raw
signature/header reads, Btrfs default/enumeration and ESP loader files remain
mandatory in the cold root preflight. Swap is not mounted as a filesystem.
The live-USB script requires
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
partition UUIDs/types still match. The target mappings are now unlocked, while raw
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

Before migration, the old installation selected `metal`. The new installed
`phoenix-target --info` reports `metal-4tb`; switch/boot previews and agent policy
agree with the native root UUID. A conflicting explicit `metal` fails closed.
The updater remains declaratively disabled; its shared targeting is covered by
the focused target evaluation rather than executing an update during acceptance.

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

## Prebuilt Phoenix and supported Nix copying

Nix 2.34.9 supports separate local stores with the same logical `/nix/store`,
`local?root=/mnt/phoenix-old&read-only=true`, and `nix copy --from ... --to
/mnt/phoenix-new PATH`. This imports store objects and adds their validity records
through Nix; it need not replace the destination database or select a system
profile. Never rsync `/nix/var/nix`, overwrite the fresh database, or use
`--profile`/activation as a reuse operation. Locally built unsigned closures may
also require explicit source trust/signature treatment.

Use the running source daemon to build `metal-4tb` **without activation**, then
`nix copy --to file:///.../.phoenix-migration-online/nix-cache?compression=zstd
SYSTEM` to export its complete closure. This is an ordinary Nix binary cache,
not a copy of the live Nix database. A real disposable two-import trial preserved
the fresh target database record and imported the new record successfully.
The actual fresh target's root-owned Nix database/profile remain unchanged online.
The actual import function also passed a disposable tiny-store trial with Nix's
experimental defaults disabled, preserving the fresh record and profile. Each
Nix invocation explicitly enables its required command/flake features for the USB.

An adjacent `build.json` is published only after the final committed build/cache
export succeeds. It records the source commit, system path and NAR hash. After
`INSTALL` approval, the USB driver checks the commit against its bundle, evaluates
the bundled `metal-4tb` output path, imports with supported `nix copy --from
file:///.../nix-cache --to /mnt/phoenix-new --no-check-sigs SYSTEM`, and checks
the imported NAR hash. `--no-check-sigs` trusts this locally prepared cache;
Nix still verifies its archive hashes. Keep the receipt/cache with the retained
fresh home. No old database, profile or boot closure is overwritten by import.

The native installer then uses `--system SYSTEM`; it does not rebuild Phoenix
on the USB. If no receipt is present, the original pinned flake build/download
path remains available. A present but mismatching/incomplete receipt is NO-GO.
Network is still needed to bootstrap the launcher's pinned tools/flake inputs.
Sources: [local store](https://nix.dev/manual/nix/2.34/store/types/local-store.html),
[nix copy](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-copy.html),
[file cache](https://nix.dev/manual/nix/2.34/store/types/local-binary-cache-store.html).

## Syncthing safety before any synchronization

Native configuration inspection confirms the six declared IDs/paths/markers.
The actual v2 main index maps those same IDs to six `folder.*.db` files.
Preflight requires the certificate/private-key pair to match, exact declared
folder paths and real `.stfolder` markers, matching main-index folder IDs,
existing mapped indexes, and SQLite `quick_check` for every database.
It runs cold and checks a private disposable copy of each DB plus its WAL;
SQLite rebuilds its regenerable SHM there. Source and staged DB/WAL/SHM files
remain byte-for-byte untouched. The full home copy includes all three, and repeats
the integrity check before checksum verification/publication. Never create an empty marker,
reset the index or regenerate a certificate to get past a failure.

The third attempt's wrapper hid the underlying SQLite exception and its detailed
log is unavailable, so the historical cause cannot be proved exactly. The actual
reported folder database and all other indexes exist and pass cold checks. A
regression reproduces the old failure with a valid committed WAL and no usable
SHM on a read-only source. Private read-only copies of the **seven actual cold
databases** also reproduce the same `folder.0001-vcanqjzi.db` wrapper error, with
the underlying cause `attempt to write a readonly database`; the corrected
checker passes and preserves all input bytes. [SQLite documents](https://www.sqlite.org/wal.html#read_only_databases)
that read-only WAL access can still need writable SHM/directory access. The fixed
checker passes that same fixture, consumes WAL-only folder mappings and leaves
all input bytes unchanged; it does not ignore WAL or use immutable mode.

The original migration bundle made both `syncthing.service` and
`syncthing-init.service` require the root-owned
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
approval, remove the temporary conditions declaratively as described above and
activate the reviewed new-host source. Observe the first
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
the source checkout nor the restored checkout is edited. With a matching prebuilt
cache, the equivalent `--system SYSTEM` selection follows supported closure import.
Otherwise the pinned native installer builds in the **destination Nix store**.
It retains its existing database,
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
The original migration bundle held Syncthing through first boot. The accepted
configuration removes those temporary conditions; see the release checks above.

The accepted new-host configuration removes the forced updater disable. Install
that exact committed source from `main` through the authorized deployment path.
Confirm the installed activated-source/system-profile baseline matches the
committed source. The updater
and protected policy then both select `metal-4tb`; `phoenix-update` and its timer
can stage normal updates without changing the old `metal` configuration. Do not
manually copy old deployment approvals/checkpoints or edit protected baselines.

Rollback: cleanly shut down, reconnect/select old serial `S4EWNG0M109916K` in
firmware, and boot its existing entry/generation **only with the offline isolation
and temporary service masks above**. Volatile read-only flags clear
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

The whole Phoenix system built before migration. Online copying, actual cold
Syncthing checks and a disposable Nix cache trial provided preparation evidence.
The operator subsequently completed the USB migration and booted generation 2;
current acceptance evidence and remaining checks are recorded above. No fixture
alone establishes bootability. During this acceptance pass only read-only
diagnostics, focused evaluation and documentation were performed; flake.lock,
hardware configuration, service holds and the running system closure are unchanged.
