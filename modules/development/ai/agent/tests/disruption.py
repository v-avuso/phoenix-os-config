#!/usr/bin/env python3
"""Disposable unit artifacts and exact approval controller tests; no OS mutation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, OWNER / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
unit = load('disruption'); deploy = load('deployment')

class Guard(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.runtime, self.candidate = [self.root / name for name in ('old', 'new')]
        for closure in (self.runtime, self.candidate):
            system = closure / 'etc/systemd/system'; system.mkdir(parents=True)
            user = closure / 'user'; user.mkdir()
            (system / 'display-manager.service').write_text('[Unit]\nDescription=Display\n[Service]\nX-RestartIfChanged=false\nExecStart=/old\n')
            (user / 'kando.service').write_text('[Unit]\nPartOf=session.target\n[Service]\nExecStart=/old\n')
            (user / 'session.target').write_text('[Unit]\nDescription=Session\n')
            (user / 'session.target.wants').mkdir()
            (user / 'session.target.wants/kando.service').symlink_to(user / 'kando.service')
        self.config = dict(systemctl='fixture-systemctl', nixStore='fixture-nix-store', operatorUid=os.getuid(), operatorName='operator', modelReviewEnabled=False,
                           disruptionGuard=dict(enable=True, systemUnits=['display-manager.service'], userUnits=['kando.service', 'session.target']))
        self.active = dict(system=['display-manager.service'], user=['kando.service', 'session.target'])
        self.stack = mock.patch.object(unit, 'immutable', lambda path: Path(path).resolve(strict=True)); self.stack.start()
        self.hm = mock.patch.object(unit, 'home_units', lambda config, closure: Path(closure) / 'user'); self.hm.start()
    def tearDown(self):
        self.hm.stop(); self.stack.stop(); self.temp.cleanup()
    def proof(self):
        return unit.inspect(self.config, str(self.runtime), str(self.candidate), self.active)
    def test_regenerated_generation_package_change_allowed(self):
        (self.candidate / 'packages').write_text('new ordinary package')
        self.assertEqual(self.proof()['findings'], [])
    def test_active_app_change(self):
        (self.candidate / 'user/kando.service').write_text('changed')
        self.assertTrue(self.proof()['findings'])
    def test_active_removal(self):
        (self.candidate / 'user/kando.service').unlink()
        self.assertTrue(self.proof()['findings'])
    def test_dropin(self):
        path = self.candidate / 'user/kando.service.d'; path.mkdir(); (path / 'override.conf').write_text('[Service]\nExecStart=/new')
        self.assertTrue(self.proof()['findings'])
    def test_type_wide_dropin(self):
        path = self.candidate / 'user/service.d'; path.mkdir(); (path / 'override.conf').write_text('[Service]\nExecStart=/new')
        self.assertTrue(self.proof()['findings'])
    def test_dependency_removal(self):
        (self.candidate / 'user/session.target.wants/kando.service').unlink()
        self.assertTrue(self.proof()['findings'])
    def test_inactive_background_change(self):
        self.active['user'] = []
        (self.candidate / 'user/kando.service').write_text('changed')
        self.assertEqual(self.proof()['findings'], [])
    def test_verified_native_no_restart(self):
        path = self.candidate / 'etc/systemd/system/display-manager.service'
        path.write_text(path.read_text().replace('/old', '/new'))
        self.assertEqual(self.proof()['findings'], [])
        path.write_text(path.read_text().replace('X-RestartIfChanged=false', 'X-RestartIfChanged=true'))
        self.assertTrue(self.proof()['findings'])
    def test_unsupported_hm(self):
        with mock.patch.object(unit, 'home_units', side_effect=unit.InspectionRequired('unsupported')):
            self.assertIn('user:inspection-required', self.proof()['findings'])
    def test_active_query_failure(self):
        with mock.patch.object(unit.subprocess, 'run', side_effect=OSError()):
            self.assertEqual(unit.probe(self.config, str(self.runtime), str(self.candidate))['findings'], ['active-unit-query-unavailable'])
    def test_actual_controller_pending_and_exact_helper_approval(self):
        self.config.update(disruptionState=str(self.root / 'state'), disruptionInfo=str(self.root / 'info'))
        Path(self.config['disruptionState']).mkdir(); Path(self.config['disruptionInfo']).mkdir()
        (self.candidate / 'user/kando.service').write_text('changed')
        proof = self.proof()
        binding = dict(nonce='a'*64, action='test', source='/nix/store/source', closure=str(self.candidate), target='metal')
        review = types.SimpleNamespace(run=mock.Mock())
        with mock.patch.object(deploy, 'load_disruption', return_value=unit), mock.patch.object(unit, 'probe', return_value=proof), mock.patch.object(unit, 'state_directory', return_value=self.root / 'state'):
            with self.assertRaises(deploy.DeploymentFailure) as failed:
                deploy.disruption_check(self.config, binding, review, os.getuid(), pending=True)
            self.assertEqual(failed.exception.pending_metadata['pendingKind'], 'disruption')
            record = json.loads((self.root / 'state' / (binding['nonce'] + '.json')).read_text())
            self.assertEqual(record['disruptionProof'], proof)
            receipt = dict(binding, disruptionApproval=proof['digest'])
            deploy.disruption_check(self.config, receipt)
            with mock.patch.object(unit, 'probe', return_value=dict(proof, digest='changed-runtime-active-policy-or-closure')):
                with self.assertRaises(deploy.DeploymentFailure): deploy.disruption_check(self.config, receipt)
    def test_security_then_disruption_approval_sequence(self):
        state = self.root / 'state'; state.mkdir()
        info = self.root / 'info'; info.mkdir()
        work = self.root / 'work'; work.mkdir()
        self.config.update(modelReviewEnabled=True, disruptionState=str(state), disruptionInfo=str(info), work=str(work), target='metal', clientUid=os.getuid())
        nonce = 'd'*64
        binding = dict(nonce=nonce, target='metal', action='test', closure=str(self.candidate), source='source', branch='main')
        proof = dict(digest='exact', findings=['protected-unit-change'])
        approved, pending = [], [dict(binding, policy='security')]
        security = types.SimpleNamespace(identity_version=lambda config: 1, validate_transition=lambda *args: None, policy_digest=lambda config: 'security', load_pending=lambda *args: binding,
            records=lambda config, kind: [(None, record) for record in (approved if kind == 'approved' else pending)],
            approve=lambda config, value, branch, run: approved.append(dict(value, policy='security')),
            consume_pending=lambda config, nonce: pending.clear())
        recorder = []
        review = types.SimpleNamespace(run=mock.Mock())
        def dispatch(config, value, temporary, review, state, uid, pid):
            deploy.disruption_check(config, value, review, uid, pending=True)
            recorder.append(value['closure']); return dict(ok=True)
        original_resolve = Path.resolve
        def resolve(path, **kwargs):
            return Path('source') if str(path).endswith('activated-source') else original_resolve(path, **kwargs)
        with mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(Path, 'resolve', resolve), mock.patch.object(deploy, 'load_security', return_value=security), mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(deploy, 'load_disruption', return_value=unit), mock.patch.object(unit, 'state_directory', return_value=state), mock.patch.object(unit, 'read_record', side_effect=lambda path: json.loads(path.read_text())), mock.patch.object(unit, 'probe', return_value=proof), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'activate_bound', side_effect=dispatch):
            with self.assertRaises(deploy.DeploymentFailure): deploy.override(self.config, nonce, os.getuid(), 1)
            self.assertEqual(pending, []); self.assertEqual(recorder, [])
            result = deploy.disruption_override(self.config, nonce, os.getuid(), 1)
            self.assertTrue(result['disruptionOverride']); self.assertEqual(recorder, [str(self.candidate)])

    def test_actual_helper_gate_with_and_without_reservations(self):
        spool = self.root / 'spool'; spool.mkdir(mode=0o700)
        nonce = 'b'*64
        config = dict(self.config, target='metal', activationSpool=str(spool))
        binding = dict(nonce=nonce, target='metal', action='test', closure=str(self.candidate), source='source', reservation={}, reservationUid=os.getuid())
        real_stat = os.fstat
        def root_info(info):
            data = list(info); data[4] = 0; return os.stat_result(data)
        original_resolve = Path.resolve
        def resolve(path, **kwargs):
            return Path('source') if str(path).endswith('activated-source') else original_resolve(path, **kwargs)
        manager = types.SimpleNamespace(engine=types.SimpleNamespace(operation=mock.MagicMock()), module=types.SimpleNamespace(Rejected=ValueError))
        proof = dict(digest='exact', findings=['protected-unit-change'])
        for reservations in (False, True):
            config['reservations'] = {'fixture': True} if reservations else None
            path = spool / (nonce + '.json'); path.write_text(json.dumps(binding)); path.chmod(0o600)
            with mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(Path, 'lstat', return_value=root_info(spool.stat())), mock.patch.object(os, 'fstat', side_effect=lambda fd: root_info(real_stat(fd))), mock.patch.object(Path, 'resolve', resolve), mock.patch.object(deploy, 'activation_guard', return_value=mock.MagicMock()), mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'load_disruption', return_value=unit), mock.patch.object(unit, 'probe', return_value=proof), mock.patch.object(deploy, 'activate') as recorder:
                with self.assertRaises(deploy.DeploymentFailure): deploy.activate_reserved(config, nonce)
                recorder.assert_not_called()
            approved = dict(binding, disruptionApproval='exact')
            path.write_text(json.dumps(approved)); path.chmod(0o600)
            with mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(Path, 'lstat', return_value=root_info(spool.stat())), mock.patch.object(os, 'fstat', side_effect=lambda fd: root_info(real_stat(fd))), mock.patch.object(Path, 'resolve', resolve), mock.patch.object(deploy, 'activation_guard', return_value=mock.MagicMock()), mock.patch.object(deploy, 'reservation_manager', return_value=manager), mock.patch.object(deploy, 'recheck_bound'), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'load_disruption', return_value=unit), mock.patch.object(unit, 'probe', return_value=proof), mock.patch.object(deploy, 'activate') as recorder:
                deploy.activate_reserved(config, nonce); recorder.assert_called_once()
    def test_authenticated_override_single_consumption_and_state_binding(self):
        state = self.root / 'state'; state.mkdir()
        info = self.root / 'info'; info.mkdir()
        work = self.root / 'work'; work.mkdir()
        self.config.update(disruptionState=str(state), disruptionInfo=str(info), work=str(work), target='metal', clientUid=os.getuid())
        nonce = 'c'*64
        proof = dict(digest='exact', findings=['protected-unit-change'])
        binding = dict(nonce=nonce, target='metal', action='test', closure=str(self.candidate), source='source', disruptionProof=proof, disruptionUid=os.getuid())
        record = state / (nonce + '.json'); record.write_text(json.dumps(binding))
        original_resolve = Path.resolve
        def resolve(path, **kwargs):
            return Path('source') if str(path).endswith('activated-source') else original_resolve(path, **kwargs)
        with mock.patch.object(os, 'geteuid', return_value=0), mock.patch.object(Path, 'resolve', resolve), mock.patch.object(deploy, 'load_disruption', return_value=unit), mock.patch.object(unit, 'state_directory', return_value=state), mock.patch.object(unit, 'read_record', side_effect=lambda path: json.loads(path.read_text())), mock.patch.object(unit, 'probe', return_value=proof) as probe, mock.patch.object(deploy, 'load_review', return_value=object()), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'recheck_bound') as baseline, mock.patch.object(deploy, 'activate_bound', return_value=dict(ok=True)) as recorder:
            probe.return_value = dict(proof, digest='later-closure-runtime-policy')
            with self.assertRaises(deploy.DeploymentFailure): deploy.disruption_override(self.config, nonce, os.getuid(), 1)
            recorder.assert_not_called(); self.assertTrue(record.exists())
            probe.return_value = proof
            baseline.side_effect = ValueError('profile-changed')
            with self.assertRaises(ValueError): deploy.disruption_override(self.config, nonce, os.getuid(), 1)
            baseline.side_effect = None
            result = deploy.disruption_override(self.config, nonce, os.getuid(), 1)
            self.assertTrue(result['disruptionOverride']); recorder.assert_called_once(); self.assertFalse(record.exists())
            with self.assertRaises(FileNotFoundError): deploy.disruption_override(self.config, nonce, os.getuid(), 1)

    def test_boot_and_routine_update_skip_probe(self):
        for action in ('boot', 'update'):
            with mock.patch.object(deploy, 'load_disruption') as module:
                deploy.disruption_check(self.config, dict(action=action)); module.assert_not_called()
    def test_security_denial_cannot_be_disruption_override(self):
        config = dict(modelReviewEnabled=True)
        security = types.SimpleNamespace(identity_version=lambda config: 1, validate_transition=lambda *args: None, policy_digest=lambda config: 'policy', records=lambda config, kind: [])
        with mock.patch.object(deploy, 'load_security', return_value=security):
            with self.assertRaises(deploy.DeploymentFailure):
                deploy.disruption_security_recheck(config, dict(disruptionSecurityPolicy='policy'))
    def test_security_policy_change(self):
        security = types.SimpleNamespace(identity_version=lambda config: 1, validate_transition=lambda *args: None, policy_digest=lambda config: 'new-policy')
        with mock.patch.object(deploy, 'load_security', return_value=security):
            with self.assertRaises(deploy.DeploymentFailure):
                deploy.disruption_security_recheck(dict(modelReviewEnabled=True), dict(disruptionSecurityPolicy='old-policy'))

if __name__ == '__main__': unittest.main()
