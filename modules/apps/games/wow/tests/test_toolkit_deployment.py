"""Filesystem acceptance without touching the real game or Nix store."""
import importlib.util
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "deploy_toolkit", Path(__file__).resolve().parents[1] / "deploy-toolkit.py"
)
DEPLOY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPLOY)


class ToolkitDeploymentTests(unittest.TestCase):
    def test_missing_destination_is_not_created(self):
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / "missing" / "AddOns"
            DEPLOY.deploy(missing, "/invalid/source")
            self.assertFalse(missing.parent.exists())

    def test_collisions_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / DEPLOY.NAME
            for kind in ("file", "directory", "link", "dangling"):
                if kind == "file":
                    target.write_text("user content")
                elif kind == "directory":
                    target.mkdir()
                else:
                    target.symlink_to(root if kind == "link" else "/missing/user/addon")
                before = target.lstat()
                DEPLOY.deploy(root, "/invalid/source")
                DEPLOY.deploy(root)
                self.assertEqual(before, target.lstat())
                if kind == "directory":
                    target.rmdir()
                else:
                    target.unlink()

    def test_install_update_idempotence_remove_and_unrelated_data(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            addons = root / "AddOns"
            addons.mkdir()
            third_party = addons / "OPie"
            third_party.mkdir()
            original = third_party / "original.lua"
            original.write_bytes(b"untouched\x00")
            sources = []
            for version in ("old", "new"):
                source = root / version / DEPLOY.NAME
                source.mkdir(parents=True)
                (source / (DEPLOY.NAME + ".toc")).write_text("fixture")
                sources.append(source)
            with patch.object(DEPLOY, "OWNED", re.compile("|".join(map(lambda p: re.escape(str(p)), sources)))):
                target = addons / DEPLOY.NAME
                DEPLOY.deploy(addons, sources[0])
                self.assertEqual(target.resolve(), sources[0])
                inode = target.lstat().st_ino
                DEPLOY.deploy(addons, sources[0])
                self.assertEqual(target.lstat().st_ino, inode)
                DEPLOY.deploy(addons, sources[1])
                self.assertEqual(target.resolve(), sources[1])
                with self.assertRaises(ValueError):
                    DEPLOY.deploy(addons, root / "invalid")
                self.assertEqual(target.resolve(), sources[1])
                DEPLOY.deploy(addons)
                self.assertFalse(os.path.lexists(target))
                DEPLOY.deploy(addons)
            self.assertEqual(original.read_bytes(), b"untouched\x00")
            self.assertEqual(list(addons.iterdir()), [third_party])

    def test_stale_owned_link_is_removed(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / DEPLOY.NAME
            target.symlink_to("/nix/store/" + "a" * 32 + "-phoenix-wow-toolkit/PhoenixWoWToolkit")
            DEPLOY.deploy(root)
            self.assertFalse(os.path.lexists(target))


if __name__ == "__main__":
    unittest.main()
