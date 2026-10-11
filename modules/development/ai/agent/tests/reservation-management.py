"""Disposable management socket tests. Fake OS/Polkit identity is explicit."""
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client = load('management', ROOT / 'reservation-client.py')
admin = load('admin', ROOT / 'admin.py')
engine = load('engine', ROOT / 'reservations.py')


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.uid = os.getuid()
        self.config = {'client_uid': self.uid}
        self.settings = {'engine': str(ROOT / 'reservations.py'), 'state': str(self.root / 'state'),
                         'mapping': engine.DEFAULT_MAPPING, 'bounds': {'owner_uid': self.uid}}
        with patch.object(client, 'baseline', return_value='fake-os-baseline'):
            self.management = client.Management(self.settings)
        # Explicit fake-OS baseline rather than reading the running deployment.
        self.management.engine.baseline = lambda: 'fake-os-baseline'
        self.broker = admin.Broker(self.config)
        self.broker.reservations = self.management
        self.config['reservations'] = {'operator_uid': self.uid}
        self.socket_path = str(self.root / 'socket')
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(self.socket_path)
        self.listener.listen()

    def tearDown(self):
        self.listener.close()
        self.temp.cleanup()

    def wire(self, request, fake_uid=None):
        errors = []
        fixture_uid = self.uid
        def serve():
            try:
                conn, _ = self.listener.accept()
                with conn:
                    if fake_uid is None:
                        admin.handle(conn, self.broker, self.config)
                    else:
                        # Explicit fake kernel UID used only in negative tests.
                        class FakePeer:
                            def __getattr__(self, name):
                                return getattr(conn, name)
                            def getsockopt(self, *args):
                                return struct.pack('3i', os.getpid(), fake_uid, fixture_uid)
                        admin.handle(FakePeer(), self.broker, self.config)
            except BaseException as error:
                errors.append(error)
        worker = threading.Thread(target=serve)
        worker.start()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(self.socket_path)
            conn.sendall(json.dumps(request).encode()+b'\n')
            with conn.makefile('rb') as stream:
                try:
                    result = json.loads(stream.readline())
                except ConnectionResetError:
                    result = {"ok": False}
        worker.join(3)
        if errors:
            raise errors[0]
        return result

    def acquire(self, task='task'):
        request = {'operation': 'acquire', 'command': 'deployment.test',
                   'task': task, 'baseline': 'fake-os-baseline'}
        return self.wire({'reservation': request})['reservation']

    def test_socket_fifo_and_no_secret_audit(self):
        with patch.object(admin.syslog, 'syslog') as audit:
            first = self.acquire()
            second = self.acquire('second')
            self.assertEqual(first['state'], 'owned')
            self.assertEqual(second['state'], 'queued')
            self.assertEqual(first['uid'], self.uid)
            self.assertFalse(self.wire({'reservation': {'operation': 'force-unlock',
                'generation': first['generation'], 'reason': 'repair'}})['ok'])
            release = {'operation': 'release', **{k: first[k] for k in ('generation', 'capability')}}
            self.assertTrue(self.wire({'reservation': release})['ok'])
            poll = {'operation': 'poll', **{k: second[k] for k in ('generation', 'capability')}}
            self.assertEqual(self.wire({'reservation': poll})['reservation']['state'], 'owned')
            logs = str(audit.call_args_list)
            self.assertNotIn(first['capability'], logs)
            self.assertNotIn(second['capability'], logs)

    def test_wire_rejects_identity_mapping_and_arbitrary_fields(self):
        self.assertFalse(self.wire({'reservation': {'operation': 'status'}}, fake_uid=self.uid+1)['ok'])
        for operation in ([], 'exec', 'deployment.test'):
            self.assertFalse(self.wire({'reservation': {'operation': operation}})['ok'])
        for extra in ({'uid': self.uid}, {'state': '/tmp'}, {'argv': ['true']}, {'operator_uid': self.uid}):
            self.assertFalse(self.wire({'reservation': {'operation': 'status', **extra}})['ok'])
        for command in ('test', 'deployment.build', '/bin/true'):
            self.assertFalse(self.wire({'reservation': {'operation': 'acquire', 'task': 'task',
                'command': command, 'baseline': 'fake-os-baseline'}})['ok'])

    def test_root_route_recovery_expected_generation(self):
        first = self.acquire()
        request = {'reservation': {'operation': 'force-unlock', 'generation': first['generation']+1,
                                  'reason': 'operator repair'}, 'operator_uid': self.uid}
        self.assertFalse(self.wire(request, fake_uid=0)['ok'])
        request['reservation']['generation'] = first['generation']
        self.assertTrue(self.wire(request, fake_uid=0)['ok'])
        request['operator_uid'] += 1
        self.assertFalse(self.wire(request, fake_uid=0)['ok'])

    def test_authenticated_acquire_roundtrip_one_helper(self):
        config = {'operator_uid': self.uid, 'bounds': {'wait_seconds': 3600}}
        class Input:
            buffer = io.BytesIO(b'{"operation":"acquire","task":"operator","command":"deployment.test","wait":0}\n')
        def exchange(settings, request, uid):
            with patch.object(client, 'baseline', return_value='fake-os-baseline'):
                result = self.wire({'reservation': request, 'operator_uid': uid}, fake_uid=0)
            if not result['ok']:
                raise ValueError(result['error'])
            return result['reservation']
        with patch.object(client.os, 'geteuid', return_value=0), patch.dict(os.environ, {'PKEXEC_UID':str(self.uid)}, clear=True), patch.object(client.sys, 'stdin', Input()), patch.object(client, 'exchange', side_effect=exchange) as calls, patch('builtins.print') as output:
            client.authenticated(config)
            self.assertEqual(calls.call_count, 2)  # status+acquire, same authenticated lifetime
            result = json.loads(output.call_args.args[0])
            self.assertEqual(result['state'], 'owned')
            self.assertEqual(len(result['capability']), 64)
        for recovery, operation in ((False, 'force-unlock'), (True, 'status')):
            Input.buffer = io.BytesIO(json.dumps({'operation':operation}).encode()+b'\n')
            with patch.object(client.os, 'geteuid', return_value=0), patch.dict(os.environ, {'PKEXEC_UID':str(self.uid)}, clear=True), patch.object(client.sys, 'stdin', Input()), self.assertRaises(ValueError):
                client.authenticated(config, recovery)

    def test_operator_queued_wait_promotes_and_cancels_in_one_lifetime(self):
        config = {'operator_uid': self.uid, 'bounds': {'wait_seconds': 3600}}
        for promote in (True, False):
            first = self.acquire('existing owner')
            class Input:
                buffer = io.BytesIO(b'{"operation":"acquire","task":"waiting operator","command":"deployment.test","wait":1}\n')
            operations = []
            def exchange(settings, request, uid):
                operations.append(request['operation'])
                with patch.object(client, 'baseline', return_value='fake-os-baseline'):
                    response = self.wire({'reservation': request, 'operator_uid': uid}, fake_uid=0)
                if not response['ok']:
                    raise ValueError(response['error'])
                return response['reservation']
            def release(_):
                self.management.engine.release(self.uid, first['generation'], first['capability'])
            with patch.object(client.os, 'geteuid', return_value=0), patch.dict(os.environ, {'PKEXEC_UID':str(self.uid)}, clear=True), patch.object(client.sys, 'stdin', Input()), patch.object(client, 'exchange', side_effect=exchange), patch.object(client, 'time', SimpleNamespace(monotonic=Mock(side_effect=[0, 0, 0] if promote else [0, 2]), sleep=Mock(side_effect=release))), patch('builtins.print') as output:
                if promote:
                    client.authenticated(config)
                    result = json.loads(output.call_args.args[0])
                    self.assertEqual(result['state'], 'owned')
                    self.assertEqual(operations, ['status', 'acquire', 'poll'])
                    self.management.engine.release(self.uid, result['generation'], result['capability'])
                else:
                    with self.assertRaises(client.Failure) as failure:
                        client.authenticated(config)
                    self.assertEqual(operations, ['status', 'acquire', 'cancel'])
                    self.assertEqual(failure.exception.stage, 'wait')
                    self.assertNotIn('capability', str(failure.exception))
                    output.assert_not_called()
                    self.assertFalse(self.management.engine.status()['queue'])
                    self.management.engine.release(self.uid, first['generation'], first['capability'])

    def test_file_permissions_links_and_no_clobber(self):
        path = self.root / 'cap'
        fd = client.private_file(path, self.uid, write=True)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'generation': 1, 'capability': 'a'*64}, stream)
        self.assertEqual(client.read_capability(path)['generation'], 1)
        with self.assertRaises(FileExistsError):
            client.private_file(path, self.uid, write=True)
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            client.read_capability(path)
        path.chmod(0o600)
        os.link(path, self.root/'linked')
        with self.assertRaises(ValueError):
            client.read_capability(path)
        (self.root/'link').symlink_to(path)
        with self.assertRaises(OSError):
            client.read_capability(self.root/'link')
        with self.assertRaises(ValueError):
            client.private_file(path, self.uid+1)

    def test_fixed_operator_authentication(self):
        config = {'operator_uid': self.uid}
        for root, pkuid in ((False, str(self.uid)), (True, None), (True, str(self.uid+1))):
            with patch.object(client.os, 'geteuid', return_value=0 if root else self.uid), patch.dict(os.environ, {} if pkuid is None else {'PKEXEC_UID': pkuid}, clear=True):
                with self.assertRaises(ValueError):
                    client.authenticated(config)
        class Input:
            buffer = io.BytesIO(b'{"operation":"status"}\n')
        with patch.object(client.os, 'geteuid', return_value=0), patch.dict(os.environ, {'PKEXEC_UID':str(self.uid)}, clear=True), patch.object(client.sys, 'stdin', Input()), patch.object(client, 'exchange', return_value={}) as exchange, patch('builtins.print'):
            client.authenticated(config)
            exchange.assert_called_once_with(config, {'operation': 'status'}, self.uid)


if __name__ == '__main__':
    unittest.main()
