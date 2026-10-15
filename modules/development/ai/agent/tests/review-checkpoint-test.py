"""Offline tests only: no auth, Nix, root operations or model calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('checkpoint_trial', Path(__file__).with_name('review-checkpoint.py'))
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class CheckpointTrialTests(unittest.TestCase):
    def test_authentication_and_config_are_required(self):
        config = dict(operatorUid=1000, modelReviewEnabled=True, model='gpt-6-luna', effort='high')
        trial.require_operator(config, 0, '1000')
        for uid, authenticated in ((1000, '1000'), (0, None), (0, '989')):
            with self.assertRaisesRegex(ValueError, 'operator-authentication-required'):
                trial.require_operator(config, uid, authenticated)
        with self.assertRaisesRegex(ValueError, 'trial-config-invalid'):
            trial.require_operator(dict(config, modelReviewEnabled=False), 0, '1000')

    def test_private_paths_do_not_reenter_global_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, lock = trial.private_config(dict(work='/var/lib/phoenix-deploy/requests'), root)
            self.assertEqual(lock, Path('/var/lib/phoenix-deploy/deployment.lock'))
            self.assertEqual(Path(config['work']).parent, root)
            self.assertNotEqual(lock, root / 'deployment.lock')
            self.assertEqual((Path(config['securityReviewState']).stat().st_mode & 0o777), 0o700)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'lock-identities-overlap'):
                trial.private_config(dict(work=str(Path(directory) / 'requests')), Path(directory))

    def test_checkpoint_binding_modes_and_real_symlink_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'state'; state.mkdir(mode=0o700)
            source = root / 'source'; source.mkdir()
            closure = root / 'closure'; closure.mkdir()
            record = state / ('a' * 64 + '.approved.json')
            record.write_text(json.dumps(dict(source=str(source), closure=str(closure))))
            record.chmod(0o600)
            record.with_suffix('.source').symlink_to(source)
            record.with_suffix('.closure').symlink_to(closure)
            original = Path.lstat
            def root_owned(path):
                values = list(original(path)); values[4] = 0
                return os.stat_result(values)
            with mock.patch.object(Path, 'lstat', root_owned):
                trial.verify_records(state, str(source), str(closure))
                with self.assertRaisesRegex(ValueError, 'checkpoint-binding-mismatch'):
                    trial.verify_records(state, str(source), '/different')
                record.chmod(0o644)
                with self.assertRaisesRegex(ValueError, 'checkpoint-owner-invalid'):
                    trial.verify_records(state, str(source), str(closure))

    def test_dry_run_never_authenticates_or_loads_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            descriptor = root / 'descriptor'; config = root / 'config'; controller = root / 'controller'
            descriptor.write_text(json.dumps(dict(config=str(config), controller=str(controller))))
            config.write_text('{}'); controller.write_text('not executed')
            with mock.patch.object(trial, 'immutable', side_effect=Path), \
                 mock.patch.object(trial, 'require_operator', side_effect=AssertionError('no auth')), \
                 mock.patch.object(trial.importlib.util, 'spec_from_file_location', side_effect=AssertionError('no controller')), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(trial.main(str(descriptor), True), 0)
            self.assertEqual(json.loads(output.getvalue())['modelInvocations'], 0)

    def test_candidate_changes_only_readme_and_preserves_modes(self):
        review = SimpleNamespace(baseline_files=lambda _: {'README.md': 'original', 'flake.nix': 'nix'},
                                 source_modes=lambda *_: {'README.md': '100644', 'flake.nix': '100755'})
        files, modes = trial.candidate(review, '/immutable')
        self.assertEqual(files['flake.nix'], 'nix')
        self.assertTrue(files['README.md'].startswith('original\n<!--'))
        self.assertEqual(modes['flake.nix'], '100755')

    def test_prebuild_plan_is_offline_and_uses_source_name(self):
        review = SimpleNamespace(baseline_files=lambda _: {'README.md': 'baseline'},
                                 source_modes=lambda *_: {'README.md': '100644'},
                                 run=mock.Mock(return_value=b'/nix/store/frozen-source\n'))
        result = trial.integration(None, review, dict(nix='/immutable/nix', target='metal'), {}, None,
                                   '/baseline', None, None, plan=True)
        self.assertEqual(review.run.call_args.args[0][:6],
                         ['/immutable/nix', '--offline', 'store', 'add-path', '--name', 'source'])
        self.assertIn('--offline', result['buildArgv'])
        self.assertEqual(result['modelInvocations'], 0)
        self.assertFalse(result['activation'])

    def test_shared_gate_allows_only_one_competing_process(self):
        gate = Path(__file__).with_name('review-call-gate.py')
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / 'used'; token.write_text('0'); token.chmod(0o600)
            code = ("import importlib.util,pathlib,sys; "
                    "s=importlib.util.spec_from_file_location('g',sys.argv[1]); "
                    "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                    "m.consume(pathlib.Path(sys.argv[2]))")
            children = [subprocess.Popen([sys.executable, '-B', '-c', code, str(gate), str(token)],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(2)]
            self.assertEqual(sorted(child.wait(timeout=5) for child in children), [0, 1])
            self.assertEqual(token.read_text(), '1')

    def test_real_authorization_dispatch_distinguishes_fixture_auth_from_daemon_caller(self):
        spec = importlib.util.spec_from_file_location('real_deployment', Path(__file__).resolve().parents[1] / 'deployment.py')
        deploy = importlib.util.module_from_spec(spec); spec.loader.exec_module(deploy)
        config = dict(target='metal', modelReviewEnabled=True, operatorUid=1000, clientUid=2000,
                      authorizationPolicy=deploy.authorization.default_policy(True, 2000, 1000))
        request = dict(files={'flake.nix': '{}', 'flake.lock': '{}'},
                       modes={'flake.nix': '100644', 'flake.lock': '100644'},
                       commit='a' * 40, target='metal', action='test', task='review-integration-trial',
                       reason='Offline authorization entrance regression')
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / 'used'; token.write_text('0')
            with mock.patch.object(deploy, 'process_inner', return_value={'offline': True}) as inner:
                with self.assertRaises(deploy.DeploymentFailure) as rejected:
                    deploy.process(config, request, 1000, 123, operator=True)
                self.assertEqual((rejected.exception.stage, rejected.exception.code), ('request', 'rejected-or-failed'))
                inner.assert_not_called()
                self.assertEqual(token.read_text(), '0')
                self.assertEqual(deploy.process(config, request, 2000, 123), {'offline': True})
                inner.assert_called_once()
                self.assertEqual(inner.call_args.args[2], 2000)
                self.assertEqual(token.read_text(), '0')

    def test_real_process_entry_and_guarded_recording_boundary_are_composed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dict(reviewerUser='reviewer', builderUser='builder', target='metal',
                          operatorUid=1000, clientUid=2000, securityReviewState=str(root / 'checkpoints'))
            public = dict(gateBwrap='/immutable/bwrap-gate', gateCodex='/immutable/codex-gate', offlineNix='/immutable/nix-offline')
            review = SimpleNamespace(baseline_files=lambda _: {'README.md': 'baseline'},
                                     source_modes=lambda *_: {'README.md': '100644'})
            deploy = SimpleNamespace(trust_active=mock.Mock(), recheck_bound=mock.Mock(),
                                     activation_guard=mock.Mock(return_value=contextlib.nullcontext()))
            calls = []
            def process(cfg, request, uid, pid, operator=False):
                self.assertFalse(operator); self.assertEqual(uid, 2000)
                self.assertEqual(cfg['codex'], public['gateCodex'])
                self.assertEqual(Path(cfg['configPath']).stat().st_mode & 0o777, 0o444)
                self.assertEqual(request['files']['README.md'], 'baseline\n<!-- Isolated review integration acceptance; no configuration change. -->\n')
                if not calls:
                    (root / 'budget/used').write_text('1')
                calls.append(request['branch'])
                return deploy.activate_bound(cfg, dict(source='/source', closure='/closure'), None, review, {}, uid, pid)
            deploy.process = process
            with mock.patch.object(trial.pwd, 'getpwnam', side_effect=lambda name: SimpleNamespace(pw_uid=989 if name == 'reviewer' else 988, pw_gid=983)), \
                 mock.patch.object(trial.os, 'chown') as ownership, mock.patch.object(trial, 'verify_records') as verify, \
                 mock.patch.object(Path, 'resolve', side_effect=lambda *args, **kwargs: Path('/unchanged')):
                receipt = trial.integration(deploy, review, config, public, root, '/baseline', '/unchanged', '/unchanged')
            ownership.assert_called_once_with(root / 'budget/used', 989, 983)
            self.assertEqual((root / 'budget').stat().st_mode & 0o777, 0o755)
            self.assertEqual((root / 'budget/used').stat().st_mode & 0o777, 0o600)
            self.assertEqual(calls, ['review-integration-a', 'review-integration-b'])
            self.assertEqual(deploy.recheck_bound.call_count, 2)
            self.assertEqual(deploy.activation_guard.call_count, 2)
            self.assertFalse(receipt['activation']); self.assertEqual(receipt['modelInvocations'], 1)
            self.assertEqual(receipt['reviewerUid'], 989)
            verify.assert_called_once()


if __name__ == '__main__':
    unittest.main()
