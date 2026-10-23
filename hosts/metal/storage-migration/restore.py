#!/usr/bin/env python3
"""Offline data restoration only. No formatting, installation or activation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from checks import check_efi, check_syncthing, fresh_identity

OLD = Path("/mnt/phoenix-old")
NEW = Path("/mnt/phoenix-new")
ESP = Path("/mnt/phoenix-esp")
OLD_UUID = "e9d1b391-3f86-4254-9970-aa47df230474"
NEW_UUID = "b1756a78-0da5-47a3-a73c-38112d1ac945"
ROOT_LUKS = "d9756988-1532-4903-b6d9-6e89735248f7"
SWAP_LUKS = "8c5388a9-cb79-4c29-8de1-65cf542437e1"
ROOT_MAP = Path("/dev/mapper/luks-" + ROOT_LUKS)
SWAP_MAP = Path("/dev/mapper/luks-" + SWAP_LUKS)
OLD_DISK = Path("/dev/disk/by-id/nvme-Samsung_SSD_970_EVO_Plus_1TB_S4EWNG0M109916K")
NEW_DISK = Path("/dev/disk/by-id/nvme-Samsung_SSD_990_PRO_with_Heatsink_4TB_S7DSNJ0Y411212Z")
FRESH_HOME = ".phoenix-fresh-v-before-migration"
STAGING_HOME = ".phoenix-restoring-v"
RSYNC = ["rsync", "-aHAXS", "--numeric-ids"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def capture(*args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def check_serial(disk, expected):
    """Bind native NVMe identity to the by-id link's actual block device."""
    device = Path(disk).stat()  # Follow the by-id link; never depend on nvme numbering.
    require(stat.S_ISBLK(device.st_mode), f"Identity path is not a block device: {disk}")
    native = Path(f"/sys/dev/block/{os.major(device.st_rdev)}:{os.minor(device.st_rdev)}/device/serial")
    # NVMe serials are fixed-width, space-padded fields. lsblk --raw can emit
    # literal \\x20 escapes for that padding when it falls back from udev to sysfs.
    observed = native.read_text().rstrip(" \n")
    require(observed == expected,
            f"Disk serial mismatch for {disk}: expected {expected!r}, observed {observed!r} via {native}")


def plain(path):
    """Reject symlink destinations, including symlinks in parent components."""
    path = Path(path)
    for item in [path, *path.parents]:
        require(not item.is_symlink(), f"Symlink destination refused: {item}")


def flatten(mounts):
    for mount in mounts:
        yield mount
        yield from flatten(mount.get("children", []))


def validate_mounts(mounts, *, apply):
    for root, uuid in [(OLD, OLD_UUID), (NEW, NEW_UUID)]:
        matching = [m for m in mounts if m.get("target") == str(root)]
        require(len(matching) == 1, f"Expected exactly one mount at {root}")
        mount = matching[0]
        require(mount.get("uuid") == uuid and mount.get("fstype") == "btrfs"
                and mount.get("fsroot") == "/", f"Wrong filesystem/top-level at {root}")
        opts = set(mount["options"].split(","))
        if root == OLD:
            require("ro" in opts and "nologreplay" in opts,
                    "Old filesystem must be ro,nologreplay")
        elif apply:
            require("rw" in opts, "Destination must be read-write for apply")
        for other in mounts:
            target = other["target"]
            require(not target.startswith(str(root) + "/"), f"Nested mount refused: {target}")
            if other.get("uuid") == uuid:
                require(target == str(root), f"Disk also mounted elsewhere: {target}")
    require(not any(m.get("target") == "/" and m.get("uuid") in [OLD_UUID, NEW_UUID]
                    for m in mounts), "Run from a live USB, not either installation")


