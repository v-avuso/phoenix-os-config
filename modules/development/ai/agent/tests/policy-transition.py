"""Disposable policy handover: real records/digests/selector, OS/store/auth stubs."""
import contextlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, OWNER / file)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
security = module('security', 'security-review.py')
deploy = module('deploy', 'deployment.py')
review = module('review', 'deploy-review.py')


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = self.root / 'state'; self.state.mkdir(mode=0o700)
        self.before = self.configuration('before'); self.after = self.configuration('after')
        self.mocks = contextlib.ExitStack(); self.addCleanup(self.mocks.close)
        self.mocks.enter_context(mock.patch.object(security, 'state_directory', return_value=self.state))
        self.mocks.enter_context(mock.patch.object(security, 'read_record', side_effect=lambda path: json.loads(path.read_text())))
        self.mocks.enter_context(mock.patch.object(security, 'immutable_file', side_effect=lambda path: Path(path).resolve(strict=True)))
        self.mocks.enter_context(mock.patch.object(security.os, 'geteuid', return_value=0))
        self.verify = lambda path, kind: Path(path).resolve(strict=True)
        self.binding = dict(source=self.after['source'], closure=self.after['closure'], target='metal')
        security.approve(self.before, dict(source=self.before['source'], closure=self.before['closure'], target='metal'), 'main', self.run_store)

    def configuration(self, name):
        root = self.root / name; root.mkdir()
        source = root / 'source'; source.mkdir(); (source / 'flake.nix').write_text(name)
        closure = root / 'closure'; marker = closure / 'etc/phoenix-agent'; marker.mkdir(parents=True)
        (marker / 'activated-source').symlink_to(source)
        policy = root / 'policy'; policy.write_text('fixed policy')
        controller = root / 'controller'; controller.write_text(name + ' controller')
        python = root / 'python'; python.write_text('interpreter stub')
        nix_store = root / 'nix-store'; nix_store.write_text('root registration stub')
        config = dict(target='metal', operatorUid=1000, modelReviewEnabled=True,
                      policy=str(policy), reviewScript=str(OWNER / 'deploy-review.py'),
                      securityReviewScript=str(OWNER / 'security-review.py'), controller=str(controller),
                      python=str(python), nixStore=str(nix_store), source=str(source), closure=str(closure))
        path = root / 'config.json'; path.write_text(json.dumps(config))
        unit = closure / 'etc/systemd/system/phoenix-deploy.service'; unit.parent.mkdir(parents=True)
        unit.write_text('ExecStart=%s -I %s %s serve\n' % (python, controller, path))
        return config

    def run_store(self, argv):
        root = Path(argv[argv.index('--add-root') + 1]); root.symlink_to(argv[-1])

    def transition(self, uid=1000):
        security.approve_transition(self.after, self.binding, 'main', self.run_store,
            predecessor_policy=security.policy_digest(self.before), predecessor_source=self.before['source'],
            predecessor_closure=self.before['closure'], uid=uid, verify_source=self.verify)
        return next(record for _, record in security.records(self.after, 'approved') if record.get('origin'))

    def select(self, config, source, closure):
        files = review.baseline_files(Path(source))
        return security.choose_checkpoint(config, 'metal', source, closure, 'branch', source, files, review, self.verify)

    def test_transition_preserves_review_continuity_without_relabelling_predecessor(self):
        with self.assertRaises(security.ApprovalBaselineRequired):
            self.select(self.after, self.after['source'], self.after['closure'])
        proof = self.transition()
        self.assertTrue(self.select(self.after, self.after['source'], self.after['closure'])[0])
        exact, context, _ = self.select(self.after, self.before['source'], self.before['closure'])
        self.assertFalse(exact); self.assertEqual(context, self.after['source'])
        old = next(r for _, r in security.records(self.after, 'approved') if not r.get('origin'))
        self.assertEqual(old['policy'], security.policy_digest(self.before))
        for field in ('predecessorSource', 'predecessorClosure'):
            self.assertTrue(any(p.name.endswith('.' + field) for p in self.state.iterdir()))
        self.assertEqual(proof['transition']['administratorUid'], 1000)

    def test_wrong_administrator_or_missing_predecessor_never_publishes(self):
        for uid in (2000,):
            with self.assertRaisesRegex(ValueError, 'administrator'):
                self.transition(uid)
        for path in self.state.glob('*.approved.json'): path.unlink()
        with self.assertRaisesRegex(ValueError, 'predecessor-approval'):
            self.transition()

    def test_invalid_receipts_and_changed_implementation_fail_closed(self):
        record = self.transition()
        for field in ('source', 'closure', 'target', 'successorPolicy', 'predecessorPolicy', 'administratorUid', 'version'):
            invalid = copy.deepcopy(record)
            invalid['transition'][field] = 2000 if field == 'administratorUid' else 'invalid'
            with self.subTest(field=field), self.assertRaises((ValueError, OSError)):
                security.validate_transition(self.after, invalid, self.verify)
        invalid = copy.deepcopy(record); invalid['transition']['predecessorCheckpoint']['policy'] = 'forged'
        with self.assertRaises(ValueError): security.validate_transition(self.after, invalid, self.verify)
        Path(self.before['controller']).write_text('changed predecessor')
        with self.assertRaisesRegex(ValueError, 'predecessor-policy'):
            security.validate_transition(self.after, record, self.verify)

    def test_retention_does_not_discard_transition_predecessor_roots(self):
        with mock.patch.object(security, 'RETENTION', 1): self.transition()
        self.assertEqual(len(security.records(self.after, 'approved')), 1)
        self.assertTrue(self.select(self.after, self.after['source'], self.after['closure'])[0])

    def test_second_handover_survives_pruning_without_recursive_receipts(self):
        with mock.patch.object(security, 'RETENTION', 1):
            self.transition()
            third = self.configuration('third')
            security.approve_transition(third, dict(source=third['source'], closure=third['closure'], target='metal'),
                'main', self.run_store, predecessor_policy=security.policy_digest(self.after),
                predecessor_source=self.after['source'], predecessor_closure=self.after['closure'],
                uid=1000, verify_source=self.verify)
        self.assertTrue(self.select(third, third['source'], third['closure'])[0])
        record = security.records(third, 'approved')[0][1]
        self.assertNotIn('transition', record['transition']['predecessorCheckpoint'])
        self.assertEqual(record['predecessorClosure'], self.after['closure'])

    def test_unit_cannot_substitute_config_or_controller(self):
        unit = Path(self.after['closure']) / 'etc/systemd/system/phoenix-deploy.service'
        unit.write_text(unit.read_text().replace(' serve', ' override'))
        with self.assertRaisesRegex(ValueError, 'binding-invalid'):
            security.closure_config(self.after['closure'])

    def test_gate_detects_changed_policy_without_publishing(self):
        with mock.patch.object(deploy, 'load_security', return_value=security):
            with self.assertRaises(deploy.DeploymentFailure) as failure:
                deploy.require_policy_continuity(dict(self.before, securityReviewState=str(self.state)), self.after['closure'])
            self.assertEqual(failure.exception.code, 'policy-transition-required')
            deploy.require_policy_continuity(dict(self.before, securityReviewState=str(self.state)), self.before['closure'])
        self.assertEqual(len(security.records(self.after, 'approved')), 1)


if __name__ == '__main__': unittest.main()
