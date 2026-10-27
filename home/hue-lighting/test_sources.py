import importlib.util
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import sources

spec = importlib.util.spec_from_file_location('picker', Path(__file__).with_name('portal-picker.py'))
picker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picker)


class PickerConsent(unittest.TestCase):
    def test_every_identity_opens_native_picker_and_only_hue_defaults_remember(self):
        for identity in ('', 'org.other.App', sources.APP_ID):
            with self.subTest(identity=identity), \
                    patch.dict(os.environ, XDPH_APP_ID=identity), \
                    patch.object(sys, 'argv',
                                 ['picker', '--picker', '/fixed/native', '--test-argument']), \
                    patch.object(picker.os, 'execv') as execute:
                picker.main()
                expected = ['/fixed/native', '--test-argument']
                if identity == sources.APP_ID:
                    expected.append('--allow-token')
                execute.assert_called_once_with('/fixed/native', expected)

    def test_existing_remember_flag_is_preserved_without_duplication(self):
        self.assertEqual(sources.picker_arguments(sources.APP_ID, ['--allow-token']), ['--allow-token'])
        self.assertEqual(sources.picker_arguments('', ['--allow-token']), ['--allow-token'])


if __name__ == '__main__':
    unittest.main()
