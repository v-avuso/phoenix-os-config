"""Read-only migration checks. Never start services or repair databases."""
import hashlib
import re
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

FOLDERS = {
    "camera": "cj1t7-e1ozi", "scans": "cvh8w-sqnsh", "music": "edxdj-scujh",
    "media": "kjuh3-ybmkz", "knowledge": "qw4b9-tsser", "personal": "rrjk6-kxuwh",
}


def fresh_identity(root):
    machine_id = root / "etc/machine-id"
    require(machine_id.is_file() and not machine_id.is_symlink()
            and re.fullmatch(r"[a-f0-9]{32}\n?", machine_id.read_text()), "Fresh machine ID missing/invalid")
    paths = [machine_id, *sorted((root / "etc/ssh").glob("ssh_host_*"))]
    require(all(p.is_file() and not p.is_symlink() for p in paths), "Unexpected fresh SSH host-key object")
    shadow = root / "etc/shadow"
    require(shadow.is_file() and not shadow.is_symlink(), "Missing ordinary fresh shadow file")
    entries = [line.split(":") for line in shadow.read_text().splitlines() if line.startswith("root:")]
    require(len(entries) == 1 and len(entries[0]) == 9, "Fresh root password entry missing")
    identity = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    identity["root-password"] = hashlib.sha256(entries[0][1].encode()).hexdigest()
    return identity


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_folders(home, configuration):
    require((home / "sync").is_dir() and not (home / "sync").is_symlink(), "Missing ordinary Syncthing data root")
    folders = configuration.findall("folder")
    require(len(folders) == len(FOLDERS), "Review unexpected/missing Syncthing folders")
    for name, folder_id in FOLDERS.items():
        matches = [f for f in folders if f.get("id") == folder_id]
        require(len(matches) == 1, f"Syncthing folder ID mismatch: {name}")
        folder = matches[0]
        require(folder.get("path") == f"/home/v/sync/{name}"
                and folder.get("type") == "sendreceive", f"Syncthing path/type mismatch: {name}")
        directory = home / "sync" / name
        require(directory.is_dir() and not directory.is_symlink(), f"Missing ordinary sync folder: {name}")
        marker_name = folder.findtext("markerName", ".stfolder")
        require(marker_name == ".stfolder" and (directory / marker_name).exists()
                and not (directory / marker_name).is_symlink(),
                f"Syncthing marker missing/unexpected: {name}; do not recreate blindly")


def check_syncthing(home):
    configuration_dir = home / ".config/syncthing"
    database_dir = home / ".local/state/syncthing/index-v2"
    for name in ["config.xml", "cert.pem", "key.pem"]:
        path = configuration_dir / name
        require(path.is_file() and not path.is_symlink(), f"Missing ordinary Syncthing {name}")
    key = configuration_dir / "key.pem"
    require(key.stat().st_mode & 0o077 == 0, "Syncthing private key permissions are unsafe")
    check_folders(home, ET.parse(configuration_dir / "config.xml").getroot())
    public_cert = subprocess.check_output([
        "openssl", "x509", "-in", str(configuration_dir / "cert.pem"), "-pubkey", "-noout"], stderr=subprocess.DEVNULL)
    public_key = subprocess.check_output([
        "openssl", "pkey", "-in", str(key), "-pubout"], stderr=subprocess.DEVNULL)
    require(public_cert == public_key, "Syncthing certificate/private-key mismatch")
    databases = sorted(database_dir.glob("*.db"))
    require((database_dir / "main.db") in databases and len(databases) >= 7,
            "Syncthing v2 index missing; do not generate a new identity/database")
    mapping = {}
    for path in databases:
        require(not path.is_symlink(), "Symlinked Syncthing database refused")
        # Read-only SQLite still needs writable SHM when WAL recovery is needed.
        # Inspect a private disposable DB/WAL copy, never creating source files.
        # SHM is a regenerable index, not database content; rebuild it in scratch.
        try:
            with tempfile.TemporaryDirectory(prefix="phoenix-cold-index-") as temporary:
                scratch = Path(temporary) / path.name
                for source in [path, Path(str(path) + "-wal")]:
                    require(not source.is_symlink(), "Symlinked Syncthing database/WAL refused")
                    if source.exists():
                        require(source.is_file(), "Unexpected Syncthing database/WAL object")
                        copied = Path(temporary) / source.name
                        shutil.copyfile(source, copied)
                        copied.chmod(0o600)
                database = sqlite3.connect(scratch.as_uri() + "?mode=ro", uri=True, timeout=2)
                try:
                    database.execute("PRAGMA query_only=ON")
                    result = database.execute("PRAGMA quick_check").fetchall()
                    if path.name == "main.db":
                        mapping = dict(database.execute("SELECT folder_id, database_name FROM folders"))
                finally:
                    database.close()
            require(result == [("ok",)], f"Syncthing database integrity failed: {path.name}")
        except sqlite3.Error as error:
            raise RuntimeError(f"Cannot verify cold Syncthing database {path.name}: {error}; stop for review") from error
    require(set(mapping) == set(FOLDERS.values()), "Syncthing configured/indexed folder IDs differ")
    require(all(isinstance(name, str) and Path(name).name == name
                and (database_dir / name) in databases for name in mapping.values()),
            "Syncthing folder index missing or unsafe")
    return {
        "certificate": hashlib.sha256((configuration_dir / "cert.pem").read_bytes()).hexdigest(),
        "folders": dict(FOLDERS), "databases": mapping,
    }


