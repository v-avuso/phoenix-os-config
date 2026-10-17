"""Offline fixed backend integration boundaries; no Podman/host service calls."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("shutdown_backend", pathlib.Path(__file__).with_name("backend.py"))
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.images = {role: {"archive": "/nix/store/fixed-" + role + ".tar.gz", "id": char * 64,
                              "sha256": char * 64, "binarySha256": char * 64}
                       for role, char in (("runtime", "a"), ("supervisor", "b"))}
        self.config = {"podman": "/nix/store/fixed-podman/bin/podman", "socket": "/run/user/1000/phoenix-openshell-podman.sock",
                       "home": "/home/fixture", "runtimeDirectory": "/run/user/1000"}
        self.commands = []
        readiness = patch.object(backend, "wait_for_socket")
        readiness.start()
        self.addCleanup(readiness.stop)

    def runner(self, argv, **kwargs):
        self.commands.append((argv, kwargs))
        if "exists" in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"")
        value = argv[-1].removeprefix("sha256:") if "inspect" in argv else "loaded"
        return subprocess.CompletedProcess(argv, 0, value.encode(), b"")

    def test_fixed_remote_store_load_then_exact_id_and_clean_environment(self):
        with patch.object(backend, "sha256_file", side_effect=lambda p: self.images["runtime" if "runtime" in p else "supervisor"]["sha256"]):
            backend.import_images(self.config, self.images, self.runner)
        self.assertEqual(len(self.commands), 6)
        for argv, kwargs in self.commands:
            self.assertEqual(argv[:4], [self.config["podman"], "--remote", "--url", "unix:" + self.config["socket"]])
            self.assertGreater(kwargs["timeout"], 0)
            self.assertLessEqual(kwargs["timeout"], 20)
            self.assertEqual(kwargs["env"], {"HOME": "/home/fixture", "XDG_RUNTIME_DIR": "/run/user/1000"})
        self.assertEqual(["load" in a for a, _ in self.commands], [False, True, False, False, True, False])

    def test_present_ids_skip_hash_and_load_but_verify_identity(self):
        def present(argv, **kwargs):
            self.commands.append(argv)
            return subprocess.CompletedProcess(argv, 0, argv[-1].removeprefix("sha256:").encode() if "inspect" in argv else b"", b"")
        with patch.object(backend, "sha256_file") as hash_file:
            backend.import_images(self.config, self.images, present)
        hash_file.assert_not_called()
        self.assertFalse(any("load" in command for command in self.commands))
        self.assertEqual(len(self.commands), 4)

    def test_storage_error_does_not_attempt_import(self):
        def fail(argv, **kwargs):
            self.commands.append(argv)
            return subprocess.CompletedProcess(argv, 125, b"", b"PRIVATE_CANARY")
        with patch.object(backend, "sha256_file") as hash_file:
            with self.assertRaisesRegex(backend.BackendError, "^image-import-failed$"):
                backend.import_images(self.config, self.images, fail)
        hash_file.assert_not_called()
        self.assertEqual(len(self.commands), 1)

    def test_timeout_is_static_and_stops(self):
        def timeout(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], stderr=b"PRIVATE_CANARY")
        with self.assertRaisesRegex(backend.BackendError, "^image-import-timeout$"):
            backend.import_images(self.config, self.images, timeout)

    def test_failed_load_stops_without_leaking_stderr(self):
        def fail(argv, **kwargs):
            self.commands.append(argv)
            return subprocess.CompletedProcess(argv, 1 if "exists" in argv else 125, b"PRIVATE_CANARY", b"PRIVATE_CANARY")
        with patch.object(backend, "sha256_file", return_value="a" * 64):
            with self.assertRaisesRegex(backend.BackendError, "^image-import-failed$"):
                backend.import_images(self.config, self.images, fail)
        self.assertEqual(len(self.commands), 2)

    def test_mismatched_loaded_id_is_failure(self):
        def wrong(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, b"c" * 64, b"")
        with patch.object(backend, "sha256_file", return_value="a" * 64):
            with self.assertRaisesRegex(backend.BackendError, "^image-id-mismatch$"):
                backend.import_images(self.config, self.images, wrong)

    def test_archive_change_never_loads(self):
        with patch.object(backend, "sha256_file", return_value="c" * 64):
            with self.assertRaisesRegex(backend.BackendError, "^image-archive-mismatch$"):
                backend.import_images(self.config, self.images, self.runner)
        self.assertEqual(len(self.commands), 1)
        self.assertIn("exists", self.commands[0][0])

    def test_gateway_binds_exact_ids_and_rejects_incomplete_template(self):
        template = 'sandbox_runtime_image = "@PHOENIX_RUNTIME_IMAGE@"\nsupervisor_image = "@PHOENIX_SUPERVISOR_IMAGE@"\n'
        result = backend.configure_gateway(template, self.images)
        self.assertIn('"sha256:' + "a" * 64 + '"', result)
        self.assertIn('"sha256:' + "b" * 64 + '"', result)
        with self.assertRaisesRegex(backend.BackendError, "gateway-template-invalid"):
            backend.configure_gateway(template.replace("@PHOENIX_RUNTIME_IMAGE@", "changed"), self.images)


class ReadinessTests(unittest.TestCase):
    def test_only_missing_or_refused_socket_retries(self):
        with patch.object(backend.socket, "socket") as constructor, patch.object(backend.time, "sleep"):
            peer = constructor.return_value.__enter__.return_value
            peer.connect.side_effect = [FileNotFoundError(), ConnectionRefusedError(), None]
            backend.wait_for_socket("/fixed/private.sock", backend.time.monotonic() + 1)
            self.assertEqual(peer.connect.call_count, 3)

    def test_permission_error_is_not_retried(self):
        with patch.object(backend.socket, "socket") as constructor:
            peer = constructor.return_value.__enter__.return_value
            peer.connect.side_effect = PermissionError()
            with self.assertRaisesRegex(backend.BackendError, "^image-api-unavailable$"):
                backend.wait_for_socket("/fixed/private.sock", backend.time.monotonic() + 1)
            self.assertEqual(peer.connect.call_count, 1)

    def test_missing_socket_cannot_reset_deadline(self):
        with patch.object(backend.socket, "socket") as constructor, patch.object(backend.time, "sleep"), \
             patch.object(backend.time, "monotonic", side_effect=[0, 21]):
            constructor.return_value.__enter__.return_value.connect.side_effect = FileNotFoundError()
            with self.assertRaisesRegex(backend.BackendError, "^image-import-timeout$"):
                backend.wait_for_socket("/fixed/private.sock", 20)


if __name__ == "__main__":
    unittest.main()
