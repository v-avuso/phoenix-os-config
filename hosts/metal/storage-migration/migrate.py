#!/usr/bin/env python3
"""Interactive cold migration. Run only through the exported live-USB launcher."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import restore as r
from checks import check_efi, check_syncthing, fresh_identity


def approve(word, explanation):
    print(explanation, flush=True)
    r.require(input(f"Type {word} to approve, or anything else to stop: ").strip() == word,
              "Operator declined; no further phase will run")


def firmware():
    directory = Path("/sys/firmware/efi/efivars")
    return {p.name: p.read_bytes() for p in directory.iterdir()
            if p.name.startswith("BootOrder-") or
            (p.name.startswith("Boot") and len(p.name.split("-")[0]) == 8)}


class Migration:
    def __init__(self, source, *, network=False, bluetooth=False):
        self.source = source
        self.options = (["--network"] if network else []) + (["--bluetooth"] if bluetooth else [])
        self.mounts = []
        self.mappings = []
        self.phase = "startup"

    def mount(self, device, target, *options):
        r.plain(target)
        target.mkdir(parents=True, exist_ok=True, mode=0o755)
        r.run("mount", *options, device, target)
        self.mounts.append(target)

    def unmount(self, target):
        r.run("umount", target)
        self.mounts.remove(target)

    def cleanup(self):
        errors = []
        for target in self.mounts.copy()[::-1]:
            try:
                self.unmount(target)
            except (OSError, subprocess.CalledProcessError):
                errors.append(str(target))
        for name in self.mappings.copy()[::-1]:
            try:
                r.run("cryptsetup", "close", name)
                self.mappings.remove(name)
            except (OSError, subprocess.CalledProcessError):
                errors.append(name)
        r.require(not errors, "Cleanup incomplete; stay in the live USB. Still in use: " + ", ".join(errors))

    def prepare(self):
        r.require(os.geteuid() == 0 and Path("/proc/self/uid_map").read_text().split()[:2] == ["0", "0"],
                  "Real host root is required")
        r.require(Path("/etc/NIXOS").exists() and Path("/sys/firmware/efi/efivars").is_dir(),
                  "Boot a NixOS live USB in UEFI mode")
        r.require(r.capture("findmnt", "-nro", "FSTYPE", "--target", "/") in ["tmpfs", "overlay"],
                  "Refusing an installed system; expected the live USB's RAM root")
        r.require(sys.stdin.isatty(), "An interactive terminal is required")
        for program in ["nixos-install", "nixos-enter", "git", "nix", "mount", "umount"]:
            r.require(shutil.which(program), "Missing command: " + program)
        r.require(len(Path("/proc/swaps").read_text().splitlines()) == 1,
                  "Swap is active. Stop and disable it through the live USB before retrying")
        self.boot_variables = firmware()
        for disk, serial, lower, upper in [
            (r.OLD_DISK, "S4EWNG0M109916K", .99e12, 1.01e12),
            (r.NEW_DISK, "S7DSNJ0Y411212Z", 3.99e12, 4.01e12),
        ]:
            r.check_serial(disk, serial)
            r.require(lower < int(r.capture("blockdev", "--getsize64", disk)) < upper, "Disk size mismatch")
            inventory = json.loads(r.capture("lsblk", "--json", "--output", "NAME,MOUNTPOINTS", disk))
            def inspect(nodes, depth=0):
                for node in nodes:
                    r.require(not any(node.get("mountpoints") or []), "Installation is already mounted; stop and unmount it")
                    r.require(depth < 2, "Existing device mapping; stop and close it before retrying")
                    inspect(node.get("children", []), depth + 1)
            inspect(inventory["blockdevices"])
        for target in [r.OLD, r.NEW, r.ESP]:
            r.plain(target)
            r.require(not target.exists() or not any(target.iterdir()), "Mount directory must be empty: " + str(target))
        for mapper in [r.ROOT_MAP, r.SWAP_MAP]:
            r.require(not mapper.exists(), "Existing LUKS mapping refused: " + str(mapper))
        # Probe raw identities before creating any mount or mapping.
        r.signature(str(r.OLD_DISK) + "-part2", "btrfs", r.OLD_UUID)
        r.signature(str(r.NEW_DISK) + "-part2", "crypto_LUKS", r.ROOT_LUKS)
        r.signature(str(r.NEW_DISK) + "-part3", "crypto_LUKS", r.SWAP_LUKS)
        for suffix in ["", "-part1", "-part2", "-part3"]:
            r.run("blockdev", "--setro", str(r.OLD_DISK) + suffix)
        self.mount(str(r.OLD_DISK) + "-part2", r.OLD, "-t", "btrfs", "-o", "ro,rescue=nologreplay,subvolid=5")
        for part, mapper, flags in [(2, r.ROOT_MAP, []), (3, r.SWAP_MAP, ["--readonly"])]:
            print(f"Unlock the NEW SSD {'root' if part == 2 else 'swap'} (password is not displayed).", flush=True)
            r.run("cryptsetup", "open", *flags, str(r.NEW_DISK) + f"-part{part}", mapper.name)
            self.mappings.append(mapper.name)
        self.mount(r.ROOT_MAP, r.NEW, "-t", "btrfs", "-o", "ro,rescue=nologreplay,subvolid=5")
        self.mount(str(r.NEW_DISK) + "-part1", r.ESP, "-o", "ro")
        self.syncthing, self.identity = r.preflight(False)
        for relative in self.selected_state():
            r.plain(r.OLD / relative)
            r.require((r.OLD / relative).is_dir(), "Missing selected state: " + relative)
        r.require(not (r.NEW / "home" / r.STAGING_HOME).exists(),
                  "An earlier restore has staging data; stop for recovery review")
        release = json.loads((self.source.parent / "release.json").read_text())
        r.require(len(release["commit"]) == 40, "Invalid bundle release identity")
        print("\nCHECKED PLAN\nOld 1 TB S4EWNG0M109916K: kernel read-only; rollback preserved.\n"
              "New 4 TB S7DSNJ0Y411212Z: restore complete /home/v, v password and "
              + ", ".join(self.selected_state()) + ".\n"
              "Retain fresh machine ID, SSH host keys and root password.\n"
              "Install Phoenix metal-4tb from reviewed commit " + release["commit"] + ".\n"
              "Syncthing and automatic updates stay held. Firmware boot order stays unchanged.\n"
              "Installation reasserts managed Home Manager settings; file backups stay on the new SSD.", flush=True)

    def selected_state(self):
        return ["var/lib/navidrome"] + (["etc/NetworkManager/system-connections"] if "--network" in self.options else []) + (
            ["var/lib/bluetooth"] if "--bluetooth" in self.options else [])

    def restore(self):
        self.unmount(r.NEW)
        self.mount(r.ROOT_MAP, r.NEW, "-t", "btrfs", "-o", "subvolid=5")
        r.run(sys.executable, "-B", Path(__file__).with_name("restore.py"),
              "--apply", "RESTORE-TO-S7DSNJ0Y411212Z", *self.options)

    def install(self):
        self.mount(r.ROOT_MAP, r.NEW / "home", "-t", "btrfs", "-o", "subvol=home")
        self.mount(r.ROOT_MAP, r.NEW / "nix", "-t", "btrfs", "-o", "subvol=nix")
        self.unmount(r.ESP)
        self.mount(str(r.NEW_DISK) + "-part1", r.NEW / "boot", "-o", "rw")
        # Only the reviewed Git archive is exposed to Nix, never private/untracked home data.
        r.run("git", "init", "--quiet", self.source)
        r.run("git", "-C", self.source, "add", "--force", "--all")
        system = self.import_prebuilt()
        # Native installer changes only the destination profile, activation and ESP.
        selection = ["--system", system] if system else ["--flake", str(self.source) + "#metal-4tb"]
        r.run("nixos-install", "--root", r.NEW, *selection,
              "--no-root-passwd", "--no-channel-copy", "--no-write-lock-file")
        r.run("nixos-enter", "--root", r.NEW, "-c", "chown -hR navidrome:navidrome /var/lib/navidrome")

    def import_prebuilt(self):
        control = r.NEW / "home" / r.FRESH_HOME / r.ONLINE_CONTROL
        receipt = control / "build.json"
        r.plain(receipt)
        if not receipt.exists():
            return None  # Normal supported target-store build/download remains available.
        r.plain(control / "nix-cache")
        build = json.loads(receipt.read_text())
        release = json.loads((self.source.parent / "release.json").read_text())
        r.require(build.get("commit") == release["commit"] and build.get("cacheReady") is True,
                  "Prebuilt closure is incomplete or belongs to another launcher")
        expected = r.capture("nix", "eval", "--raw", "--no-write-lock-file",
                             str(self.source) + "#nixosConfigurations.metal-4tb.config.system.build.toplevel.outPath")
        r.require(build.get("system") == expected and expected.startswith("/nix/store/"),
                  "Prebuilt closure differs from the reviewed metal-4tb configuration")
        print("Importing the prebuilt Phoenix closure through Nix; preserving the fresh store database", flush=True)
        r.run("nix", "copy", "--from", (control / "nix-cache").as_uri(),
              "--to", r.NEW, "--no-check-sigs", expected)
        info = json.loads(r.capture("nix", "path-info", "--store", r.NEW,
                                    "--json", "--json-format", "2", expected))[expected]
        r.require(info["narHash"] == build.get("narHash"), "Imported Phoenix closure hash mismatch")
        return expected

    def verify(self):
        # Resolve absolute /etc links inside the target, never against the live USB.
        r.run("nixos-enter", "--root", r.NEW, "-c", """set -eu
