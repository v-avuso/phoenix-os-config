"""Offline recovery acceptance; no authentication, model or host activation."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_bootstrap', OWNER / 'recovery/source-bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)
spec = importlib.util.spec_from_file_location('deploy', OWNER / 'deployment.py')
deploy = importlib.util.module_from_spec(spec); spec.loader.exec_module(deploy)


class RecoveryTests(unittest.TestCase):
    def descriptor(self):
        return dict(installedPolicy='old-policy', candidatePolicy='new-policy',
                    approvedSource='old-source', approvedClosure='old-closure',
                    candidateSource='new-source', candidateClosure='new-closure',
                    baseline='active-source', profile='profile', commit='a' * 40)

    def test_root_record_must_match_source_closure_policy_and_target(self):
        d = self.descriptor()
        record = dict(policy='old-policy', target='metal', source='old-source', closure='old-closure')
        security = mock.Mock()
        for field in ('policy', 'target', 'source', 'closure'):
            security.records.side_effect = lambda config, suffix: [(None, dict(record, **{field: 'different'}))] if suffix == 'approved' else []
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'previous-protected-approval-required'):
                bootstrap.approved_baseline(d, {'target': 'metal'}, security)
        security.records.side_effect = lambda config, suffix: [(None, record)] if suffix == 'approved' else []
        bootstrap.approved_baseline(d, {'target': 'metal'}, security)
        security.records.side_effect = lambda config, suffix: [(None, record)] if suffix == 'approved' else [(None, dict(source='new-source', code='model-denied'))]
        with self.assertRaisesRegex(ValueError, 'retained-denial'):
            bootstrap.approved_baseline(d, {'target': 'metal'}, security)

    def test_candidate_service_must_bind_exact_controller_configuration_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unit = root / 'etc/systemd/system/phoenix-deploy.service'
            unit.parent.mkdir(parents=True)
            config = dict(python='python', controller='controller')
            for tail in ('python -I controller config serve', 'python -I controller other serve',
                         'python -I forged config serve', 'python -I controller config operator',
                         'python -I controller config serve extra'):
                unit.write_text('ExecStart=' + tail + '\n')
                with mock.patch.object(bootstrap, 'immutable', side_effect=Path):
                    if tail == 'python -I controller config serve':
                        bootstrap.service_binding(str(root), 'config', config)
                    else:
                        with self.assertRaisesRegex(ValueError, 'binding-mismatch'):
                            bootstrap.service_binding(str(root), 'config', config)

    def trial(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'requests'; work.mkdir()
            old = dict(work=str(work), operatorUid=1000, target='metal', reviewerUser='reviewer',
                       python='installed-python', controller='installed-controller', configPath='installed-config', reviewHome='/protected/auth', nixStore='installed-nix-store')
            new = dict(old, reviewerUser='reviewer', python='python', controller='fixed-controller',
                       configPath='fixed-config', reviewHome='/protected/auth', nixStore='nix-store')
            d = self.descriptor()
            active = root / 'active'; active.mkdir()
            marker = root / 'profile/etc/phoenix-agent'; marker.mkdir(parents=True)
            (marker / 'activated-source').symlink_to(active)
            d['profile'] = str(root / 'profile')
            review = deploy.load_review({'reviewScript': str(OWNER / 'deploy-review.py')})
            review.baseline_files = mock.Mock(side_effect=lambda path: {'flake.nix': str(path)})
            review.source_modes = mock.Mock(return_value={'flake.nix': '100644'})
            review.run = mock.Mock(return_value=b'')
            security = mock.Mock()
            security.records.side_effect = lambda config, suffix: [(None, dict(policy='old-policy', target='metal', source='old-source', closure='old-closure'))] if suffix == 'approved' else []
            controller = mock.Mock()
            controller.load_review.return_value = review
            controller.load_security.return_value = security
            security.policy_digest.return_value = 'unsupported-scheme' if mode == 'unsupported-scheme' else d['candidatePolicy']
            controller.activation_guard.side_effect = lambda config: contextlib.nullcontext(42)
            events = []
            def worker(config, user, argv, runner, **kwargs):
                events.append('review')
                payload = json.loads(kwargs['data'])
                self.assertEqual(payload['binding']['reviewBase'], 'old-source')
                self.assertEqual(argv[:4], ['installed-python', '-I', 'installed-controller', 'installed-config'])
                self.assertEqual(config['controller'], 'installed-controller')
                self.assertEqual(payload['baseline']['flake.nix'], 'old-source')
                self.assertIn('+new-source', payload['diff'])
                self.assertEqual(Path(argv[-1]).name, 'review')
                self.assertEqual((Path(argv[-1]).stat().st_mode & 0o777), 0o700)
                verdict = dict(payload['binding'], approved=mode != 'deny', summary='offline double')
                if mode == 'forged': verdict['source'] = 'attacker-source'
                if mode == 'worker-error': return json.dumps(dict(status='error', code='review-timeout')).encode()
                return json.dumps(dict(status='verdict', verdict=verdict)).encode()
            controller.as_user.side_effect = worker
            security.approve_transition.side_effect = lambda *_args, **_kwargs: events.append('checkpoint')
            def activate(config, binding, temporary, *_args):
                self.assertEqual(binding['source'], 'new-source')
                self.assertEqual(binding['closure'], 'new-closure')
                self.assertEqual(binding['action'], 'switch')
                self.assertNotEqual(temporary.name, 'review')
                events.append('activation')
                return {'ok': True}
            controller.activate_bound.side_effect = activate
            checked = mock.Mock(side_effect=[None, ValueError('recovery-active-state-changed')] if mode == 'changed-state' else None)
            with mock.patch.object(bootstrap.os, 'geteuid', return_value=0), \
                 mock.patch.object(bootstrap.os, 'chown'), \
                 mock.patch.object(bootstrap.pwd, 'getpwnam', return_value=mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())), \
                 mock.patch.object(bootstrap, 'load', side_effect=lambda path: controller if events == ['review'] else self.fail('candidate code loaded before verdict')), \
                 mock.patch.object(bootstrap, 'verify_completion') as complete, \
                 mock.patch.object(bootstrap, 'recheck', checked):
                if mode == 'pass':
                    self.assertTrue(bootstrap.recover(d, old, new, controller, security, 1000)['ok'])
                    self.assertEqual(events, ['review', 'checkpoint', 'activation'])
                    complete.assert_called_once()
                else:
                    with self.assertRaises(ValueError):
                        bootstrap.recover(d, old, new, controller, security, 1000)
                    self.assertEqual(events, ['review'])
                    security.approve_transition.assert_not_called(); controller.activate_bound.assert_not_called()
                    complete.assert_not_called()
                    if mode == 'deny': security.pending.assert_called_once()

    def test_review_checkpoint_activation_order(self):
        self.trial('pass')

    def test_denied_forged_failed_or_stale_review_never_authorizes_activation(self):
        for mode in ('deny', 'forged', 'worker-error', 'changed-state', 'unsupported-scheme'):
            with self.subTest(mode=mode): self.trial(mode)

    def test_wrong_identity_cannot_read_checkpoints_or_review(self):
        for effective, uid in ((1000, 1000), (0, 2000)):
            security = mock.Mock(); controller = mock.Mock()
            with mock.patch.object(bootstrap.os, 'geteuid', return_value=effective), self.assertRaises(ValueError):
                bootstrap.recover(self.descriptor(), {'operatorUid': 1000}, {}, controller, security, uid)
            controller.load_review.assert_not_called(); security.records.assert_not_called()


if __name__ == '__main__': unittest.main()