def signature(device, expected_type, expected_uuid=None, *, part_uuid=None, part_type=None):
    fields = dict(line.split("=", 1) for line in capture(
        "blkid", "-p", "-o", "export", device).splitlines() if "=" in line)
    require(fields.get("TYPE") == expected_type, f"Unexpected filesystem on {device}")
    if expected_uuid:
        require(fields.get("UUID") == expected_uuid, f"UUID mismatch on {device}")
    if part_uuid:
        require(fields.get("PART_ENTRY_UUID") == part_uuid, f"Partition GUID mismatch on {device}")
    if part_type:
        require(fields.get("PART_ENTRY_TYPE") == part_type, f"Partition type mismatch on {device}")
    return fields


def preflight(apply):
    require(os.geteuid() == 0, "Run as root on the NixOS live USB")
    uid_map = Path("/proc/self/uid_map").read_text().split()
    require(uid_map[:2] == ["0", "0"], "Host root required; user namespaces are refused")
    for program in ["rsync", "findmnt", "lsblk", "blkid", "blockdev", "btrfs", "cryptsetup", "du", "openssl"]:
        require(shutil.which(program), f"Missing command: {program}")
    mounts = list(flatten(json.loads(capture(
        "findmnt", "--json", "--output", "TARGET,UUID,FSTYPE,OPTIONS,FSROOT"))["filesystems"]))
    validate_mounts(mounts, apply=apply)
    efi_mounts = [m for m in mounts if m.get("target") == str(ESP)]
    require(len(efi_mounts) == 1 and efi_mounts[0].get("uuid") == "B4E3-63E5"
            and efi_mounts[0].get("fstype") == "vfat"
            and "ro" in efi_mounts[0]["options"].split(","), "Mount the new ESP read-only at /mnt/phoenix-esp")
    print("Verified new ESP files and firmware entries: " + ", ".join(check_efi(ESP)), flush=True)
    for path in [OLD, NEW, NEW / "home", NEW / "etc", NEW / "var/lib"]:
        plain(path)
    for disk, serial, lower, upper in [
        (OLD_DISK, "S4EWNG0M109916K", 0.99e12, 1.01e12),
        (NEW_DISK, "S7DSNJ0Y411212Z", 3.99e12, 4.01e12),
    ]:
        check_serial(disk, serial)
        require(lower < int(capture("blockdev", "--getsize64", disk)) < upper, "Disk size mismatch")
    for suffix in ["", "-part1", "-part2", "-part3"]:
        require(capture("blockdev", "--getro", str(OLD_DISK) + suffix) == "1",
                "All old SSD block devices must be kernel read-only")
    signature(str(OLD_DISK) + "-part2", "btrfs", OLD_UUID)
    signature(str(NEW_DISK) + "-part1", "vfat", "B4E3-63E5",
              part_uuid="d1a46384-039f-42f2-9ccd-13ec17dd2250",
              part_type="c12a7328-f81f-11d2-ba4b-00a0c93ec93b")
    for part, uuid, mapper, partition in [
        (2, ROOT_LUKS, ROOT_MAP, "2e71962c-9167-4224-a4cd-41aeb445ec8b"),
        (3, SWAP_LUKS, SWAP_MAP, "9828605f-2fec-4ee3-adeb-34cca577b07b"),
    ]:
        raw = Path(str(NEW_DISK) + f"-part{part}")
        signature(raw, "crypto_LUKS", uuid, part_uuid=partition)
        require(any(line.split() == ["Version:", "2"] for line in capture(
            "cryptsetup", "luksDump", raw).splitlines()), "Expected LUKS2")
        status = capture("cryptsetup", "status", mapper.name)
        backing = next((line.split(":", 1)[1].strip() for line in status.splitlines()
                        if line.strip().startswith("device:")), "")
        require(backing and Path(backing).resolve() == raw.resolve(), "Wrong decrypted backing device")
    signature(ROOT_MAP, "btrfs", NEW_UUID)
    swap = signature(SWAP_MAP, "swap")
    require(swap.get("UUID"), "New inner swap UUID is missing")
    print(f"Verified new inner swap UUID: {swap['UUID']}", flush=True)
    # With every swap device disabled, neither old swap nor a hibernation image is touched.
    require(len(Path("/proc/swaps").read_text().splitlines()) == 1, "Disable live-USB swap before proceeding")
    for root in [OLD, NEW]:
        require(capture("btrfs", "subvolume", "get-default", root).startswith("ID 5 "),
                f"Unexpected Btrfs default subvolume: {root}")
        for subvolume, expected_id in [("home", "256"), ("nix", "257")]:
            require(capture("btrfs", "inspect-internal", "rootid", root / subvolume) == expected_id,
                    f"Unexpected subvolume: {root / subvolume}")
        run("btrfs", "subvolume", "list", root)
        account = next((line.split(":") for line in (root / "etc/passwd").read_text().splitlines()
                        if line.startswith("v:")), [])
        require(len(account) == 7 and account[2:4] == ["1000", "100"]
                and account[5] == "/home/v", f"Unexpected v identity on {root}")
    old_home = OLD / "home/v"
    require(old_home.is_dir() and not old_home.is_symlink(), "Missing ordinary source home")
    require((old_home.stat().st_uid, old_home.stat().st_gid) == (1000, 100), "Home ownership mismatch")
    key = old_home / ".config/Yubico/u2f_keys"
    require(key.is_file() and not key.is_symlink() and key.stat().st_uid == 1000
            and key.stat().st_mode & 0o077 == 0, "YubiKey mapping missing or unsafe")
    password_line(OLD / "etc/shadow")
    keyrings = old_home / ".local/share/keyrings"
    require(keyrings.is_dir() and not keyrings.is_symlink() and any(keyrings.iterdir()), "GNOME Keyring state missing")
    syncthing = check_syncthing(old_home)
    print("Verified Syncthing identity/key pair, six folder IDs/markers and cold SQLite indexes", flush=True)
    print("Syncthing certificate SHA256: " + syncthing["certificate"], flush=True)
    require(not (NEW / "home" / FRESH_HOME).exists(), "Home already published; follow recovery instructions")
    require(not (NEW / "var/lib/phoenix-migration/syncthing-accepted").exists(),
            "Syncthing acceptance marker already exists; stop for review")
    required = int(capture("du", "-s", "--apparent-size", "--block-size=1", old_home).split()[0])
    available = shutil.disk_usage(NEW / "home").free
    require(available > required + 20 * 1024**3, "Need home apparent size plus 20 GiB free")
    print(f"Home apparent bytes: {required:,}; destination free: {available:,}", flush=True)
    # Rootless container identities must survive the home copy. Refuse broader account merging.
    for name in ["subuid", "subgid"]:
        for root in [OLD, NEW]:
            path = root / "etc" / name
            plain(path)
            require(path.read_text().strip() == "v:100000:65536", f"Review subordinate IDs: {path}")
    return syncthing, fresh_identity(NEW)


