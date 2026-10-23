#!/usr/bin/env python3
"""Seed a private, unpublished home copy on the already mounted 4 TB target."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import restore as r

CONTROL = r.ONLINE_CONTROL
DEFERRED = ["/.codex/", "/.config/Codex/", "/.local/state/phoenix*/",
            "/.config/phoenix-kando/", "/.local/state/codex/", "/.local/state/caelestia/",
            "/.local/share/sddm/", "/.pki/",
            "/.local/share/containers/", "/.local/share/keyrings/", "/.config/dconf/",
            "/.cache/", "*.db", "*.db-*", "*.sqlite", "*.sqlite-*", "*.sqlite3", "*.sqlite3-*",
            "*-wal", "*-shm", "*-journal", "*.sock", "/" + CONTROL + "/"]


def service_stopped(name):
    result = subprocess.run(["systemctl", "is-active", name + ".service"], capture_output=True, text=True)
    return result.stdout.strip() in ["inactive", "failed"]


def target_control(root):
    r.require(os.geteuid() == 1000, "Run online seeding as v, not root")
    r.require(r.capture("findmnt", "-nro", "UUID", "--target", "/") == r.OLD_UUID,
              "Online source must be the old Phoenix root")
    for disk, serial in [(r.OLD_DISK, "S4EWNG0M109916K"), (r.NEW_DISK, "S7DSNJ0Y411212Z")]:
        r.check_serial(disk, serial)
    mounts = list(r.flatten(json.loads(r.capture("findmnt", "--json", "--output",
                                               "TARGET,UUID,FSTYPE,FSROOT,OPTIONS"))["filesystems"]))
    own = [m for m in mounts if m["target"] == str(root)]
    r.require(len(own) == 1 and own[0].get("uuid") == r.NEW_UUID and own[0].get("fstype") == "btrfs"
              and own[0].get("fsroot") == "/" and "rw" in own[0]["options"].split(","),
              "Expected the new SSD's writable Btrfs top level")
    r.require(not any(m.get("uuid") in ["3A05-B29F", "5EE2873DE2871903", "7CFA7AE2FA7A97DA"] for m in mounts),
              "The excluded 2 TB drive must remain unmounted")
    for sub, expected in [("home", "256"), ("nix", "257")]:
        r.require(r.capture("findmnt", "-nro", "UUID", "--target", root / sub) == r.NEW_UUID,
                  "Target subvolume belongs to another filesystem")
        r.require(r.capture("btrfs", "inspect-internal", "rootid", root / sub) == expected,
                  "Unexpected target subvolume: " + sub)
    home = root / "home/v"
    r.plain(home)
    r.require(home.is_dir() and (home.stat().st_uid, home.stat().st_gid) == (1000, 100), "Unexpected target account home")
    control = home / CONTROL
    r.plain(control)
    r.plain(control / "home")
    if control.exists():
        manifest = json.loads((control / "manifest.json").read_text())
        r.require(manifest.get("sourceRootUUID") == r.OLD_UUID and manifest.get("targetRootUUID") == r.NEW_UUID,
                  "Existing online staging identity mismatch")
    else:
        control.mkdir(mode=0o700)
        write_manifest(control, {"version": 1, "sourceRootUUID": r.OLD_UUID, "targetRootUUID": r.NEW_UUID,
                                 "status": "created", "consistentFinalSnapshot": False})
    return control


def write_manifest(control, manifest):
    temporary = control / ".manifest-new.json"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(control / "manifest.json")


def rsync_filters(syncthing_cold):
    filters = ["--include=/.mozilla/***"]
    if syncthing_cold:
        filters += ["--include=/.config/syncthing/***", "--include=/.local/state/syncthing/***"]
    else:
        filters += ["--exclude=/.config/syncthing/", "--exclude=/.local/state/syncthing/"]
    return filters + ["--exclude=" + path for path in DEFERRED]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, default=Path("/run/media/v/root"))
    parser.add_argument("--copy", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    control = target_control(args.target_root)
    # No Firefox-family process may own the explicitly included cold profile.
    processes = r.capture("ps", "-eo", "comm").lower().splitlines()
    r.require(not any(any(browser in p for browser in ["firefox", "librewolf", "floorp"]) for p in processes),
              "Firefox is running; defer its profile instead of copying live databases")
    syncthing_cold = service_stopped("syncthing") and not any("syncthing" in p for p in processes)
    filters = rsync_filters(syncthing_cold)
    command = [*r.RSYNC, "--one-file-system", "--no-devices", "--no-specials", *filters,
               "--info=progress2", "--stats", "/home/v/", str(control / "home") + "/"]
    manifest = json.loads((control / "manifest.json").read_text())
    manifest.update(excludedOnline=DEFERRED, syncthingCopiedCold=syncthing_cold,
                    codexDeferred=True, ownershipRequiresFinalRootSync=True,
                    source="/home/v", destination=str(control / "home"))
    if not args.copy:
        command.insert(1, "--dry-run")
    else:
        manifest.update(status="copying", startedUnix=time.time())
        write_manifest(control, manifest)
    print("Unpublished online seed:", control, "Syncthing cold:", syncthing_cold, flush=True)
    result = subprocess.run(command)
    if args.copy:
        manifest.update(status="seeded" if result.returncode == 0 else "partial",
                        rsyncExit=result.returncode, finishedUnix=time.time())
        write_manifest(control, manifest)
    r.require(result.returncode == 0, "Rsync reported incomplete data; retain staging and inspect its log")
    print("ONLINE SEED ONLY. Final offline synchronization and verification are mandatory.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit("STOP: " + str(error))
