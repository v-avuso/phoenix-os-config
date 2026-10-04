#!/usr/bin/env python3
"""ZIP action fixtures; all sample files live in temporary directories."""

import importlib.util
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "home/thunar-archive.py"
spec = importlib.util.spec_from_file_location("thunar_archive", SCRIPT)
thunar_archive = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(thunar_archive)


class CreateZipTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="phoenix-zip-test-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_archives_multiple_items_with_literal_names_and_directory_contents(self):
        strange = self.root / "- notes [draft].txt"
        strange.write_text("selected file", encoding="utf-8")
        folder = self.root / "folder with spaces"
        folder.mkdir()
        (folder / "nested.txt").write_text("nested file", encoding="utf-8")

        success, message = thunar_archive.create_archive([str(strange), str(folder)])

        self.assertTrue(success, message)
        output = self.root / "Archive.zip"
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist(), [
                "- notes [draft].txt",
                "folder with spaces/",
                "folder with spaces/nested.txt",
            ])
            self.assertEqual(archive.read("- notes [draft].txt"), b"selected file")
            self.assertEqual(archive.read("folder with spaces/nested.txt"), b"nested file")
        self.assertEqual(strange.read_text(encoding="utf-8"), "selected file")

    def test_single_item_name_and_collisions_preserve_existing_archive(self):
        source = self.root / "photo sample.png"
        source.write_bytes(b"original")
        existing = self.root / "photo sample.zip"
        existing.write_bytes(b"keep this")

        success, message = thunar_archive.create_archive([str(source)])

        self.assertTrue(success, message)
        self.assertEqual(existing.read_bytes(), b"keep this")
        with zipfile.ZipFile(self.root / "photo sample.2.zip") as archive:
            self.assertEqual(archive.read(source.name), b"original")

    def test_empty_and_missing_inputs_report_failure(self):
        self.assertFalse(thunar_archive.create_archive([])[0])
        self.assertFalse(thunar_archive.create_archive([str(self.root / "missing")])[0])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_symlinks_are_stored_as_links_without_reading_their_targets(self):
        outside = self.root.parent / f"{self.root.name}-outside.txt"
        outside.write_bytes(b"private target contents")
        file_link = self.root / "link to outside.txt"
        file_link.symlink_to(outside)
        folder = self.root / "folder"
        folder.mkdir()
        folder_link = self.root / "folder link"
        folder_link.symlink_to(folder, target_is_directory=True)

        success, message = thunar_archive.create_archive([str(file_link), str(folder_link)])

        self.assertTrue(success, message)
        with zipfile.ZipFile(self.root / "Archive.zip") as archive:
            for name, target in ((file_link.name, str(outside)), (folder_link.name, str(folder))):
                info = archive.getinfo(name)
                self.assertTrue(stat.S_ISLNK(info.external_attr >> 16))
                self.assertEqual(archive.read(name), os.fsencode(target))
            self.assertNotIn(b"private target contents", b"".join(archive.read(name) for name in archive.namelist()))
        outside.unlink()

    def test_overlapping_parent_and_child_selections_have_no_duplicates_or_temp_file(self):
        parent = self.root / "selected folder"
        parent.mkdir()
        child = parent / "child.txt"
        child.write_text("child", encoding="utf-8")

        success, message = thunar_archive.create_archive([str(child), str(parent)])

        self.assertTrue(success, message)
        with zipfile.ZipFile(self.root / "selected folder.zip") as archive:
            self.assertEqual(archive.namelist(), ["selected folder/", "selected folder/child.txt"])
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            self.assertFalse(any("phoenix-zip" in name for name in archive.namelist()))

    def test_fifo_is_rejected_without_opening_it(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)

        success, message = thunar_archive.create_archive([str(fifo)])

        self.assertFalse(success)
        self.assertIn("unsupported special file", message)
        self.assertEqual(list(self.root.iterdir()), [fifo])

    def test_pre_zip_epoch_timestamps_are_clamped(self):
        old_file = self.root / "old.txt"
        old_file.write_text("old", encoding="utf-8")
        os.utime(old_file, (0, 0))

        success, message = thunar_archive.create_archive([str(old_file)])

        self.assertTrue(success, message)
        with zipfile.ZipFile(self.root / "old.zip") as archive:
            self.assertEqual(archive.read(old_file.name), b"old")


if __name__ == "__main__":
    unittest.main(verbosity=2)
