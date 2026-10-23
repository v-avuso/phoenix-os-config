#!/usr/bin/env python3
"""Source-format security fixtures; disposable trees, no deployment or network."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_manifest', OWNER / 'source-manifest.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class SourceTests(unittest.TestCase):
    def manifest(self):
        files = {'flake.nix': '{}', 'flake.lock': '{}', 'package/template/lib.typ': 'canonical',
                 'package/lib.typ': 'template/lib.typ', 'collection/adapter.typ': '../package/template/lib.typ'}
        modes = {name: ('120000' if name in {'package/lib.typ', 'collection/adapter.typ'} else '100644')
                 for name in files}
        return files, modes

    def test_links_round_trip_without_dereferencing_and_retain_modes(self):
        files, modes = self.manifest()
        modes['package/template/lib.typ'] = '100755'
        with tempfile.TemporaryDirectory() as directory:
            source.materialize(Path(directory), files, modes)
            self.assertEqual(source.read_tree(Path(directory), 4096), (files, modes))
            self.assertEqual(os.readlink(Path(directory) / 'package/lib.typ'), 'template/lib.typ')
            self.assertEqual((Path(directory) / 'collection/adapter.typ').read_text(), 'canonical')

    def test_controller_umask_keeps_source_readable_to_unprivileged_builder(self):
        files, modes = self.manifest()
        with tempfile.TemporaryDirectory() as directory:
            previous = os.umask(0o077)
            try:
                source.materialize(Path(directory), files, modes)
            finally:
                os.umask(previous)
            self.assertEqual((Path(directory) / 'package/template').stat().st_mode & 0o777, 0o755)
            self.assertEqual((Path(directory) / 'package/template/lib.typ').stat().st_mode & 0o777, 0o644)

    def test_unsafe_links_and_submodules_are_rejected_before_writing(self):
        for target in ['/etc/passwd', '../../outside', 'missing', 'template', 'lib.typ',
                       '../collection/adapter.typ', 'template/lib.typ/../lib.typ', './template/lib.typ',
                       'template//lib.typ', 'template/lib.typ\n', '']:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                files, modes = self.manifest()
                files['package/lib.typ'] = target
                with self.assertRaises(ValueError):
                    source.materialize(Path(directory), files, modes)
                self.assertEqual(list(Path(directory).iterdir()), [])
        files, modes = self.manifest()
        for mode in ['160000', '040000', '100600']:
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                source.validate(files, dict(modes, **{'package/lib.typ': mode}))

    def test_file_directory_collisions_and_linked_flake_files_are_rejected(self):
        files, modes = self.manifest()
        files['collection/adapter.typ/child'] = 'cannot write through link'
        modes['collection/adapter.typ/child'] = '100644'
        with self.assertRaises(ValueError):
            source.validate(files, modes)
        files, modes = self.manifest()
        files['flake.nix'] = 'package/template/lib.typ'; modes['flake.nix'] = '120000'
        with self.assertRaises(ValueError):
            source.validate(files, modes)

    def test_link_target_must_be_tracked_in_working_snapshot(self):
        files, modes = self.manifest()
        with self.assertRaisesRegex(ValueError, 'tracked'):
            source.validate(files, modes, tracked={'flake.nix', 'flake.lock', 'package/lib.typ', 'collection/adapter.typ'})

    def test_snapshot_reads_reject_parent_redirection_and_special_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir(); (root / 'real/file').write_text('private')
            (root / 'redirect').symlink_to('real', target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                source.read_entry(root, 'redirect/file', 4096)
            os.mkfifo(root / 'fifo')
            with self.assertRaises(ValueError):
                source.read_entry(root, 'fifo', 4096)

    def test_retarget_during_read_is_rejected_without_following_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'link').symlink_to('safe')
            original = os.readlink
            def retarget(path, **kwargs):
                value = original(path, **kwargs)
                (root / 'link').unlink(); (root / 'link').symlink_to('/etc/passwd')
                return value
            with mock.patch.object(source.os, 'readlink', side_effect=retarget), \
                 self.assertRaisesRegex(ValueError, 'changed'):
                source.read_entry(root, 'link', 4096)

    def test_regular_file_mutation_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'file').write_text('before')
            original = os.read
            changed = False
            def mutate(fd, size):
                nonlocal changed
                data = original(fd, size)
                if not changed:
                    changed = True
                    (root / 'file').write_text('changed')
                return data
            with mock.patch.object(source.os, 'read', side_effect=mutate), \
                 self.assertRaisesRegex(ValueError, 'changed'):
                source.read_entry(root, 'file', 4096)

    def test_parent_replacement_cannot_redirect_an_open_directory_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'; root.mkdir()
            (root / 'parent').mkdir(); (root / 'parent/file').write_text('safe captured bytes')
            outside = Path(directory) / 'outside'; outside.mkdir(); (outside / 'file').write_text('private')
            original = os.open
            def replace_parent(path, flags, **kwargs):
                fd = original(path, flags, **kwargs)
                if path == 'parent':
                    (root / 'parent').rename(root / 'original')
                    (root / 'parent').symlink_to(outside)
                return fd
            with mock.patch.object(source.os, 'open', side_effect=replace_parent):
                self.assertEqual(source.read_entry(root, 'parent/file', 4096), (b'safe captured bytes', '100644'))


if __name__ == '__main__':
    unittest.main()