def verify_copy(source, destination):
    result = capture(*RSYNC, "--checksum", "--dry-run", "--delete", "--itemize-changes",
                     str(source) + "/", str(destination) + "/")
    # --delete is ONLY used with --dry-run to detect destination-only entries.
    require(not result, "Copy verification differs; retain staging and inspect before continuing")


def copy_home(source, home, *, validator=None):
    stage, fresh, target = home / STAGING_HOME, home / FRESH_HOME, home / "v"
    for path in [home, stage, fresh, target]:
        plain(path)
    require(not fresh.exists(), "Fresh-home backup exists; refusing a second publication")
    require(target.is_dir(), "Expected fresh v home")
    run(*RSYNC, "--info=progress2", "--stats", str(source) + "/", str(stage) + "/")
    print("Checking all home file checksums and metadata (a second full read)…", flush=True)
    if validator:
        validator(stage)
    verify_copy(source, stage)
    target.rename(fresh)
    try:
        stage.rename(target)
    except BaseException:
        fresh.rename(target)
        raise


def password_line(path):
    plain(path)
    lines = [line for line in path.read_text().splitlines() if line.startswith("v:")]
    require(len(lines) == 1 and len(lines[0].split(":")) == 9
            and lines[0].split(":")[1].startswith("$"), "v needs a usable password hash; stop for password recovery")
    return lines[0]


