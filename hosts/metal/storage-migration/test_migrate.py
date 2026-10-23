"""Disposable orchestration checks; every native disk/install operation is mocked."""
import base64
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import migrate

spec = importlib.util.spec_from_file_location("export_launcher", Path(__file__).with_name("export-launcher.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class Workflow(unittest.TestCase):
    def exercise(self, fail=None, decline=None):
        events = []
        driver = migrate.Migration(Path("/reviewed-source"))
        def step(name):
            def call(*args):
                events.append(name)
                if fail == name:
                    raise RuntimeError("simulated failure")
            return call
        def approval(word, explanation):
            events.append(word)
            if decline == word:
                raise RuntimeError("operator declined")
        with contextlib.ExitStack() as stack:
            for name in ["prepare", "restore", "install", "verify", "cleanup"]:
                stack.enter_context(patch.object(driver, name, side_effect=step(name)))
            stack.enter_context(patch.object(migrate, "approve", side_effect=approval))
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            if fail or decline:
                with self.assertRaises(RuntimeError): driver.execute()
                self.assertNotIn("SUCCESS", output.getvalue())
            else:
                driver.execute()
                self.assertIn("SUCCESS", output.getvalue())
        return events

    def test_success_requires_both_approvals_and_verification_before_cleanup(self):
        self.assertEqual(self.exercise(), ["prepare", "RESTORE", "restore", "INSTALL", "install", "verify", "cleanup"])

    def test_failures_and_declined_approvals_never_continue(self):
        for stage, expected in [
            ("prepare", ["prepare", "cleanup"]),
            ("restore", ["prepare", "RESTORE", "restore", "cleanup"]),
            ("install", ["prepare", "RESTORE", "restore", "INSTALL", "install", "cleanup"]),
            ("verify", ["prepare", "RESTORE", "restore", "INSTALL", "install", "verify", "cleanup"]),
            ("cleanup", ["prepare", "RESTORE", "restore", "INSTALL", "install", "verify", "cleanup"]),
        ]:
            with self.subTest(stage=stage): self.assertEqual(self.exercise(fail=stage), expected)
        self.assertEqual(self.exercise(decline="RESTORE"), ["prepare", "RESTORE", "cleanup"])
        self.assertEqual(self.exercise(decline="INSTALL"), ["prepare", "RESTORE", "restore", "INSTALL", "cleanup"])

    def test_approval_requires_exact_word(self):
        with patch("builtins.input", return_value="yes"), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError): migrate.approve("RESTORE", "plan")

    def test_restore_opens_only_target_for_writing_and_calls_original_checks(self):
        driver = migrate.Migration(Path("/reviewed"), network=True)
        calls = []
        with patch.object(driver, "unmount", side_effect=lambda *a: calls.append(("unmount", *a))), \
             patch.object(driver, "mount", side_effect=lambda *a: calls.append(("mount", *a))), \
             patch.object(migrate.r, "run", side_effect=lambda *a: calls.append(a)):
            driver.restore()
        self.assertEqual(calls[0], ("unmount", migrate.r.NEW))
        self.assertEqual(calls[1][1:3], (migrate.r.ROOT_MAP, migrate.r.NEW))
        self.assertIn("--apply", calls[2])
        self.assertIn("RESTORE-TO-S7DSNJ0Y411212Z", calls[2])
        self.assertIn("--network", calls[2])

    def test_installer_is_pinned_to_new_root_and_target_without_password_reset(self):
        driver = migrate.Migration(Path("/reviewed"))
        calls = []
        with patch.object(driver, "mount"), patch.object(driver, "unmount"), \
             patch.object(migrate.r, "run", side_effect=lambda *a: calls.append(a)):
            driver.install()
        installer = next(c for c in calls if c[0] == "nixos-install")
        self.assertEqual(installer[1:5], ("--root", migrate.r.NEW, "--flake", "/reviewed#metal-4tb"))
        self.assertIn("--no-root-passwd", installer)
        self.assertIn("--no-write-lock-file", installer)
        self.assertFalse(any(str(migrate.r.OLD) in str(c) for c in calls))

    def test_cleanup_closes_only_owned_resources_in_reverse_order(self):
        driver = migrate.Migration(Path("/reviewed"))
        driver.mounts = [migrate.r.OLD, migrate.r.NEW, migrate.r.NEW / "home"]
        driver.mappings = [migrate.r.ROOT_MAP.name, migrate.r.SWAP_MAP.name]
        calls = []
        with patch.object(migrate.r, "run", side_effect=lambda *a: calls.append(a)):
            driver.cleanup()
        self.assertEqual(calls, [("umount", migrate.r.NEW / "home"), ("umount", migrate.r.NEW),
                                 ("umount", migrate.r.OLD), ("cryptsetup", "close", migrate.r.SWAP_MAP.name),
                                 ("cryptsetup", "close", migrate.r.ROOT_MAP.name)])
        self.assertEqual(driver.mounts, [])
        self.assertEqual(driver.mappings, [])

    def test_cleanup_failure_is_no_go(self):
        driver = migrate.Migration(Path("/reviewed"))
        driver.mounts = [migrate.r.OLD]
        with patch.object(migrate.r, "run", side_effect=OSError("busy")):
            with self.assertRaisesRegex(RuntimeError, "Cleanup incomplete"): driver.cleanup()
        self.assertEqual(driver.mounts, [migrate.r.OLD])

    def test_native_preflight_failure_prevents_unlock_and_mount(self):
        driver = migrate.Migration(Path("/reviewed"))
        with patch.object(migrate.os, "geteuid", return_value=1000), patch.object(migrate.r, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "host root"): driver.prepare()
        run.assert_not_called()

    def test_native_plan_keeps_source_and_esp_read_only_and_never_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old, new, esp = (root / name for name in ["old", "new", "esp"])
            source = root / "source"; source.mkdir()
            (root / "release.json").write_text(json.dumps({"commit": "a" * 40}))
            driver = migrate.Migration(source)
            calls = []
            def capture(*args):
                if args[0] == "findmnt": return "tmpfs"
                if args[0] == "lsblk" and "--json" in args:
                    return json.dumps({"blockdevices": [{"mountpoints": [None], "children": [{"mountpoints": [None]}]}]})
                if args[:3] == ("lsblk", "-dnro", "SERIAL"):
                    # Exact raw sysfs-fallback representation that broke the old gate.
                    serial = "S4EWNG0M109916K" if args[3] == migrate.r.OLD_DISK else "S7DSNJ0Y411212Z"
                    return serial + "\\x20" * 5
                if args[:2] == ("blockdev", "--getsize64"):
                    return str(10**12 if args[2] == migrate.r.OLD_DISK else 4 * 10**12)
                raise AssertionError(args)
            def preflight(apply):
                self.assertFalse(apply)
                (old / "var/lib/navidrome").mkdir(parents=True)
                return {"fixture": True}, {"identity": True}
            read_text = Path.read_text
            is_dir = Path.is_dir
            def read(path, *args, **kwargs):
                if str(path) == "/proc/self/uid_map": return "0 0 4294967295\n"
                if str(path) == "/proc/swaps": return "Filename Type Size Used Priority\n"
                return read_text(path, *args, **kwargs)
            with patch.object(migrate.r, "OLD", old), patch.object(migrate.r, "NEW", new), \
                 patch.object(migrate.r, "ESP", esp), patch.object(migrate.r, "ROOT_MAP", root / "root-map"), \
                 patch.object(migrate.r, "SWAP_MAP", root / "swap-map"), \
                 patch.object(migrate.os, "geteuid", return_value=0), patch.object(migrate.sys.stdin, "isatty", return_value=True), \
                 patch.object(migrate.shutil, "which", return_value="/fixture"), patch.object(migrate, "firmware", return_value={}), \
                 patch.object(migrate.r, "capture", side_effect=capture), patch.object(migrate.r, "signature"), \
                 patch.object(migrate.r, "check_serial") as serial_check, \
                 patch.object(migrate.r, "preflight", side_effect=preflight), \
                 patch.object(migrate.r, "run", side_effect=lambda *a: calls.append(a)), \
                 patch.object(migrate.Path, "exists", autospec=True, side_effect=lambda p: str(p) in ["/etc/NIXOS"]), \
                 patch.object(migrate.Path, "read_text", autospec=True, side_effect=read), \
                 patch.object(migrate.Path, "is_dir", autospec=True, side_effect=lambda p: str(p) == "/sys/firmware/efi/efivars" or is_dir(p)), \
                 contextlib.redirect_stdout(io.StringIO()):
                driver.prepare()
            self.assertEqual(serial_check.call_args_list, [
                unittest.mock.call(migrate.r.OLD_DISK, "S4EWNG0M109916K"),
                unittest.mock.call(migrate.r.NEW_DISK, "S7DSNJ0Y411212Z"),
            ])
            old_mount = next(c for c in calls if c[0] == "mount" and c[-1] == old)
            self.assertIn("ro,nologreplay,subvolid=5", old_mount)
            self.assertEqual([c[0] for c in calls[:4]], ["blockdev"] * 4)
            self.assertTrue(all(c[1] == "--setro" for c in calls[:4]))
            self.assertFalse(any(c[0] in ["rsync", "nixos-install"] for c in calls))
            self.assertIn(("mount", "-o", "ro", str(migrate.r.NEW_DISK) + "-part1", esp), calls)
            swap_open = next(c for c in calls if c[0] == "cryptsetup" and c[-1] == "swap-map")
            self.assertIn("--readonly", swap_open)

    def test_portable_bundle_contains_entire_committed_source_and_no_untracked_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "repo"; source.mkdir()
            (source / "flake.lock").write_text(json.dumps({"nodes": {"root": {"inputs": {"nixpkgs": "nixpkgs"}},
                "nixpkgs": {"locked": {"rev": "abc123"}}}}))
            (source / "migrate.py").write_text("reviewed fixture")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "flake.lock", "migrate.py"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost",
                            "commit", "-qm", "fixture"], check=True)
            (source / "private.txt").write_text("must not leak")
            (source / "migrate.py").write_text("unreviewed modification")
            launcher = root / "phoenix-migrate"
            with contextlib.redirect_stdout(io.StringIO()): exporter.export(source, launcher)
            subprocess.run(["bash", "-n", str(launcher)], check=True)
            help_result = subprocess.run(["bash", str(launcher), "--help"], check=True, capture_output=True, text=True)
            self.assertIn("sudo bash phoenix-migrate", help_result.stdout)
            header, encoded = launcher.read_text().split("\n__PHOENIX_PAYLOAD__\n")
            payload = base64.decodebytes(encoded.encode())
            self.assertIn(hashlib.sha256(payload).hexdigest(), header)
            self.assertIn("nixpkgs/archive/abc123.tar.gz", header)
            with tarfile.open(fileobj=io.BytesIO(gzip.decompress(payload))) as archive:
                self.assertEqual(archive.extractfile("source/migrate.py").read(), b"reviewed fixture")
                self.assertNotIn("source/private.txt", archive.getnames())
                self.assertEqual(len(json.load(archive.extractfile("release.json"))["commit"]), 40)


if __name__ == "__main__":
    unittest.main()