test "$(cat /etc/hostname)" = phoenix
test "$(passwd -S v | awk '{print $2}')" = P
test ! -e /var/lib/phoenix-migration/syncthing-accepted
grep -F 'ConditionPathExists=/var/lib/phoenix-migration/syncthing-accepted' /etc/systemd/system/syncthing.service /etc/systemd/system/syncthing-init.service
test ! -e /etc/systemd/system/timers.target.wants/phoenix-updates.timer
grep -F 'luks-d9756988-1532-4903-b6d9-6e89735248f7' /etc/fstab
grep -F 'B4E3-63E5' /etc/fstab
test -x /nix/var/nix/profiles/system/bin/switch-to-configuration
test "$(stat -c %U /var/lib/navidrome)" = navidrome
profile=$(readlink -f /nix/var/nix/profiles/system)
entry=$(grep -lF "init=$profile/init " /boot/loader/entries/*.conf | head -n 1)
test -n "$entry"
test "$(basename "$entry")" = "$(awk '$1 == "default" {print $2}' /boot/loader/loader.conf)"
grep -F 'root=fstab' "$entry"
""")
        r.require(fresh_identity(r.NEW) == self.identity, "Fresh installation identity changed")
        r.require(check_syncthing(r.NEW / "home/v") == self.syncthing, "Syncthing identity/index layout changed")
        check_efi(r.NEW / "boot")
        r.require(firmware() == self.boot_variables, "Firmware boot entries/order changed; stop for review")
        for suffix in ["", "-part1", "-part2", "-part3"]:
            r.require(r.capture("blockdev", "--getro", str(r.OLD_DISK) + suffix) == "1", "Source lost read-only protection")
        r.run("sync", "-f", r.NEW)

    def execute(self):
        try:
            self.phase = "native preflight and unlocking"
            self.prepare()
            approve("RESTORE", "Approve writing restored files ONLY to the checked 4 TB SSD.")
            self.phase = "file restoration"
            self.restore()
            approve("INSTALL", "Files verified. Approve the offline Phoenix build, target activation and new ESP installation.")
            self.phase = "offline Phoenix installation"
            self.install()
            self.phase = "final verification"
            self.verify()
        finally:
            self.cleanup()
        print("\nSUCCESS: Phoenix is installed on the 4 TB SSD; all offline checks passed and mounts are closed.\n"
              "Power off. Prefer disconnecting the old SSD while powered off. Select the 4 TB SSD in firmware.\n"
              "Test password login first. Syncthing and automatic updates remain held pending acceptance.\n"
              "The untouched 1 TB SSD is the rollback. No reboot was performed.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", action="store_true", help="also preserve saved NetworkManager connections")
    parser.add_argument("--bluetooth", action="store_true", help="also preserve Bluetooth pairings")
    args = parser.parse_args()
    os.umask(0o077)
    migration = Migration(Path(__file__).resolve().parents[3], network=args.network, bluetooth=args.bluetooth)
    try:
        migration.execute()
    except (Exception, KeyboardInterrupt) as error:
        print(f"\nNO-GO during {migration.phase}: {error}\nDo not boot the target. Keep backups; follow the recovery runbook. The old SSD remains the rollback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
