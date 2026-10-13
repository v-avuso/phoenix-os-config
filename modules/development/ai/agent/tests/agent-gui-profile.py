#!/usr/bin/env python3
"""Typed preference migration, keeping Native secrets and history outside."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
spec = importlib.util.spec_from_file_location('gui_profile', ROOT / 'modules/development/ai/agent/gui-profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
ACCOUNT = '11111111-1111-4111-8111-111111111111'


class Profile(unittest.TestCase):
    def test_selected_preferences_exclude_private_state_and_other_accounts(self):
        atoms = {'electron:onboarding-projectless-completed': True,
                 'electron:onboarding-welcome-pending': False,
                 'electron:onboarding-conversational-completed-by-account-id': {ACCOUNT: True, 'other': True},
                 'electron:onboarding-welcome-v2-role-state': {'roles': ['engineering'], 'workMode': 'coding',
                     'completedConversationalOnboarding': True, 'completedConversationalOnboardingTaskSnapshot': 'private'},
                 'chatgpt-conversation-resume-tokens-v1': 'secret', 'prompt-history': 'private'}
        source = {'electron-persisted-atom-state': atoms, 'auth': 'secret',
                  'electron-main-window-bounds': {'x': 0, 'y': 0, 'width': 2288, 'height': 1288, 'isMaximized': True},
                  'local-projects': {'approved': {'id': 'approved', 'rootPaths': ['/tmp/nested', '/private'], 'name': 'fixture', 'createdAt': 1, 'updatedAt': 2, 'history': 'private'},
                                     'denied': {'id': 'denied', 'rootPaths': ['/private']}}}
        selected = profile.selected(source, ACCOUNT, ['/tmp'])
        text = json.dumps(selected)
        for denied in ['secret', 'private', 'other', 'Snapshot', 'history']:
            self.assertNotIn(denied, text)
        self.assertEqual(selected['local-projects']['approved']['rootPaths'], ['/tmp/nested'])
        self.assertEqual(selected['electron-main-window-bounds']['width'], 1400)
        self.assertEqual(selected['electron-main-window-bounds']['height'], 900)
        self.assertFalse(selected['electron-main-window-bounds']['isMaximized'])
        self.assertEqual(selected['electron-persisted-atom-state']['electron:onboarding-welcome-v2-role-state']['workMode'], 'coding')

    def test_existing_destination_is_preserved_and_migration_runs_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source, destination = path/'native.json', path/'sandbox.json'
            source.write_text(json.dumps({'electron-persisted-atom-state': {'electron:onboarding-projectless-completed': True}}))
            destination.write_text(json.dumps({'sandbox-own-state': ['keep'], 'electron-main-window-bounds': {'unknownFullscreen': True}, 'electron-persisted-atom-state': {'sandbox-own-atom': 'keep'}}))
            (path/'account-id.json').write_text(json.dumps(ACCOUNT))
            (path/'launcher.json').write_text(json.dumps({'state': directory}))
            config = {'source': str(source), 'destination': str(destination), 'marker': str(path/'marker'), 'launcherConfig': str(path/'launcher.json'), 'workspaces': []}
            profile.seed(config)
            result = json.loads(destination.read_text())
            self.assertEqual(result['sandbox-own-state'], ['keep'])
            self.assertEqual(result['electron-persisted-atom-state']['sandbox-own-atom'], 'keep')
            first = destination.read_text()
            source.write_text('{}')
            profile.seed(config)
            self.assertEqual(first, destination.read_text())
            self.assertEqual(source.read_text(), '{}')

    def test_legacy_seed_imports_new_projects_once_without_overwriting_sandbox(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            def project(key, root, name):
                return {'id': key, 'name': name, 'rootPaths': [str(root)],
                        'createdAt': 1, 'updatedAt': 2, 'chatGptBacking': 'private'}
            native = {'local-projects': {
                'existing': project('existing', path/'existing', 'native name'),
                'second': project('second', path/'second', 'second'),
                'third': project('third', path/'third', 'third'),
                'duplicate': project('duplicate', path/'owned', 'duplicate'),
                'outside': project('outside', Path('/private'), 'outside')},
                'electron-persisted-atom-state': {'electron:onboarding-welcome-pending': True}}
            source, destination, marker = path/'native', path/'sandbox', path/'marker'
            source.write_text(json.dumps(native))
            destination.write_text(json.dumps({'local-projects': {
                'existing': project('existing', path/'existing', 'sandbox name'),
                'owned': project('owned', path/'owned', 'owned')},
                'sandbox-private': 'keep'}))
            marker.write_text('Selected desktop preferences seeded; worker config unchanged.\n')
            config = {'source': str(source), 'destination': str(destination),
                      'marker': str(marker), 'workspaces': [directory]}
            profile.seed(config)
            result = json.loads(destination.read_text())
            self.assertEqual(set(result['local-projects']), {'existing', 'owned', 'second', 'third'})
            self.assertEqual(result['local-projects']['existing']['name'], 'sandbox name')
            self.assertNotIn('chatGptBacking', result['local-projects']['second'])
            self.assertNotIn('electron-persisted-atom-state', result)
            self.assertEqual(result['sandbox-private'], 'keep')
            del result['local-projects']['second']
            destination.write_text(json.dumps(result))
            native['local-projects']['fourth'] = project('fourth', path/'fourth', 'fourth')
            source.write_text(json.dumps(native))
            profile.seed(config)
            result = json.loads(destination.read_text())
            self.assertNotIn('second', result['local-projects'])
            self.assertIn('fourth', result['local-projects'])
            self.assertEqual(json.loads(source.read_text()), native)

    def test_marker_is_fail_closed_and_unchanged_launch_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source, destination, marker = path/'native', path/'sandbox', path/'marker'
            source.write_text('{}')
            destination.write_text('{"sandbox": "keep"}')
            config = {'source': str(source), 'destination': str(destination),
                      'marker': str(marker), 'workspaces': [directory]}
            for value in ('broken', '{}', '{"version": true, "projectIds": []}',
                          '{"version": 2, "projectIds": ["duplicate", "duplicate"]}',
                          '{"version": 2, "projectIds": [1]}', 'x' * (128 * 1024 + 1)):
                marker.write_text(value)
                with self.assertRaisesRegex(ValueError, 'marker'):
                    profile.seed(config)
                self.assertEqual(destination.read_text(), '{"sandbox": "keep"}')
            marker.write_text(json.dumps({'version': 2, 'projectIds': []}))
            before = (destination.stat().st_mtime_ns, marker.stat().st_mtime_ns)
            profile.seed(config)
            self.assertEqual(before, (destination.stat().st_mtime_ns, marker.stat().st_mtime_ns))

    def test_output_bounds_are_checked_before_profile_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source, destination, marker = path/'native', path/'sandbox', path/'marker'
            def project(key):
                return {'id': key, 'name': 'fixture', 'rootPaths': [str(path/'root')],
                        'createdAt': 1, 'updatedAt': 2}
            config = {'source': str(source), 'destination': str(destination),
                      'marker': str(marker), 'workspaces': [directory]}
            destination.write_text('{"sandbox": "keep"}')
            marker.write_text(json.dumps({'version': 2, 'projectIds': []}))
            source.write_text(json.dumps({'local-projects': {
                str(i).zfill(256): project(str(i).zfill(256)) for i in range(600)}}))
            with self.assertRaisesRegex(ValueError, 'marker exceeds'):
                profile.seed(config)
            self.assertEqual(destination.read_text(), '{"sandbox": "keep"}')
            self.assertEqual(json.loads(marker.read_text())['projectIds'], [])
            source.write_text(json.dumps({'local-projects': {'new': project('new')}}))
            destination.write_text(json.dumps({'padding': 'x' * (16 * 1024 * 1024 - 50)}))
            before = destination.read_bytes()
            with self.assertRaisesRegex(ValueError, 'bounded output'):
                profile.seed(config)
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(json.loads(marker.read_text())['projectIds'], [])

    def test_worker_preferences_use_only_fixed_typed_cli_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'config.toml'
            path.write_text('''model="gpt-6.1-sol"
model_reasoning_effort="medium"
service_tier="priority"
approval_policy="never"
sandbox_mode="danger-full-access"
chatgpt_base_url="https://evil.invalid"
[desktop]
conversationDetailMode="STEPS_COMMANDS"
appearanceTheme="dark"
followUpQueueMode="steer"
ambient-suggestions-enabled=true
command="private-command"
[mcp_servers.secret]
url="https://secret.invalid"
''')
            result = profile.worker_preferences(path)
            self.assertEqual(set(result), {'model', 'model_reasoning_effort', 'service_tier', 'desktop.conversationDetailMode', 'desktop.appearanceTheme', 'desktop.followUpQueueMode', 'desktop.ambient-suggestions-enabled'})
            self.assertEqual(result['desktop.conversationDetailMode'], 'STEPS_COMMANDS')
            self.assertNotIn('secret', json.dumps(result))
            path.write_text('model="https://evil.invalid"\nmodel_reasoning_effort="arbitrary"\n[desktop]\nappearanceTheme="arbitrary"\n')
            self.assertEqual(profile.worker_preferences(path), {})

    def test_alias_and_invalid_shapes_are_rejected(self):
        self.assertEqual(profile.selected({'electron-main-window-bounds': {'x': 0, 'y': 0, 'width': float('inf'), 'height': 600}}, None, []), {})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path/'native').write_text('{}')
            (path/'alias').symlink_to(path/'target')
            with self.assertRaisesRegex(ValueError, 'aliased'):
                profile.seed({'marker': str(path/'marker'), 'source': str(path/'native'), 'destination': str(path/'alias')})


if __name__ == '__main__':
    unittest.main()
