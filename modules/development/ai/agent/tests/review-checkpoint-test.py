"""Offline tests only: no auth, Nix, root operations or model calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
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


if __name__ == '__main__':
    unittest.main()
