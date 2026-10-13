#!/usr/bin/env python3
"""Authorization contract; OS authentication/execution are stubbed explicitly."""
import importlib.util
import json
import io
import os
import struct
import socket
import tempfile
import contextlib
from pathlib import Path
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[2]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
auth = load('authorization', ROOT / 'authorization/request.py')
admin = load('authorization_admin', ROOT / 'admin.py')
deploy = load('authorization_deployment', ROOT / 'deployment.py')
class Contract(unittest.TestCase):
    def setUp(self):
        self.policy = auth.default_policy(False, 1000, 1000, [], ['NetworkManager.service'])
        self.request = auth.named('admin.dmesg', {}, 'fixture', 'Read kernel diagnostics')
    def test_same_diagnostic_automatic_human_denied(self):
        broker = admin.Broker({'client_uid': 1000, 'wakeup_devices': [], 'status_services': [], 'dmesg': '/fixed/dmesg', 'authorizationPolicy': self.policy})
        with mock.patch.object(broker, 'run', return_value='bounded kernel output'):
            self.assertEqual(broker.execute_authorized(self.request, 1000, 23), 'bounded kernel output')
            self.policy['diagnostics']['admin.dmesg'] = 'human'
            with self.assertRaises(ValueError): broker.execute_authorized(self.request, 1000, 23)
            self.assertEqual(broker.execute_authorized(self.request, 1000, 23, operator=True), 'bounded kernel output')
            self.policy['diagnostics']['admin.dmesg'] = 'denied'
            with self.assertRaises(ValueError): broker.execute_authorized(self.request, 1000, 23, operator=True)
    def test_boundary(self):
        for reason in ['x' * 301, '\nunsafe', 'unsafe\u202e', 'unsafe\u200b', 9]:
            with self.assertRaises(ValueError): auth.validate(auth.named('admin.dmesg', {}, 'fixture', reason), self.policy)
        auth.validate(auth.named('admin.dmesg', {}, 'fixture', 'x' * 300), self.policy)
        for field in ['mode', 'backend', 'config', 'command', 'authorizationId']:
            with self.assertRaises(ValueError): auth.validate(dict(self.request, **{field: 'automatic'}), self.policy)
        for version in [True, '1', 2]:
            with self.assertRaises(ValueError): auth.validate(dict(self.request, version=version), self.policy)
        with self.assertRaises(ValueError): auth.validate(auth.named('admin.service-status', {'service': '/bin/sh'}, 'fixture', 'read'), self.policy)
    def test_deployment_and_caller_policy(self):
        deploy = auth.named('deployment.test', {'target': 'metal'}, 'fixture', 'Deploy dirty source')
        self.assertEqual(auth.validate(deploy, self.policy), 'human')
        self.assertEqual(auth.validate(auth.named('deployment.update', {'target': 'metal'}, 'updater', 'Update stable packages'), self.policy), 'automatic')
        self.policy['securityReviewEnabled'] = True
        self.assertEqual(auth.validate(deploy, self.policy), 'security-review')
        with self.assertRaises(ValueError): auth.preflight(self.request, self.policy, 999, 24)
        with mock.patch.object(auth.syslog, 'syslog') as journal:
            event = auth.preflight(self.request, self.policy, 1000, 24)
            record = json.loads(journal.call_args.args[-1])
            self.assertEqual(event['id'], record['id'])
            self.assertEqual(record['event'], 'preflight')
            self.assertEqual(record['uid'], 1000)
    def test_distinct_operator_socket_metadata_never_executes(self):
        policy = auth.default_policy(False, 2000, 1000)
        named = auth.named('deployment.test', {'target': 'metal'}, 'fixture', 'Validate dirty source')
        for request, permitted in [({'authorization': named}, True), ({'action': 'test'}, False)]:
            handlers = {}
            connection = mock.Mock()
            connection.getsockopt.return_value = struct.pack('3i', 23, 1000, 1000)
            connection.recv.return_value = json.dumps(request).encode() + b'\n'
            listener = mock.Mock()
            def finish():
                handlers[deploy.signal.SIGUSR1](None, None)
                raise socket.timeout()
            listener.accept.side_effect = [(connection, None), finish]
            # Callable side effects in a list aren't called by Mock; use explicit sequence.
            calls = iter([0, 1])
            def accept():
                if next(calls) == 0: return connection, None
                return finish()
            listener.accept.side_effect = accept
            config = dict(clientUid=2000, operatorUid=1000, target='metal', modelReviewEnabled=False, authorizationPolicy=policy)
            with mock.patch.object(deploy.os, 'getuid', return_value=0), mock.patch.object(deploy.socket, 'socket', return_value=listener), mock.patch.object(deploy.signal, 'signal', side_effect=lambda sig, fn: handlers.update({sig: fn})), mock.patch.object(deploy, 'process') as execute, contextlib.redirect_stdout(io.StringIO()):
                deploy.serve(config)
            response = json.loads(connection.sendall.call_args.args[0])
            self.assertEqual(response['ok'], permitted)
            if permitted: self.assertEqual(response['decision'], 'human')
            execute.assert_not_called()

    def test_admin_socket_preflight_and_direct_legacy_policy(self):
        self.policy['clientUid'] = 2000
        self.policy['diagnostics']['admin.dmesg'] = 'human'
        config = dict(client_uid=2000, wakeup_devices=[], status_services=[], dmesg='/fixed/dmesg', authorizationPolicy=self.policy)
        broker = admin.Broker(config)
        for request, uid, permitted in [({'authorization': self.request}, 1000, True), ({'args': ['dmesg'], 'reason': 'fixture'}, 2000, False), ({'args': ['dmesg'], 'reason': 'fixture'}, 1000, False)]:
            connection = mock.Mock()
            connection.getsockopt.return_value = struct.pack('3i', 24, uid, 1000)
            connection.makefile.return_value = io.BytesIO(json.dumps(request).encode() + b'\n')
            with mock.patch.object(broker, 'dispatch') as dispatch, mock.patch.object(admin.syslog, 'syslog'):
                admin.handle(connection, broker, config)
            self.assertEqual(json.loads(connection.sendall.call_args.args[0])['ok'], permitted)
            dispatch.assert_not_called()
        with mock.patch.object(broker, 'run', return_value='human fixture'), mock.patch.object(admin.syslog, 'syslog') as journal:
            self.assertEqual(broker.execute_authorized(self.request, 1000, 24, operator=True, preflight_id='a' * 32), 'human fixture')
            events = [json.loads(call.args[-1]) for call in journal.call_args_list]
            self.assertEqual(events[0]['clientPreflightId'], 'a' * 32)
            self.assertNotEqual(events[0]['id'], 'a' * 32)
            self.assertEqual(events[0]['id'], events[1]['id'])
        for identifier in ['/bin/sh', 'x' * 33, [], 9]:
            with self.assertRaises(ValueError):
                broker.execute_authorized(self.request, 1000, 24, operator=True, preflight_id=identifier)

    def test_installed_policy_revalidation_and_isolated_script(self):
        with tempfile.TemporaryDirectory() as directory:
            policy_path = Path(directory) / 'policy.json'
            policy_path.write_text(json.dumps(self.policy))
            isolated = Path(directory) / 'entry.py'
            isolated.write_text((ROOT / 'admin.py').read_text().replace('@authorizationLibrary@', str(ROOT / 'authorization/request.py')))
            module = load('authorization_isolated', isolated)
            broker = module.Broker(dict(client_uid=1000, wakeup_devices=[], status_services=[], dmesg='/fixed/dmesg', authorizationPolicy=str(policy_path)))
            with mock.patch.object(broker, 'run', return_value='fixture'):
                broker.execute_authorized(self.request, 1000, 24)
                self.policy['diagnostics']['admin.dmesg'] = 'denied'
                policy_path.write_text(json.dumps(self.policy))
                with self.assertRaises(ValueError): broker.execute_authorized(self.request, 1000, 24)
        with self.assertRaises(ValueError):
            auth.policy(dict(authorizationPolicy=self.policy, modelReviewEnabled=True))
        state = auth.named('admin.wakeup-set', {'device': 'fixture', 'state': []}, 'fixture', 'change state')
        self.policy['wakeupDevices'] = ['fixture']
        with self.assertRaises(ValueError): auth.validate(state, self.policy)

    def test_fixed_updater_role_is_operation_specific(self):
        installed = dict(auth.default_policy(False, 2000, 1000), updaterUid=1000)
        update = auth.named('deployment.update', {'target': 'metal'}, 'fixture', 'Stage stable updates')
        self.assertEqual(auth.require(update, installed, 1000, 24)['decision'], 'automatic')
        for operation, arguments in [('deployment.test', {'target': 'metal'}), ('deployment.switch', {'target': 'metal'}), ('deployment.boot', {'target': 'metal'}), ('admin.dmesg', {})]:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                auth.require(auth.named(operation, arguments, 'fixture', 'Unauthorized updater operation'), installed, 1000, 24)
        for uid in [True, '1000', -1, None]:
            with self.assertRaises(ValueError): auth.policy(dict(authorizationPolicy=dict(installed, updaterUid=uid)))
        with self.assertRaises(ValueError): auth.policy(dict(authorizationPolicy=installed, updaterUid=2000))
        with self.assertRaises(ValueError): auth.validate(dict(update, role='updater'), installed)

if __name__ == '__main__': unittest.main()
