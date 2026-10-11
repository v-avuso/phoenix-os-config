#!/usr/bin/env python3
"""Actual reserved activation adapter lifetime with explicit host interface stubs."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import threading
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
engine_module = load('engine', OWNER / 'reservations.py')
deploy = load('deployment', OWNER / 'deployment.py')


def helper(directory, nonce, legacy=False):
    directory = Path(directory)
    config = {'target': 'metal', 'activationSpool': str(directory / 'spool'), 'activationLock': str(directory / 'activation.lock'), 'reservations': {'fixture': True}}
    mapping = json.loads((directory / 'mapping.json').read_text()) if (directory / 'mapping.json').exists() else None
    engine = engine_module.Engine(directory / 'state', baseline=lambda: (directory / 'baseline').read_text(), owner_uid=os.getuid(), mapping=mapping)
    manager = type('Manager', (), {'engine': engine, 'module': engine_module})()
    original_lstat, original_fstat = Path.lstat, os.fstat
    def root_info(info):
        values = list(info)
        values[4] = 0
        return os.stat_result(values)
    def lstat(path, *args, **kwargs):
        info = original_lstat(path, *args, **kwargs)
        return root_info(info) if path in {directory, directory / 'spool'} else info
    def fstat(fd):
        info = original_fstat(fd)
        return root_info(info) if os.readlink('/proc/self/fd/' + str(fd)).endswith(('.json', '/activation.lock')) else info
    def activate(config, closure, action, run):
        try:
            run([sys.executable, str(directory / 'mutation.py'), str(directory)], timeout=5)
        except Exception:
            (directory / 'rollback').write_text('started')
            run([sys.executable, str(directory / 'rollback.py'), str(directory)], timeout=5)
            raise
        (directory / 'baseline').write_text('new')
    # Explicit stubs: fixture owner is not root; no Nix/store/systemd/OS change.
    with mock.patch.object(os, 'getuid', return_value=0), mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(Path, 'lstat', lstat), mock.patch.object(os, 'fstat', fstat), mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(Path, 'resolve', lambda self, **kwargs: Path('source') if str(self).endswith('activated-source') else Path('profile') if str(self) == '/nix/var/nix/profiles/system' else self), mock.patch.object(deploy, 'activate', activate):
        if legacy:
            config.pop('reservations')
            config.update(baseline=str(directory / 'baseline'), reviewScript=str(OWNER / 'deploy-review.py'))
            configfile = directory / 'legacy-config.json'; configfile.write_text(json.dumps(config))
            with mock.patch.object(sys, 'argv', ['controller', str(configfile), 'activate', 'closure', 'test', '--expected-base', str(directory / 'baseline'), '--expected-source', 'source', '--expected-profile', 'profile']):
                deploy.main()
        else:
            deploy.activate_reserved(config, nonce)


class Integration(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        (self.directory / 'spool').mkdir(mode=0o700)
        (self.directory / 'baseline').write_text('old')
        self.engine = engine_module.Engine(self.directory / 'state', baseline=lambda: (self.directory / 'baseline').read_text(), owner_uid=os.getuid())
        self.ticket = self.engine.acquire(os.getuid(), 'first-task', 'deployment.test', 'old')
        self.cap = {key: self.ticket[key] for key in ('generation', 'capability')}
        self.nonce = 'a' * 64
        binding = dict(nonce=self.nonce, target='metal', action='test', closure='closure', source='source', reservation=self.cap, reservationUid=os.getuid())
        envelope = self.directory / 'spool' / (self.nonce + '.json')
        envelope.write_text(json.dumps(binding)); envelope.chmod(0o600)
        (self.directory / 'mutation.py').write_text("import pathlib, sys, time\nd=pathlib.Path(sys.argv[1]); (d/'started').touch()\nwhile not (d/'finish').exists(): time.sleep(.02)\nif (d/'fail').exists(): raise SystemExit(1)\n")
        (self.directory / 'rollback.py').write_text("import pathlib, sys, time\nd=pathlib.Path(sys.argv[1])\nwhile not (d/'rollback-finish').exists(): time.sleep(.02)\n")
        self.processes = []
    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill(); process.wait()
        self.temporary.cleanup()
    def wait_file(self, name):
        deadline = time.monotonic() + 3
        while not (self.directory / name).exists():
            if time.monotonic() > deadline: self.fail('helper did not reach ' + name)
            time.sleep(.02)
    def spawn(self):
        process = subprocess.Popen([sys.executable, '-B', __file__, 'helper', str(self.directory), self.nonce], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.processes.append(process)
        self.wait_file('started')
        return process
    def test_activation_advances_owner_and_runtime_hold_then_second_task(self):
        process = self.spawn()
        second = self.engine.acquire(os.getuid(), 'second-task', 'deployment.switch', 'old')
        self.assertEqual(second['state'], 'queued')
        (self.directory / 'finish').touch(); self.assertEqual(process.wait(3), 0)
        self.engine.renew(os.getuid(), **self.cap, seconds=60)
        self.engine.release(os.getuid(), **self.cap)
        with self.assertRaises(engine_module.Rejected):
            self.engine.poll(os.getuid(), second['generation'], second['capability'])
        self.engine.cancel(os.getuid(), second['generation'], second['capability'])
        second = self.engine.acquire(os.getuid(), 'second-task-current', 'deployment.switch', 'new')
        self.assertEqual(second['state'], 'owned')
    def test_revoke_does_not_overlap_actual_helper_or_failed_rollback(self):
        (self.directory / 'fail').touch()
        process = self.spawn()
        self.engine.force_unlock(self.cap['generation'], 'recover failed task')
        second = self.engine.acquire(os.getuid(), 'second', 'deployment.test', 'old')
        cap = {key: second[key] for key in ('generation', 'capability')}
        with self.assertRaises(engine_module.Busy):
            with self.engine.operation(os.getuid(), command='deployment.test', **cap): pass
        (self.directory / 'finish').touch(); self.wait_file('rollback')
        with self.assertRaises(engine_module.Busy):
            with self.engine.operation(os.getuid(), command='deployment.test', **cap): pass
        (self.directory / 'rollback-finish').touch(); self.assertNotEqual(process.wait(3), 0)
        with self.engine.operation(os.getuid(), command='deployment.test', **cap): pass
    def test_success_after_revoke_reports_actual_success_without_new_owner_refresh(self):
        process = self.spawn()
        self.engine.force_unlock(self.cap['generation'], 'recover')
        second = self.engine.acquire(os.getuid(), 'second', 'deployment.test', 'old')
        (self.directory / 'finish').touch(); self.assertEqual(process.wait(3), 0)
        self.assertEqual((self.directory / 'baseline').read_text(), 'new')
        with self.assertRaises(engine_module.Rejected):
            self.engine.renew(os.getuid(), second['generation'], second['capability'], seconds=60)
    def test_controller_death_keeps_actual_activation_gate(self):
        pidfile = self.directory / 'service-pid'
        code = "import subprocess,sys,pathlib,time; p=subprocess.Popen([sys.executable,'-B',%r,'helper',%r,%r],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); pathlib.Path(%r).write_text(str(p.pid)); time.sleep(10)" % (__file__, str(self.directory), self.nonce, str(pidfile))
        controller = subprocess.Popen([sys.executable, '-c', code])
        self.processes.append(controller)
        self.wait_file('started'); controller.kill(); controller.wait()
        with self.assertRaises(engine_module.Busy):
            with self.engine.operation(os.getuid(), command='deployment.test', **self.cap): pass
        (self.directory / 'finish').touch()
        deadline = time.monotonic() + 3
        while (self.directory / 'spool' / (self.nonce + '.json')).exists():
            if time.monotonic() > deadline: self.fail('detached helper did not finish')
            time.sleep(.02)
        with self.engine.operation(os.getuid(), command='deployment.test', **self.cap): pass

    def test_expiry_while_actual_activation_is_blocked_cannot_overlap(self):
        process = self.spawn()
        future = time.monotonic() + 1000
        self.engine.clock = lambda: future
        second = self.engine.acquire(os.getuid(), 'second-after-expiry', 'deployment.test', 'old')
        cap = {key: second[key] for key in ('generation', 'capability')}
        with self.assertRaises(engine_module.Busy):
            with self.engine.operation(os.getuid(), command='deployment.test', **cap): pass
        (self.directory / 'finish').touch(); self.assertEqual(process.wait(3), 0)
        with self.assertRaises(engine_module.Rejected):
            self.engine.renew(os.getuid(), **cap, seconds=60)

    def test_controller_authority_off_missing_stale_uid_generation_and_mapping(self):
        request = dict(files={'flake.nix': '{}', 'flake.lock': '{}'}, modes={'flake.nix': '100644', 'flake.lock': '100644'}, commit='a'*40, target='metal', action='test', reason='fixture')
        with self.assertRaises(ValueError): deploy.request_valid(dict(request, reservation=self.cap), 'metal')
        with self.assertRaises(ValueError): deploy.request_valid(request, 'metal', True)
        manager = type('Manager', (), {'engine': self.engine, 'module': engine_module})()
        config = {'reservations': True, 'target': 'metal', 'modelReviewEnabled': False, 'operatorUid': os.getuid()}
        with mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(deploy, 'process_inner', return_value={'ok': True}) as workflow:
            with self.assertRaises(deploy.DeploymentFailure):
                deploy.process(config, dict(request, reservation=self.cap), os.getuid(), 1)
            self.assertEqual(deploy.process(config, dict(request, reservation=self.cap), os.getuid(), 1, operator=True), {'ok': True})
            for uid, cap in [(os.getuid()+1, self.cap), (os.getuid(), dict(self.cap, generation=self.cap['generation']+1)), (os.getuid(), dict(self.cap, capability='0'*64))]:
                with self.assertRaises(engine_module.Rejected):
                    deploy.reservation_identity(config, cap, uid, 'deployment.test')
            self.engine.mapping['deployment.switch'] = 'other'
            with self.assertRaises(engine_module.Rejected):
                deploy.reservation_identity(config, self.cap, os.getuid(), 'deployment.switch')
            (self.directory / 'baseline').write_text('new')
            with self.assertRaises(engine_module.Rejected):
                deploy.reservation_identity(config, self.cap, os.getuid(), 'deployment.test')

    def test_mapped_admin_real_socket_gate_denies_missing_then_allows_fixed_operation(self):
        admin = load('admin', OWNER / 'admin.py')
        self.engine.mapping['admin.wakeup-set'] = 'system-testing'
        manager = type('Manager', (), {'engine': self.engine, 'module': engine_module})()
        broker = type('Broker', (), {})()
        broker.reservations = manager
        broker.dispatch = mock.Mock(return_value='{}')
        config = {'client_uid': os.getuid(), 'reservations': {'mapping': self.engine.mapping}}
        def exchange(cap):
            client, server = socket.socketpair()
            request = dict(args=['wakeup-set', 'fixed-device', 'enabled'], reason='fixture')
            if cap is not None: request['reservation'] = cap
            with mock.patch.object(admin.syslog, 'syslog'):
                thread = threading.Thread(target=admin.handle, args=(server, broker, config))
                thread.start(); client.sendall(json.dumps(request).encode()+b'\n')
                response = json.loads(client.makefile('rb').readline())
                thread.join(2)
            client.close(); server.close()
            return response
        self.assertFalse(exchange(None)['ok']); broker.dispatch.assert_not_called()
        self.assertTrue(exchange(self.cap)['ok']); broker.dispatch.assert_called_once_with(['wakeup-set', 'fixed-device', 'enabled'])

    def test_critical_override_requires_fresh_authenticated_operator_lease(self):
        operator = os.getuid() + 10
        self.engine.release(os.getuid(), **self.cap)
        ticket = self.engine.acquire(operator, 'recovery', 'deployment.override', 'old')
        fresh = {key: ticket[key] for key in ('generation', 'capability')}
        closure = self.directory / 'closure'
        (closure / 'etc/phoenix-agent').mkdir(parents=True)
        source = self.directory / 'source'; source.mkdir()
        (closure / 'etc/phoenix-agent/activated-source').symlink_to(source)
        binding = dict(source=str(source), closure=str(closure), action='test', branch='task', nonce=self.nonce)
        security = mock.Mock(); security.load_pending.return_value = binding
        manager = type('Manager', (), {'engine': self.engine, 'module': engine_module})()
        config = {'work': str(self.directory), 'modelReviewEnabled': True, 'operatorUid': operator, 'clientUid': os.getuid(), 'reservations': True}
        with mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'load_security', return_value=security), mock.patch.object(deploy, 'load_review'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'activate_bound', return_value={'ok': True}) as activation:
            with self.assertRaises(deploy.DeploymentFailure):
                deploy.override(config, self.nonce, operator, 1)
            with self.assertRaises(engine_module.Rejected):
                deploy.override(config, self.nonce, operator, 1, self.cap)
            with self.assertRaises(ValueError):
                deploy.override(config, self.nonce, os.getuid(), 1, fresh)
            self.assertTrue(deploy.override(config, self.nonce, operator, 1, fresh)['ok'])
            used = activation.call_args.args[1]
            self.assertEqual(used['reservationUid'], operator)
            self.assertEqual(used['reservation'], fresh)
            self.assertEqual(used['source'], binding['source'])

    def test_private_file_override_cli_works_with_default_review_action(self):
        capability = self.directory / 'cap.json'
        capability.write_text(json.dumps(self.cap)); capability.chmod(0o600)
        script = self.directory / 'authenticated-stub.py'
        script.write_text("import json,sys; value=json.load(sys.stdin); assert set(value)=={'generation','capability'}; print(json.dumps({'ok':True}))")
        config = self.directory / 'client.json'
        config.write_text(json.dumps({'reservationAdapter': str(OWNER / 'reservation-client.py'), 'overrideCommand': [sys.executable, str(script)]}))
        result = subprocess.run([sys.executable, '-B', str(OWNER / 'deploy-review.py'), str(config), '--security-override', self.nonce, '--reservation-file', str(capability)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(self.cap['capability'], result.stdout + result.stderr)

    def test_routine_staging_composes_bounded_root_lease_without_model(self):
        self.engine.release(os.getuid(), **self.cap)
        manager = type('Manager', (), {'engine': self.engine, 'module': engine_module})()
        binding = dict(base='old-source', profile='profile', profileSource='profile-source', source='source', closure='closure', action='update', target='metal', nonce=self.nonce)
        config = dict(reservations=True, activationSpool=str(self.directory / 'spool'), nixStore='nix-store', systemdRun='systemd-run', python=sys.executable, controller='controller', configPath='config')
        def command(argv, **kwargs):
            if argv[0] == 'nix-store': return b''
            self.assertEqual(argv[0], 'systemd-run')
            self.assertEqual(argv[-2:], ['activate-reserved', self.nonce])
            envelope = json.loads((self.directory / 'spool' / (self.nonce + '.json')).read_text())
            self.assertEqual(envelope['reservationUid'], 0)
            self.assertTrue(envelope['routineReservation'])
            cap = envelope['reservation']
            self.assertNotIn(cap['capability'], ' '.join(argv))
            with self.engine.operation(0, command='deployment.update', **cap): pass
            self.engine.release(0, **cap)
            return b''
        review = mock.Mock(); review.run.side_effect = command
        # Replace the setup's unused manual envelope to test routine dispatch.
        (self.directory / 'spool' / (self.nonce + '.json')).unlink()
        with mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'store_path'), mock.patch.object(Path, 'resolve', lambda self, **kwargs: self), mock.patch.object(deploy, 'load_security') as model:
            self.assertTrue(deploy.activate_bound(config, binding, self.directory, review, {}, os.getuid(), 1)['ok'])
            model.assert_not_called()
        second = self.engine.acquire(os.getuid(), 'runtime', 'deployment.test', 'old')
        # Occupied runtime task cancels routine's queued ticket without activation.
        (self.directory / 'spool' / (self.nonce + '.json')).unlink()
        with mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'store_path'), mock.patch.object(Path, 'resolve', lambda self, **kwargs: self):
            with self.assertRaises(deploy.DeploymentFailure) as failure:
                deploy.activate_bound(config, binding, self.directory, review, {}, os.getuid(), 1)
            self.assertEqual(failure.exception.code, 'routine-resource-busy')
        self.assertFalse(any(row['uid'] == 0 for row in self.engine.status()['queue']))

    def test_mapping_rename_and_off_helper_share_actual_execution_guard(self):
        first = self.spawn()
        self.engine.force_unlock(self.cap['generation'], 'recover while old mapping mutates')
        self.engine.mapping = {key: 'renamed-resource' for key in self.engine.mapping}
        (self.directory / 'mapping.json').write_text(json.dumps(self.engine.mapping))
        ticket = self.engine.acquire(os.getuid(), 'new-mapping-task', 'deployment.test', 'old')
        nonce = 'b' * 64
        envelope = self.directory / 'spool' / (nonce + '.json')
        envelope.write_text(json.dumps(dict(nonce=nonce, target='metal', action='test', closure='closure', source='source', reservation={key: ticket[key] for key in ('generation', 'capability')}, reservationUid=os.getuid())))
        envelope.chmod(0o600)
        for mode in ('helper', 'legacy-helper'):
            competing = subprocess.run([sys.executable, '-B', __file__, mode, str(self.directory), nonce], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            self.assertNotEqual(competing.returncode, 0)
        (self.directory / 'finish').touch(); self.assertEqual(first.wait(3), 0)
        # The actual OFF activation entry point succeeds after the old helper ends.
        legacy = subprocess.run([sys.executable, '-B', __file__, 'legacy-helper', str(self.directory), nonce], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        self.assertEqual(legacy.returncode, 0)

    def test_timeout_kills_descendant_before_recovery(self):
        descendant = "import pathlib,time; time.sleep(.5); pathlib.Path(%r).touch()" % str(self.directory / 'escaped')
        code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',%r]); time.sleep(5)" % descendant
        with self.engine.operation(os.getuid(), command='deployment.test', **self.cap) as operation:
            with self.assertRaises(subprocess.TimeoutExpired):
                operation.run_child([sys.executable, '-c', code], timeout=.1)
            time.sleep(.7)
            self.assertFalse((self.directory / 'escaped').exists())

if __name__ == '__main__':
    if sys.argv[1:2] in (['helper'], ['legacy-helper']):
        helper(sys.argv[2], sys.argv[3], sys.argv[1] == 'legacy-helper')
    else:
        unittest.main()
