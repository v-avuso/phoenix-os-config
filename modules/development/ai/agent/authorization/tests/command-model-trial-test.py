"""Offline fixed-helper safety; no root, model, credentials or native dialog."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('trial',Path(__file__).with_name('command-model-trial.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Safety(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.public=dict(version=1,gateBwrap='/fixed/gate-bwrap',gateCodex='/fixed/gate-codex',trialAuthority=str(self.root/'authority'),
            controller='/fixed/controller',config=str(self.root/'config'),executable='/fixed/id',provider='/fixed/codex',operatorUid=1000)
        self.config=dict(operatorUid=1000,clientUid=1000,modelReviewEnabled=True,adapter='codex',model='gpt-6-luna',effort='high',
            reviewerUser='phoenix-deploy-review',reviewHome='/var/lib/phoenix-deploy-review',codex='/fixed/codex',
            commandLibrary='/fixed/library',commandExec='/fixed/executor',reviewScript='/fixed/review',commandReviewPolicy='/fixed/policy',
            python='/fixed/python',systemdRun='/fixed/systemd-run',systemctl='/fixed/systemctl',setpriv='/fixed/setpriv',work='/host/requests',commandState='/host/cache',
            commands=dict(enable=True,entries={'identity-review':dict(executable='/fixed/id',arguments=['-u'],rationale='Read UID only',mode='review',timeout=10)}))
        Path(self.public['trialAuthority']).write_text(json.dumps(dict(registry=self.config['commands'])))
    def test_requires_root_and_exact_authenticated_operator(self):
        for uid,authenticated in ((1000,'1000'),(0,None),(0,'1001'),(0,'1000\n')):
            with self.assertRaisesRegex(ValueError,'operator-authentication-required'):
                m.require_operator(self.config,uid,authenticated)
        m.require_operator(self.config,0,'1000')
    def test_fixed_definition_provider_and_identity(self):
        with patch.object(m,'immutable',side_effect=Path):
            m.validate_config(self.public,self.config)
            for mutation in (lambda c:c.update(clientUid=1001),lambda c:c.update(model='other'),lambda c:c.update(effort='low'),
                    lambda c:c.update(modelReviewEnabled=False),lambda c:c['commands']['entries']['identity-review'].update(arguments=['-u','extra']),
                    lambda c:c['commands']['entries']['identity-review'].update(mode='automatic'),lambda c:c['commands']['entries'].update(extra={})):
                altered=copy.deepcopy(self.config);mutation(altered)
                with self.assertRaisesRegex(ValueError,'trial-config-invalid'):m.validate_config(self.public,altered)
    def test_dry_run_has_no_auth_model_or_state_path(self):
        Path(self.public['config']).write_text(json.dumps(self.config))
        descriptor=self.root/'descriptor';descriptor.write_text(json.dumps(self.public))
        output=io.StringIO()
        with patch.object(m,'immutable',side_effect=Path),patch.object(m,'require_operator',side_effect=AssertionError('auth')),patch.object(m,'controlled_trial',side_effect=AssertionError('model')),patch.object(m.subprocess,'Popen',side_effect=AssertionError('process')),contextlib.redirect_stdout(output):
            self.assertEqual(m.main(descriptor,dry_run=True),0)
        result=json.loads(output.getvalue());self.assertEqual(result['modelInvocations'],0);self.assertFalse(result['activation'])
        self.assertFalse((self.root/'requests').exists())
    def test_private_configuration_preserves_original_and_permissions(self):
        original=copy.deepcopy(self.config);root=self.root/'trial';root.mkdir()
        reviewer=types.SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
        with patch.object(m.os,'chown'):
            trial,used=m.private_config(self.config,self.public,root,reviewer)
        self.assertEqual(self.config,original)
        self.assertEqual(stat.S_IMODE((root/'requests').stat().st_mode),0o711)
        self.assertEqual(stat.S_IMODE((root/'cache').stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE((root/'config.json').stat().st_mode),0o444)
        self.assertEqual(stat.S_IMODE(used.stat().st_mode),0o600)
        self.assertEqual(used.read_text(),'0');self.assertEqual(trial['codex'],self.public['gateCodex'])
        self.assertEqual((root/'current-authority').resolve(),Path(self.public['trialAuthority']))
    def test_cleanup_never_selects_unrelated_unit(self):
        with patch.object(m.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'trial-unit-invalid'):m.cleanup_units(self.config,{'unrelated.service'})
            run.assert_not_called()

    def test_owned_unit_cleanup_checks_inactive_and_rejects_failure(self):
        unit='phoenix-command-'+'a'*32+'.service'
        def run(argv,**kwargs):return types.SimpleNamespace(returncode=3 if argv[1]=='is-active' else 0)
        with patch.object(m.subprocess,'run',side_effect=run) as runner:
            m.cleanup_units(self.config,{unit})
            self.assertEqual(runner.call_count,3)
            self.assertTrue(all(unit in call.args[0] for call in runner.call_args_list))
        with patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)):
            with self.assertRaisesRegex(ValueError,'trial-cleanup-failed'):m.cleanup_units(self.config,{unit})

if __name__=='__main__':unittest.main()