def efi_load_option(data):
    """Parse GPT hard-drive nodes in an EFI_LOAD_OPTION, after efivar attributes."""
    require(len(data) >= 8, "Truncated EFI load option")
    path_size = struct.unpack_from("<H", data, 4)[0]
    position = 6
    while position + 2 <= len(data) and data[position:position + 2] != b"\0\0":
        position += 2
    position += 2
    end = position + path_size
    require(end <= len(data), "Invalid EFI device path length")
    result = []
    files = []
    while position + 4 <= end:
        kind, subtype, length = struct.unpack_from("<BBH", data, position)
        require(length >= 4 and position + length <= end, "Malformed EFI device path")
        if (kind, subtype) == (4, 1) and length >= 42 and data[position + 41] == 2:
            result.append(str(uuid.UUID(bytes_le=data[position + 24:position + 40])))
        if (kind, subtype) == (4, 4):
            files.append(data[position + 4:position + length].decode("utf-16le").rstrip("\0").replace("\\", "/").lstrip("/").lower())
        position += length
    return result, files, bool(struct.unpack_from("<I", data)[0] & 1)


def check_efi(esp, variables=Path("/sys/firmware/efi/efivars")):
    expected_guid = "d1a46384-039f-42f2-9ccd-13ec17dd2250"
    require(variables.is_dir(), "Boot the live USB in UEFI mode")
    matching = []
    for variable in variables.glob("Boot????-*"):
        guids, files, active = efi_load_option(variable.read_bytes()[4:])
        if active and expected_guid in guids and any(name in [
            "efi/systemd/systemd-bootx64.efi", "efi/boot/bootx64.efi"] for name in files):
            matching.append(variable.name[:8])
    require(matching, "No firmware entry for the new ESP GUID")
    for name in ["EFI/systemd/systemd-bootx64.efi", "EFI/BOOT/BOOTX64.EFI"]:
        path = esp / name
        require(path.is_file() and not path.is_symlink(), f"Missing new ESP loader: {name}")
        with path.open("rb") as stream:
            require(stream.read(2) == b"MZ", f"Unexpected EFI executable: {name}")
    require((esp / "loader/loader.conf").is_file(), "Missing new ESP loader.conf")
    entries = list((esp / "loader/entries").glob("*.conf"))
    require(entries, "Missing new ESP boot entries")
    for entry in entries:
        images = []
        for line in entry.read_text().splitlines():
            fields = line.split()
            if fields and fields[0] in ["linux", "initrd"]:
                require(len(fields) == 2, "Unexpected EFI loader image directive")
                image = Path(fields[1].lstrip("/"))
                require(".." not in image.parts and (esp / image).is_file(),
                        f"Missing/unsafe EFI image in {entry.name}")
                images.append(fields[0])
        require("linux" in images and "initrd" in images, f"Incomplete EFI entry: {entry.name}")
    return matching


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Read-only Syncthing/EFI checks; Syncthing must be stopped")
    parser.add_argument("--home", type=Path)
    parser.add_argument("--esp", type=Path)
    args = parser.parse_args()
    if not args.home and not args.esp:
        parser.error("supply --home and/or --esp")
    try:
        report = {}
        if args.home:
            report["syncthing"] = check_syncthing(args.home.absolute())
        if args.esp:
            report["efiEntries"] = check_efi(args.esp.absolute())
        print(json.dumps(report, indent=2))
    except (RuntimeError, OSError, subprocess.CalledProcessError, ET.ParseError) as error:
        parser.exit(1, f"NO-GO: {error}\n")
