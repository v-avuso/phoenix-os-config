"""Isolated lifecycle fixtures; never reads or changes live settings."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    "mutable_json_settings", Path(__file__).resolve().parents[1] / "home/mutable-json-settings.py"
)
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text('{"general":{"idle":{"timeouts":[]}}}\n')
        self.target = self.root / "home/.config/caelestia/shell.json"

    def deploy(self, mode="reassert"):
        settings.deploy(self.baseline, self.target, mode)

    def test_fresh_boot_initializes_writable_user_file(self):
        self.deploy("preserve")
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.stat().st_uid, os.getuid())
        self.assertTrue(self.target.stat().st_mode & 0o200)

    def test_boot_preserves_experiments_and_switch_reasserts_whole_baseline(self):
        self.deploy()
        self.target.write_text('{"experiment":true}')
        self.deploy("preserve")
        self.assertEqual(json.loads(self.target.read_text()), {"experiment": True})
        self.deploy()
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_legacy_symlink_is_replaced_even_at_boot_without_changing_source(self):
        self.target.parent.mkdir(parents=True)
        legacy = self.root / "legacy.json"
        legacy.write_text('{"legacy":true}')
        legacy.chmod(0o444)
        self.target.symlink_to(legacy)
        self.deploy("preserve")
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(legacy.read_text(), '{"legacy":true}')
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_dangling_symlink_is_initialized(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.root / "missing")
        self.deploy("preserve")
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_read_only_file_remains_editable_without_losing_boot_experiment(self):
        self.deploy()
        self.target.write_text('{"experiment":true}')
        self.target.chmod(0o444)
        self.deploy("preserve")
        self.assertTrue(self.target.stat().st_mode & 0o200)
        self.assertEqual(json.loads(self.target.read_text()), {"experiment": True})
        self.deploy()
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_repeated_semantically_equal_activation_does_not_replace_file(self):
        self.deploy()
        self.target.write_text('{"general": {"idle": {"timeouts": []}}}')
        before = self.target.stat()
        self.deploy()
        self.deploy("preserve")
        after = self.target.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_reassert_repairs_invalid_runtime_json(self):
        self.deploy()
        self.target.write_text("incomplete JSON")
        self.deploy("preserve")
        self.assertEqual(self.target.read_text(), "incomplete JSON")
        self.deploy()
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_invalid_path_is_rejected_without_removal(self):
        self.target.mkdir(parents=True)
        for mode in ("preserve", "reassert"):
            with self.assertRaises(ValueError):
                self.deploy(mode)
        self.assertTrue(self.target.is_dir())

    def test_special_path_is_rejected_without_opening_it(self):
        self.target.parent.mkdir(parents=True)
        os.mkfifo(self.target)
        with self.assertRaises(ValueError):
            self.deploy()

    def test_failed_atomic_replacement_preserves_experiment_and_cleans_temporary(self):
        self.deploy()
        self.target.write_text('{"experiment":true}')
        with patch.object(settings.os, "replace", side_effect=OSError("simulated rename failure")):
            with self.assertRaises(OSError):
                self.deploy()
        self.assertEqual(self.target.read_text(), '{"experiment":true}')
        self.assertEqual(list(self.target.parent.glob(".shell.json.*")), [])

    def test_invalid_baseline_fails_before_changing_runtime(self):
        self.deploy()
        self.baseline.write_text("[]")
        with self.assertRaises(ValueError):
            self.deploy()
        self.assertEqual(json.loads(self.target.read_text()), {"general": {"idle": {"timeouts": []}}})
        self.assertEqual(list(self.target.parent.glob(".shell.json.*")), [])

    def test_array_baseline_reasserts_keybindings(self):
        self.baseline.write_text('[{"key":"ctrl+k","command":"example"}]')
        self.target = self.root / "home/.config/VSCodium/User/keybindings.json"
        settings.deploy(self.baseline, self.target, "preserve", "array")
        self.target.write_text('[{"key":"ctrl+j","command":"experiment"}]')
        settings.deploy(self.baseline, self.target, "preserve", "array")
        self.assertEqual(json.loads(self.target.read_text())[0]["command"], "experiment")
        settings.deploy(self.baseline, self.target, "reassert", "array")
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())

    def test_array_expected_type_rejects_object_before_creating_target(self):
        with self.assertRaises(ValueError):
            settings.deploy(self.baseline, self.target, "preserve", "array")
        self.assertFalse(self.target.exists())

    def test_reassert_distinguishes_boolean_from_number_in_objects_and_arrays(self):
        for expected_type, baseline, experiment in (
            ("object", '{"enabled":true}', '{"enabled":1}'),
            ("array", '[{"enabled":false}]', '[{"enabled":0}]'),
        ):
            self.baseline.write_text(baseline)
            settings.deploy(self.baseline, self.target, "reassert", expected_type)
            self.target.write_text(experiment)
            settings.deploy(self.baseline, self.target, "reassert", expected_type)
            self.assertEqual(self.target.read_text(), baseline)

    def test_vscodium_jsonc_experiment_and_unrelated_state_are_preserved(self):
        self.target = self.root / "home/.config/VSCodium/User/settings.json"
        self.deploy()
        experiment = '{\n // live preference\n "editor.fontSize": 18,\n}'
        self.target.write_text(experiment)
        other = self.target.parent / "globalStorage/storage.json"
        other.parent.mkdir()
        other.write_text('{"session":"preserve"}')
        legacy = self.root / "home/.config/Code/User/settings.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"old":"unrelated"}')
        self.deploy("preserve")
        self.assertEqual(self.target.read_text(), experiment)
        self.deploy()
        self.assertEqual(self.target.read_bytes(), self.baseline.read_bytes())
        self.assertEqual(other.read_text(), '{"session":"preserve"}')
        self.assertEqual(legacy.read_text(), '{"old":"unrelated"}')


if __name__ == "__main__":
    unittest.main()
