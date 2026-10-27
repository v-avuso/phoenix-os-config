import unittest
from unittest.mock import patch
import sources


class Sources(unittest.TestCase):
    def test_default_is_spatial_and_survives_connector_change(self):
        displays = [{'name': 'DP-9', 'x': 4800, 'y': 0},
                    {'name': 'HDMI-A-2', 'x': 2400, 'y': 0},
                    {'name': 'DP-1', 'x': 0, 'y': 0}]
        import json
        with patch.object(sources.subprocess, 'check_output', return_value=json.dumps(displays)):
            ordered = sources.monitors()
        self.assertEqual(sources.default_monitor(ordered, 2), 'HDMI-A-2')
        ordered[1]['name'] = 'DP-3'
        self.assertEqual(sources.default_monitor(ordered, 2), 'DP-3')
        with self.assertRaises(ValueError):
            sources.default_monitor(ordered[:1], 2)

    def test_only_hue_with_connected_explicit_output_can_autoselect(self):
        displays = [{'name': 'DP-3'}]
        preference = {'mode': 'screen', 'output': 'DP-3'}
        self.assertEqual(sources.automatic_selection(sources.APP_ID, preference, displays),
                         '[SELECTION]/screen:DP-3\n')
        for app_id in ('', 'org.example.Other'):
            self.assertIsNone(sources.automatic_selection(app_id, preference, displays))
        self.assertIsNone(sources.automatic_selection(sources.APP_ID, {'mode': 'manual'}, displays))
        self.assertIsNone(sources.automatic_selection(sources.APP_ID, preference, []))
        self.assertIsNone(sources.automatic_selection(sources.APP_ID, [], displays))


class PortalPicker(unittest.TestCase):
    def picker(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location('portal_picker', Path(__file__).with_name('portal-picker.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_other_apps_use_native_picker_without_reading_hue_state(self):
        picker = self.picker()
        for app_id in ('', 'org.example.Other'):
            with self.subTest(app_id=app_id), \
                    patch.object(picker.sys, 'argv', ['picker', '--picker', '/fixed/native-picker', '--hyprctl', '/fixed/hyprctl', '--allow-token']), \
                    patch.dict(picker.os.environ, XDPH_APP_ID=app_id), \
                    patch.object(picker, 'preference_path') as preference, \
                    patch.object(picker.os, 'execv', side_effect=RuntimeError('exec')) as execute:
                with self.assertRaisesRegex(RuntimeError, 'exec'):
                    picker.main()
                preference.assert_not_called()
                execute.assert_called_once_with('/fixed/native-picker', ['/fixed/native-picker', '--allow-token'])

    def test_hue_output_is_automatic_and_manual_mode_keeps_full_picker(self):
        import contextlib
        import io
        picker = self.picker()
        for mode in ('screen', 'manual'):
            output = io.StringIO()
            with patch.object(picker.sys, 'argv', ['picker', '--picker', '/fixed/native-picker', '--hyprctl', '/fixed/hyprctl']), \
                    patch.dict(picker.os.environ, XDPH_APP_ID=sources.APP_ID), \
                    patch.object(picker, 'preference_path') as path, \
                    patch.object(picker, 'monitors', return_value=[{'name': 'DP-3'}]), \
                    patch.object(picker.os, 'execv') as execute, contextlib.redirect_stdout(output):
                import json
                path.return_value.read_text.return_value = json.dumps({'mode': mode, 'output': 'DP-3'})
                picker.main()
            if mode == 'screen':
                self.assertEqual(output.getvalue(), '[SELECTION]/screen:DP-3\n')
                execute.assert_not_called()
            else:
                execute.assert_called_once()
                self.assertEqual(output.getvalue(), '')
