"""Disposable checks only: no host disks, private profiles or root operations."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sqlite3
import stat
import struct
from types import SimpleNamespace
import uuid
import tempfile
import unittest
from unittest.mock import patch
from checks import FOLDERS, check_folders, check_efi, check_syncthing, fresh_identity
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("restore", Path(__file__).with_name("restore.py"))
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class Safety(unittest.TestCase):
    def test_native_serial_accepts_only_fixed_width_padding(self):
        disk = Path("/dev/disk/by-id/fixture")
        device = SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(259, 4))
        for serial in ["S4EWNG0M109916K\n", "S4EWNG0M109916K     \n"]:
            with self.subTest(serial=serial), patch.object(Path, "stat", return_value=device), \
                 patch.object(Path, "read_text", return_value=serial):
                restore.check_serial(disk, "S4EWNG0M109916K")
        for serial in ["S4J4NZ0R303233H     \n", "S4EWNG0M109916K\\x20\\x20\n", "S4EWNG0M109916K extra\n",
                       " S4EWNG0M109916K\n", "S4EWNG0M109916K\t\n", ""]:
            with self.subTest(serial=serial), patch.object(Path, "stat", return_value=device), \
                 patch.object(Path, "read_text", return_value=serial):
                with self.assertRaisesRegex(RuntimeError, "Disk serial mismatch.*expected.*observed"):
                    restore.check_serial(disk, "S4EWNG0M109916K")

    def test_native_serial_uses_resolved_device_number_and_refuses_non_devices(self):
        disk = Path("/dev/disk/by-id/fixture")
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(259, 4))), \
             patch.object(Path, "read_text", autospec=True, return_value="S4EWNG0M109916K     \n") as read:
            restore.check_serial(disk, "S4EWNG0M109916K")
            self.assertEqual(read.call_args.args[0], Path("/sys/dev/block/259:4/device/serial"))
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=stat.S_IFREG)), \
             patch.object(Path, "read_text") as read:
            with self.assertRaisesRegex(RuntimeError, "not a block device"):
                restore.check_serial(disk, "S4EWNG0M109916K")
            read.assert_not_called()
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(259, 4))), \
             patch.object(Path, "read_text", side_effect=FileNotFoundError("missing native identity")):
            with self.assertRaises(OSError): restore.check_serial(disk, "S4EWNG0M109916K")

    @unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
    def test_cold_syncthing_identity_and_sqlite_integrity_without_starting_service(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            config = home / ".config/syncthing"; config.mkdir(parents=True)
            index = home / ".local/state/syncthing/index-v2"; index.mkdir(parents=True)
            configuration = ET.Element("configuration")
            for name, folder_id in FOLDERS.items():
                (home / "sync" / name / ".stfolder").mkdir(parents=True)
                ET.SubElement(configuration, "folder", id=folder_id, path=f"/home/v/sync/{name}", type="sendreceive")
            ET.ElementTree(configuration).write(config / "config.xml")
            subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
                            "-nodes", "-keyout", str(config / "key.pem"), "-out", str(config / "cert.pem"),
                            "-subj", "/CN=synthetic-migration-test", "-days", "1"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (config / "key.pem").chmod(0o600)
            for name in ["main.db", *[f"folder.{n:04}.db" for n in range(1, 7)]]:
                database = sqlite3.connect(index / name)
                database.execute("create table fixture (state text)")
                database.commit(); database.close()
            database = sqlite3.connect(index / "main.db")
            database.execute("create table folders (folder_id text, database_name text)")
            database.executemany("insert into folders values (?, ?)", [
                (folder_id, f"folder.{n:04}.db") for n, folder_id in enumerate(FOLDERS.values(), 1)])
            database.commit(); database.close()
            before = {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()}
            report = check_syncthing(home)
            self.assertEqual(len(report["databases"]), 6)
            self.assertEqual(before, {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()})
            (index / "main.db").write_bytes(b"corrupted database")
            with self.assertRaises(RuntimeError): check_syncthing(home)

    def test_syncthing_folder_markers_ids_and_paths_are_mandatory(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            config = ET.Element("configuration")
            for name, folder_id in FOLDERS.items():
                (home / "sync" / name / ".stfolder").mkdir(parents=True)
                ET.SubElement(config, "folder", id=folder_id, path=f"/home/v/sync/{name}", type="sendreceive")
            check_folders(home, config)
            (home / "sync/music/.stfolder").rmdir()
            with self.assertRaises(RuntimeError): check_folders(home, config)
            (home / "sync/music/.stfolder").mkdir()
            config.find("folder").set("path", "/home/v/empty")
            with self.assertRaises(RuntimeError): check_folders(home, config)

    def test_efi_requires_correct_guid_and_real_loader_images(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); esp, variables = root / "esp", root / "vars"
            variables.mkdir()
            for name in ["EFI/systemd/systemd-bootx64.efi", "EFI/BOOT/BOOTX64.EFI", "EFI/nixos/kernel", "EFI/nixos/initrd"]:
                path = esp / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"MZsynthetic")
            (esp / "loader/entries").mkdir(parents=True)
            (esp / "loader/loader.conf").write_text("default nixos\n")
            (esp / "loader/entries/nixos.conf").write_text("linux /EFI/nixos/kernel\ninitrd /EFI/nixos/initrd\n")
            node = struct.pack("<BBHIQQ", 4, 1, 42, 1, 2048, 2097152)
            node += uuid.UUID("d1a46384-039f-42f2-9ccd-13ec17dd2250").bytes_le + bytes([2, 2])
            filename = "\\EFI\\systemd\\systemd-bootx64.efi\0".encode("utf-16le")
            node += struct.pack("<BBH", 4, 4, len(filename) + 4) + filename
            (variables / "Boot0004-fixture").write_bytes(bytes(4) + struct.pack("<IH", 1, len(node)) + "NixOS\0".encode("utf-16le") + node)
            self.assertEqual(check_efi(esp, variables), ["Boot0004"])
            (esp / "EFI/nixos/initrd").unlink()
            with self.assertRaises(RuntimeError): check_efi(esp, variables)

    def test_fresh_identity_detects_host_key_change_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "etc/ssh").mkdir(parents=True)
            (root / "etc/machine-id").write_text("a" * 32 + "\n")
            (root / "etc/shadow").write_text("root:$6$synthetic:1::::::\n")
            key = root / "etc/ssh/ssh_host_ed25519_key"; key.write_text("synthetic original")
            before = fresh_identity(root)
            key.write_text("synthetic changed")
            self.assertNotEqual(before, fresh_identity(root))
            before = fresh_identity(root)
            (root / "etc/shadow").write_text("root:!:1::::::\n")
            self.assertNotEqual(before, fresh_identity(root))

    def mounts(self):
        return [
            dict(target="/", uuid="live", options="rw", fstype="overlay", fsroot="/"),
            dict(target=str(restore.OLD), uuid=restore.OLD_UUID,
                 options="ro,rescue=nologreplay", fstype="btrfs", fsroot="/"),
            dict(target=str(restore.NEW), uuid=restore.NEW_UUID,
                 options="rw", fstype="btrfs", fsroot="/"),
        ]

    def test_correct_offline_mounts(self):
        restore.validate_mounts(self.mounts(), apply=True)

    def test_source_requires_read_only_rescue_nologreplay(self):
        for options in ["ro", "ro,rescue=usebackuproot", "rw,rescue=nologreplay"]:
            with self.subTest(options=options):
                mounts = self.mounts()
                mounts[1]["options"] = options
                with self.assertRaises(RuntimeError): restore.validate_mounts(mounts, apply=True)

    def test_rejects_live_source_writable_source_wrong_disk_and_nested_mount(self):
        for change in ["live", "writable", "wrong", "nested", "replay", "subvolume", "target-ro"]:
            with self.subTest(change=change):
                mounts = self.mounts()
                if change == "live": mounts[0]["uuid"] = restore.OLD_UUID
                if change == "writable": mounts[1]["options"] = "rw,rescue=nologreplay"
                if change == "wrong": mounts[2]["uuid"] = restore.OLD_UUID
                if change == "nested": mounts.append(dict(target=str(restore.OLD / "home/v/mount"), uuid="other", options="ro"))
                if change == "replay": mounts[1]["options"] = "ro"
                if change == "subvolume": mounts[1]["fsroot"] = "/home"
                if change == "target-ro": mounts[2]["options"] = "ro"
                with self.assertRaises(RuntimeError): restore.validate_mounts(mounts, apply=True)

    def test_shadow_replaces_only_v_and_never_accepts_locked_password(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, target = root / "old", root / "new"
            source.write_text("root:old-root:1::::::\nv:$6$synthetic:2::::::\n")
            target.write_text("root:new-root:3::::::\nv:!:4::::::\nservice:!:5::::::\n")
            target.chmod(0o640)
            restore.restore_password(source, target)
            self.assertEqual(target.read_text(), "root:new-root:3::::::\nv:$6$synthetic:2::::::\nservice:!:5::::::\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            source.write_text("v:!:2::::::\n")
            with self.assertRaises(RuntimeError): restore.restore_password(source, target)

    def test_real_rsync_metadata_resume_checksum_and_fresh_home_retention(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, home = root / "source", root / "home"
            source.mkdir(mode=0o700); home.mkdir()
            (home / "v").mkdir(); (home / "v/fresh").write_text("retain")
            (source / ".hidden").mkdir(mode=0o700)
            data = source / ".hidden/state"
            data.write_bytes(b"session\0data"); data.chmod(0o600)
            os.link(data, source / "hardlink")
            (source / "store-link").symlink_to("/nix/store/synthetic")
            os.setxattr(data, "user.phoenix-test", b"preserved")
            with (source / "sparse").open("wb") as f:
                f.seek(1024 * 1024); f.write(b"end")
            restore.copy_home(source, home)
            target = home / "v"
            self.assertEqual((home / restore.FRESH_HOME / "fresh").read_text(), "retain")
            self.assertEqual((target / ".hidden/state").read_bytes(), data.read_bytes())
            self.assertEqual((target / "store-link").readlink(), Path("/nix/store/synthetic"))
            self.assertEqual((target / "hardlink").stat().st_ino, (target / ".hidden/state").stat().st_ino)
            self.assertEqual(os.getxattr(target / "hardlink", "user.phoenix-test"), b"preserved")
            self.assertEqual((target / ".hidden/state").stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)
            self.assertEqual(target.stat().st_uid, source.stat().st_uid)
            self.assertLess((target / "sparse").stat().st_blocks * 512, (target / "sparse").stat().st_size)
            # Checksum validation catches same-size/same-mtime corruption.
            corrupt = target / ".hidden/state"
            st = corrupt.stat(); corrupt.write_bytes(b"broken!\0data")
            os.utime(corrupt, ns=(st.st_atime_ns, st.st_mtime_ns))
            with self.assertRaises(RuntimeError): restore.verify_copy(source, target)
            with self.assertRaises(RuntimeError): restore.copy_home(source, home)

    def test_service_state_replaces_without_merging_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = Path(d) / "old", Path(d) / "new"
            relative = "var/lib/navidrome"
            (old / relative).mkdir(parents=True)
            (new / relative).mkdir(parents=True)
            (old / relative / "db").write_text("old account")
            (new / relative / "fresh-only").write_text("fresh account")
            with patch.object(restore, "OLD", old), patch.object(restore, "NEW", new):
                restore.restore_directory(relative)
                self.assertEqual((new / relative / "db").read_text(), "old account")
                self.assertFalse((new / relative / "fresh-only").exists())
                self.assertEqual((new / "root/phoenix-migration-before" / relative / "fresh-only").read_text(), "fresh account")
                restore.restore_directory(relative)
                (new / relative / "db").write_text("changed after copy")
                with self.assertRaises(RuntimeError): restore.restore_directory(relative)

    def test_rejects_symlink_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "elsewhere").mkdir()
            (root / "link").symlink_to(root / "elsewhere", target_is_directory=True)
            with self.assertRaises(RuntimeError): restore.plain(root / "link/child")

    @unittest.skipUnless(shutil.which("setfacl") and shutil.which("getfacl"), "ACL tools unavailable")
    def test_real_rsync_access_and_default_acls(self):
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d) / "source", Path(d) / "target"
            source.mkdir(); target.mkdir()
            (source / "file").write_text("private")
            subprocess.run(["setfacl", "-m", f"u:{os.getuid()}:r--", str(source / "file")], check=True)
            subprocess.run(["setfacl", "-m", f"d:u:{os.getuid()}:r-x", str(source)], check=True)
            restore.run(*restore.RSYNC, str(source) + "/", str(target) + "/")
            for relative in ["", "file"]:
                get = lambda p: subprocess.check_output(["getfacl", "-cn", str(p)], text=True)
                self.assertEqual(get(source / relative), get(target / relative))


if __name__ == "__main__":
    unittest.main()