def restore_password(source, target):
    replacement = password_line(source)
    plain(target)
    lines = target.read_text().splitlines()
    require(sum(line.startswith("v:") for line in lines) == 1, "Destination v shadow entry missing")
    stat = target.stat()
    fd, temporary = tempfile.mkstemp(prefix=".phoenix-shadow-", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(replacement if line.startswith("v:") else line for line in lines) + "\n")
            f.flush(); os.fsync(f.fileno())
        shutil.copystat(target, temporary)
        if os.geteuid() == 0:
            os.chown(temporary, stat.st_uid, stat.st_gid)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def backup(relative):
    source = NEW / relative
    target = NEW / "root/phoenix-migration-before" / relative
    plain(source); plain(target)
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(source.is_file(), f"Expected regular backup file: {source}")
        run(*RSYNC, source, target)


def restore_directory(relative):
    source, target = OLD / relative, NEW / relative
    saved = NEW / "root/phoenix-migration-before" / relative
    stage = target.with_name(".phoenix-restoring-" + target.name)
    for path in [source, target, saved, stage]:
        plain(path)
    if saved.exists():
        # A previous attempt published this state. Only resume when it is exact.
        verify_copy(source, target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    run(*RSYNC, "--info=progress2", str(source) + "/", str(stage) + "/")
    verify_copy(source, stage)
    if target.exists():
        saved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.rename(saved)
    try:
        stage.rename(target)
    except BaseException:
        if saved.exists(): saved.rename(target)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", metavar="CONFIRMATION", choices=["RESTORE-TO-S7DSNJ0Y411212Z"])
    parser.add_argument("--network", action="store_true", help="also restore saved NetworkManager connections")
    parser.add_argument("--bluetooth", action="store_true", help="also restore Bluetooth pairings")
    args = parser.parse_args()
    os.umask(0o077)
    apply = bool(args.apply)
    print("Phase 1/4: native device, offline mount, identity and capacity checks", flush=True)
    syncthing, identity = preflight(apply)
    selected = ["var/lib/navidrome"]
    if args.network: selected.append("etc/NetworkManager/system-connections")
    if args.bluetooth: selected.append("var/lib/bluetooth")
    print("State selection: v password + " + ", ".join(selected), flush=True)
    for relative in selected:
        source, target = OLD / relative, NEW / relative
        plain(source); plain(target)
        require(source.is_dir(), f"Expected state directory missing: {source}")
    if not apply:
        print("PLAN ONLY: dry-run home copy; no destination files will be written", flush=True)
        run(*RSYNC, "--dry-run", "--stats", str(OLD / "home/v") + "/", str(NEW / "home" / STAGING_HOME) + "/")
        return
    print("Phase 2/4: backing up fresh target state; restoring selected persistent state", flush=True)
    backup("etc/shadow")
    for relative in selected:
        restore_directory(relative)
    restore_password(OLD / "etc/shadow", NEW / "etc/shadow")
    print("Phase 3/4: restoring complete /home/v into a separate staging directory", flush=True)
    copy_home(OLD / "home/v", NEW / "home", validator=lambda stage: require(
        check_syncthing(stage) == syncthing, "Restored Syncthing identity/folder/index layout changed"))
    require(fresh_identity(NEW) == identity, "Fresh machine ID, SSH host keys or root password changed; stop before installation")
    print("Phase 4/4: flushing destination filesystem", flush=True)
    run("sync", "-f", NEW)
    print("DATA RESTORED. No installation or activation performed. Follow README before booting.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        # Never render private shadow content or profile data in diagnostics.
        print(f"STOP: {error}", file=sys.stderr)
        sys.exit(1)
