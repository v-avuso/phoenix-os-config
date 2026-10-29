"""Versioned authority/tool identities and bounded distributor receipts; no OS activation."""
import contextlib
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

OWNER = Path(__file__).resolve().parents[1]
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, OWNER / filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

security = load('security', 'security-review.py')
deploy = load('deploy', 'deployment.py')
review = load('review', 'deploy-review.py')


class ToolchainTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = self.root / 'state'; self.state.mkdir(mode=0o700)
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(security, 'state_directory', return_value=self.state))
        self.stack.enter_context(mock.patch.object(security, 'read_record', side_effect=lambda path: json.loads(path.read_text())))
        self.stack.enter_context(mock.patch.object(security, 'immutable_file', side_effect=lambda path: Path(path).resolve(strict=True)))
        self.stack.enter_context(mock.patch.object(security.os, 'geteuid', return_value=0))
        self.before = self.configuration('before'); self.after = self.configuration('after')
        self.verify = lambda value, kind: Path(value).resolve(strict=True)

    def configuration(self, name):
        root = self.root / name; root.mkdir()
        source = root / 'source'; source.mkdir(); (source / 'flake.lock').write_text(name)
        closure = root / 'closure'; marker = closure / 'etc/phoenix-agent'; marker.mkdir(parents=True)
        (marker / 'activated-source').symlink_to(source)
        cfg = dict(securityIdentityVersion=2, target='metal', system='x86_64-linux',
                   modelReviewEnabled=True, operatorUid=1000, clientUid=1000, updaterUid=1000,
                   adapter='codex', model='fixed-model', effort='high', reviewerUser='reviewer',
                   builderUser='builder', securityReviewState=str(self.state), source=str(source), closure=str(closure),
                   activationEnvironment={'PATH': '/fixed/path', 'HOME': '/root'})
        for key, filename in [('authorizationLibrary', 'authorization/request.py'),
                              ('deploymentTransportPolicy', 'transport.json'),
                              ('sourceManifestLibrary', 'source-manifest.py')]:
            path = root / key; path.write_bytes((OWNER / filename).read_bytes()); cfg[key] = str(path)
        for key, filename in [('controller', 'deployment.py'), ('reviewScript', 'deploy-review.py'),
                              ('securityReviewScript', 'security-review.py'), ('routineUpdateScript', 'routine-update.py'),
                              ('policy', 'review-policy.md')]:
            contents = (OWNER / filename).read_text()
            for binding in ('authorizationLibrary', 'deploymentTransportPolicy', 'sourceManifestLibrary'):
                contents = contents.replace('@' + binding + '@', cfg[binding])
            path = root / key; path.write_text(contents); cfg[key] = str(path)
        for key in ('python', 'nix', 'nixStore', 'bwrap', 'setpriv', 'systemdRun', 'codex', 'caBundle'):
            path = root / key; path.write_text('tool stub'); cfg[key] = str(path)
        locale = root / 'locale'; locale.write_text('locale stub')
        cfg['activationEnvironmentTools'] = {'LOCALE_ARCHIVE': str(locale)}
        self.save(cfg)
        return cfg

    def save(self, cfg):
        path = Path(cfg['source']).parent / 'config.json'; path.write_text(json.dumps(cfg))
        unit = Path(cfg['closure']) / 'etc/systemd/system/phoenix-deploy.service'; unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text('ExecStart=%s -I %s %s serve\n' % (cfg['python'], cfg['controller'], path))

    def run_store(self, argv):
        if '--add-root' in argv:
            path = Path(argv[argv.index('--add-root') + 1]); path.symlink_to(argv[-1])

    def seed(self, cfg):
        security.approve(cfg, cfg, 'main', self.run_store)

    def update(self, before, after):
        binding = dict(after, action='update')
        return security.approve_update(before, binding,
            {'source': before['source'], 'closure': before['closure']}, 'updates', self.run_store, self.verify)

    def test_package_paths_and_declared_helper_relocation_do_not_change_authority(self):
        self.assertEqual(security.policy_digest(self.before), security.policy_digest(self.after))
        self.assertNotEqual(security.toolchain_digest(self.before), security.toolchain_digest(self.after))
        with mock.patch.object(deploy, 'load_security', return_value=security), mock.patch.object(deploy, 'successor_config', return_value=self.after):
            with self.assertRaises(deploy.DeploymentFailure) as failure:
                deploy.require_policy_continuity(self.before, self.after['closure'])
            self.assertEqual(failure.exception.code, 'toolchain-transition-required')
            deploy.require_policy_continuity(self.before, self.after['closure'], validated_update=True)

    def test_reservation_helper_bytes_and_semantics_survive_packaging_relocation(self):
        configs = []
        for name, cfg in (('before', self.before), ('after', self.after)):
            settings = dict(state='/protected/reservations', mapping={'deployment.update': 'system-testing'})
            for key, filename in (('engine', 'reservations.py'), ('adapter', 'reservation-client.py')):
                path = self.root / name / key
                path.write_bytes((OWNER / filename).read_bytes()); settings[key] = str(path)
            configs.append(dict(cfg, reservations=settings))
        self.assertEqual(security.policy_digest(configs[0]), security.policy_digest(configs[1]))
        changed = dict(configs[1], reservations=dict(configs[1]['reservations'], state='/other'))
        self.assertNotEqual(security.policy_digest(configs[0]), security.policy_digest(changed))
        Path(configs[1]['reservations']['engine']).write_text('changed enforcement')
        self.assertNotEqual(security.policy_digest(configs[0]), security.policy_digest(configs[1]))

    def test_authority_changes_and_wrong_helper_bindings_remain_changes(self):
        digest = security.policy_digest(self.before)
        for key in ('model', 'effort', 'operatorUid', 'clientUid', 'updaterUid', 'reviewerUser', 'builderUser', 'target'):
            with self.subTest(key=key):
                self.assertNotEqual(digest, security.policy_digest(dict(self.before, **{key: 'changed'})))
        self.assertNotEqual(digest, security.policy_digest(dict(self.before, activationEnvironment={'HOME': '/other'})))
        for key in ('routineUpdateScript', 'authorizationLibrary', 'controller'):
            path = Path(self.after[key]); original = path.read_bytes(); path.write_bytes(original + b'\n# authority change')
            self.assertNotEqual(digest, security.policy_digest(self.after)); path.write_bytes(original)
        path = Path(self.after['controller']); original = path.read_text()
        path.write_text(original.replace(self.after['authorizationLibrary'], '/unbound/helper'))
        with self.assertRaisesRegex(ValueError, 'helper-binding'):
            security.policy_digest(self.after)
        with self.assertRaisesRegex(ValueError, 'identity-version'):
            security.policy_digest(dict(self.before, securityIdentityVersion=3))

    def test_two_updates_survive_pruning_without_recursive_adoption(self):
        self.seed(self.before)
        third = self.configuration('third')
        with mock.patch.object(security, 'RETENTION', 1):
            self.update(self.before, self.after)
            self.update(self.after, third)
        entries = security.records(third, 'approved'); self.assertEqual(len(entries), 1)
        record = entries[0][1]
        self.assertEqual(record['origin'], 'distributor-update')
        self.assertEqual(record['toolchain'], security.toolchain_digest(third))
        self.assertNotIn('transition', record['predecessorApproval'])
        self.assertTrue(any(p.name.endswith('.predecessorClosure') for p in self.state.iterdir()))
        security.validate_transition(third, record, self.verify)
        exact, _, _ = security.choose_checkpoint(third, 'metal', third['source'], third['closure'], 'other',
            third['source'], review.baseline_files(Path(third['source'])), review, self.verify)
        self.assertTrue(exact)

    def test_explicit_versioned_administrator_handover_keeps_legacy_evidence(self):
        legacy = dict(self.before, securityIdentityVersion=1)
        self.save(legacy); self.seed(legacy)
        old_policy = security.legacy_policy_digest(legacy)
        self.assertEqual(security.policy_digest(legacy), old_policy)
        security.approve_transition(self.after, self.after, 'migration', self.run_store,
            predecessor_policy=old_policy, predecessor_source=legacy['source'],
            predecessor_closure=legacy['closure'], uid=1000, verify_source=self.verify)
        receipt = next(r for _, r in security.records(self.after, 'approved') if 'transition' in r)
        security.validate_transition(self.after, receipt, self.verify)
        self.assertEqual(receipt['transition']['predecessorPolicy'], old_policy)
        self.update(self.after, self.configuration('after-migration'))

    def test_pending_decisions_and_disruption_bind_the_current_tools(self):
        binding = dict(self.before, action='switch', nonce='a'*64, base=self.before['source'], profile=self.before['closure'])
        security.pending(self.before, binding, 1000, 'main', 'model-denied', 'test', self.run_store)
        security.load_pending(self.before, 'a'*64, 1000, self.verify)
        with self.assertRaisesRegex(ValueError, 'toolchain'):
            security.load_pending(self.after, 'a'*64, 1000, self.verify)
        disruption = dict(binding, disruptionSecurityPolicy=security.policy_digest(self.before),
                          disruptionSecurityToolchain=security.toolchain_digest(self.before))
        with mock.patch.object(deploy, 'load_security', return_value=security):
            with self.assertRaises(deploy.DeploymentFailure) as error:
                deploy.disruption_security_recheck(self.after, disruption)
            self.assertEqual(error.exception.code, 'security-toolchain-changed')

    def test_recheck_rejects_a_predecessor_that_is_no_longer_installed(self):
        third = self.configuration('third')
        binding = dict(self.before, action='update', base=self.before['source'], profile=third['closure'],
                       profileSource=third['source'], updatePredecessor={key: self.after[key] for key in ('source', 'closure')})
        cfg = dict(self.before, baseline=self.before['source'])
        original = Path.resolve
        def resolve(path, *args, **kwargs):
            if str(path) in ('/run/current-system', '/nix/var/nix/profiles/system'):
                return Path(third['closure'])
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'resolve', resolve), self.assertRaisesRegex(ValueError, 'no-longer-installed'):
            deploy.recheck_bound(cfg, binding)

    def test_missing_predecessor_changed_authority_and_forged_receipts_fail(self):
        with self.assertRaisesRegex(ValueError, 'approved-predecessor'):
            self.update(self.before, self.after)
        self.seed(self.before)
        changed = dict(self.after, model='changed'); self.save(changed)
        with self.assertRaisesRegex(ValueError, 'policy'):
            self.update(self.before, changed)
        self.save(self.after)
        self.update(self.before, self.after)
        record = next(r for _, r in security.records(self.after, 'approved') if r.get('origin') == 'distributor-update')
        for field in ('toolchain', 'policy', 'predecessorToolchain', 'source', 'closure', 'target', 'identityVersion'):
            invalid = copy.deepcopy(record); invalid[field] = 'forged'
            with self.subTest(field=field), self.assertRaises((ValueError, OSError)):
                security.validate_transition(self.after, invalid, self.verify)
        invalid = copy.deepcopy(record); invalid['predecessorApproval']['policy'] = 'forged'
        with self.assertRaises(ValueError): security.validate_transition(self.after, invalid, self.verify)
        invalid = copy.deepcopy(record); invalid['identityVersion'] = 1
        with self.assertRaises(ValueError): security.validate_transition(self.after, invalid, self.verify)
        request = dict(files={}, modes={}, commit='a'*40, action='update', target='metal', reason='probe',
                       expectedBase='source', expectedProfile='profile', toolchainReceipt=record)
        with self.assertRaises(ValueError): deploy.request_valid(request, 'metal')


if __name__ == '__main__': unittest.main()
