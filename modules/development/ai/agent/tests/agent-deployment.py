#!/usr/bin/env python3
"""Rejection and profile-recovery fixtures; no actual activation/network."""
import importlib.util
from pathlib import Path
import json
import hashlib
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('deployment', Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/deployment.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
routine_spec = importlib.util.spec_from_file_location('routine_update', Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/routine-update.py')
routine = importlib.util.module_from_spec(routine_spec)
routine_spec.loader.exec_module(routine)


class DeploymentTests(unittest.TestCase):
    def request(self):
        return dict(files={'flake.nix': '{}', 'flake.lock': '{}'},
                    modes={'flake.nix': '100644', 'flake.lock': '100644'},
                    commit='a' * 40, action='test', target='metal', reason='Implement requested isolated controller')

    def test_optin_integration_branch_with_offline_adapter_double(self):
        owner = Path(__file__).resolve().parents[1]
        for context_round in (False, True):
            with self.subTest(context=context_round):
                review = deploy.load_review({'reviewScript': str(owner / 'deploy-review.py')})
                invocations = []
                def adapter(argv, **kwargs):
                    invocations.append(argv)
                    payload = json.loads(kwargs['data'].decode().split('Source data follows:\n', 1)[1].split('\nResolved context', 1)[0])
                    verdict = dict(payload['binding'], approved=True, summary='offline adapter double')
                    if len(invocations) == 1:
                        verdict['context'] = []
                        if context_round:
                            verdict.update(approved=None, context=[dict(source='baseline', path='context.nix', start=1, end=1)])
                    work = Path(argv[argv.index('/work') - 1])
                    (work / 'verdict.json').write_text(json.dumps(verdict))
                    return b''
                self.live_review = dict(codex='/fixed/codex', bwrap='/fixed/bwrap', caBundle='/fixed/ca',
                                        reviewHome='/var/lib/phoenix-deploy-review', model='gpt-6-luna', effort='high')
                original_is_file = Path.is_file
                def auth_metadata(path):
                    return True if str(path) == '/var/lib/phoenix-deploy-review/auth.json' else original_is_file(path)
                try:
                    with mock.patch.object(deploy, 'load_review', return_value=review), \
                         mock.patch.object(Path, 'is_file', auth_metadata), \
                         mock.patch.object(review, 'run', side_effect=adapter):
                        self.test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow()
                    self.assertEqual(self.live_receipt['modelInvocations'], 2 if context_round else 1)
                    self.assertTrue(self.live_receipt['exactReuse'])
                    self.assertTrue(self.live_receipt['stubFallbackBound'])
                finally:
                    del self.live_review

    def test_live_receipt_preserves_static_pre_adapter_category_and_fixture_line(self):
        spec = importlib.util.spec_from_file_location('live_runner', Path(__file__).with_name('agent-review-live.py'))
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        class Failure(unittest.TestCase):
            def runTest(case):
                case.live_stage = 'seed-checkpoint'
                raise deploy.DeploymentFailure('baseline', 'baseline-policy-mismatch')
        case = Failure()
        result = runner.TrialResult()
        case.run(result)
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(case.live_failure, 'baseline-policy-mismatch')
        self.assertEqual(case.live_stage, 'seed-checkpoint')
        self.assertGreater(case.live_fixture_line, 0)
        self.assertEqual(getattr(case, 'live_invocations', 0), 0)

    def test_live_runner_stops_at_same_uid_offline_failure_before_auth_or_model(self):
        spec = importlib.util.spec_from_file_location('live_runner', Path(__file__).with_name('agent-review-live.py'))
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        class OfflineFailure(unittest.TestCase):
            def runTest(case):
                case.live_stage = 'seed-checkpoint'
                raise deploy.DeploymentFailure('baseline', 'baseline-verification-failed')
        factory = mock.Mock(side_effect=lambda _: OfflineFailure())
        fixture = mock.Mock(DeploymentTests=factory)
        original_lstat = Path.lstat
        def no_auth(path):
            if str(path) == '/var/lib/phoenix-deploy-review':
                raise AssertionError('offline failure must precede auth home access')
            return original_lstat(path)
        with mock.patch.object(runner, 'configuration', return_value={'reviewHome': '/var/lib/phoenix-deploy-review'}), \
             mock.patch.object(runner.pwd, 'getpwnam', return_value=mock.Mock(pw_uid=989)), \
             mock.patch.object(runner.os, 'getuid', return_value=989), \
             mock.patch.object(runner.os, 'geteuid', return_value=989), \
             mock.patch.object(runner.importlib.util, 'spec_from_file_location', return_value=mock.Mock()), \
             mock.patch.object(runner.importlib.util, 'module_from_spec', return_value=fixture), \
             mock.patch.object(Path, 'lstat', no_auth), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(['--allow-paid-review', '--config', '/fixed/public']), 1)
        receipt = json.loads(output.getvalue())
        self.assertEqual((receipt['stage'], receipt['code'], receipt['modelInvocations']),
                         ('offline-seed-checkpoint', 'baseline-verification-failed', 0))
        factory.assert_called_once()

    def test_live_runner_requires_explicit_optin_and_immutable_auth_route(self):
        path = Path(__file__).with_name('agent-review-live.py')
        spec = importlib.util.spec_from_file_location('live_runner', path)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with mock.patch.object(runner.pwd, 'getpwnam', side_effect=AssertionError('no auth lookup')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main([]), 1)
            self.assertEqual(runner.main(['--allow-paid-review']), 1)
            self.assertEqual(runner.main(['--dry-run']), 0)
            with tempfile.NamedTemporaryFile(mode='w') as config:
                config.write('{}'); config.flush()
                self.assertEqual(runner.main(['--allow-paid-review', '--config', config.name]), 1)
        self.assertNotIn('auth.json', output.getvalue())

    def test_unsupported_capabilities_and_forged_verdict(self):
        good = self.request()
        deploy.request_valid(good, 'metal')
        for mutation in [dict(approved=True), dict(closure='/nix/store/evil'),
                         dict(argv=['sh']), dict(action='boot'), dict(action='update'), dict(action='sh'),
                         dict(target='vm'), dict(reason=''), dict(reason='line\nbreak'), dict(reason='x'*2001), dict(commit='HEAD')]:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                deploy.request_valid(dict(good, **mutation), 'metal')

    def test_source_names_modes_bounds(self):
        for name in ['/etc/passwd', '../escape', 'a/../escape', '.git/config', 'a//b', 'x\ncommand', '.', 'a/./b']:
            request = self.request()
            request['files'][name] = 'text'
            request['modes'][name] = '100644'
            with self.subTest(name=name), self.assertRaises(ValueError):
                deploy.request_valid(request, 'metal')
        for content, mode in [('x', '120000'), ('x' * deploy.SOURCE_LIMIT, '100644'), (['binary'], '100644')]:
            request = self.request()
            request['files']['flake.nix'] = content
            request['modes']['flake.nix'] = mode
            with self.assertRaises(ValueError):
                deploy.request_valid(request, 'metal')

    def test_reload_finishes_and_replies_to_active_request_before_exit(self):
        handlers = {}
        connection = mock.Mock()
        connection.getsockopt.return_value = deploy.struct.pack('3i', 22, 1000, 1000)
        connection.recv.return_value = b'{}\n'
        listener = mock.Mock()
        listener.accept.return_value = (connection, None)
        def process(*args):
            handlers[deploy.signal.SIGUSR1](deploy.signal.SIGUSR1, None)
            connection.sendall.assert_not_called()
            return dict(ok=True, action='update')
        with mock.patch.object(deploy.os, 'getuid', return_value=0), \
             mock.patch.object(deploy.socket, 'socket', return_value=listener), \
             mock.patch.object(deploy.signal, 'signal', side_effect=lambda sig, handler: handlers.update({sig: handler})), \
             mock.patch.object(deploy, 'process', side_effect=process), contextlib.redirect_stdout(io.StringIO()):
            deploy.serve({'clientUid': 1000})
        connection.sendall.assert_called_once()
        self.assertTrue(json.loads(connection.sendall.call_args.args[0])['ok'])
        connection.close.assert_called_once()
        listener.accept.assert_called_once()

    def test_controller_wire_failure_is_typed_before_source_processing(self):
        handlers = {}
        connection = mock.Mock()
        connection.getsockopt.return_value = deploy.struct.pack('3i', 22, 1000, 1000)
        connection.recv.return_value = b'1234'
        listener = mock.Mock()
        listener.accept.return_value = (connection, None)
        def replied(_body):
            handlers[deploy.signal.SIGUSR1](deploy.signal.SIGUSR1, None)
        connection.sendall.side_effect = replied
        with mock.patch.object(deploy, 'LIMIT', 3), \
             mock.patch.object(deploy.os, 'getuid', return_value=0), \
             mock.patch.object(deploy.socket, 'socket', return_value=listener), \
             mock.patch.object(deploy.signal, 'signal', side_effect=lambda sig, handler: handlers.update({sig: handler})), \
             mock.patch.object(deploy, 'process') as process, contextlib.redirect_stdout(io.StringIO()):
            deploy.serve({'clientUid': 1000})
        response = json.loads(connection.sendall.call_args.args[0])
        self.assertEqual((response['stage'], response['code']), ('source-transport', 'wire-capacity-exceeded'))
        process.assert_not_called()

    def test_pending_rejection_response_displays_identity_without_journaling_private_text(self):
        handlers={};connection=mock.Mock();listener=mock.Mock();listener.accept.return_value=(connection,None)
        connection.getsockopt.return_value=deploy.struct.pack('3i',22,1000,1000)
        connection.recv.return_value=b'{}\n'
        denial=deploy.DeploymentDenied('PRIVATE summary')
        denial.pending_nonce='a'*64
        denial.pending_metadata=deploy.pending_metadata(dict(source='/nix/store/'+'b'*32+'-source',action='boot',target='metal'))
        def process(*args):
            handlers[deploy.signal.SIGUSR1](deploy.signal.SIGUSR1,None)
            raise denial
        with mock.patch.object(deploy.os,'getuid',return_value=0),mock.patch.object(deploy.socket,'socket',return_value=listener), \
             mock.patch.object(deploy.signal,'signal',side_effect=lambda sig,handler:handlers.update({sig:handler})), \
             mock.patch.object(deploy,'process',side_effect=process),contextlib.redirect_stdout(io.StringIO()) as journal:
            deploy.serve({'clientUid':1000})
        result=json.loads(connection.sendall.call_args.args[0])
        self.assertEqual(result['pendingSourceFingerprint'],'b'*32)
        self.assertEqual(result['pendingTarget'],'metal');self.assertEqual(result['pendingAction'],'boot')
        self.assertEqual(result['pendingNonce'],'a'*64)
        self.assertNotIn('PRIVATE',journal.getvalue())
        self.assertNotIn('summary',journal.getvalue())

    def test_idle_reload_exits_without_starting_another_request(self):
        handlers = {}
        listener = mock.Mock()
        def accept():
            handlers[deploy.signal.SIGUSR1](deploy.signal.SIGUSR1, None)
            raise deploy.socket.timeout()
        listener.accept.side_effect = accept
        with mock.patch.object(deploy.os, 'getuid', return_value=0), \
             mock.patch.object(deploy.socket, 'socket', return_value=listener), \
             mock.patch.object(deploy.signal, 'signal', side_effect=lambda sig, handler: handlers.update({sig: handler})), \
             mock.patch.object(deploy, 'process') as process:
            deploy.serve({'clientUid': 1000})
        process.assert_not_called()
        listener.accept.assert_called_once()

    def test_larger_complete_source_preserves_wire_bound(self):
        request = self.request()
        request['files']['flake.nix'] = 'x' * (512 * 1024 + 1)
        deploy.request_valid(request, 'metal')
        self.assertEqual(deploy.SOURCE_LIMIT, 4 * 1024 * 1024)
        self.assertEqual(deploy.LIMIT, 32 * 1024 * 1024)

    def test_mutable_source_and_fake_closure_rejected(self):
        for path in ['/tmp/source', '/nix/store/short-source', '/nix/store/' + 'a' * 32 + '-source/../source']:
            with self.assertRaises(ValueError):
                deploy.store_path(path, 'source')

    def test_prefix_collision_rejected_before_materialization(self):
        request = self.request()
        request['files'].update({'directory': 'file', 'directory/child': 'child'})
        request['modes'].update({'directory': '100644', 'directory/child': '100644'})
        with mock.patch.object(deploy.tempfile, 'TemporaryDirectory') as temporary:
            with self.assertRaises(deploy.DeploymentFailure):
                deploy.process({'target': 'metal'}, request, 1000, 22)
            temporary.assert_not_called()

    def test_controller_never_activates_failed_or_forged_review(self):
        for mode in ['rejected', 'forged', 'model-failed', 'malformed', 'closure-mismatch', 'compacted', 'oversized', 'extra-envelope']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                baseline = root / 'baseline'
                baseline.mkdir()
                (baseline / 'flake.nix').write_text('{}')
                (baseline / 'flake.lock').write_text('{}')
                profile = root / 'profile'
                profile_marker = profile / 'etc/phoenix-agent'
                profile_marker.mkdir(parents=True)
                (profile_marker / 'activated-source').symlink_to(baseline)
                original_resolve = Path.resolve
                def resolve(path, *args, **kwargs):
                    if path == Path('/nix/var/nix/profiles/system'):
                        return profile
                    return original_resolve(path, *args, **kwargs)
                frozen, closure = root / 'frozen', root / 'closure'
                marker = closure / 'etc/phoenix-agent'
                marker.mkdir(parents=True)
                (marker / 'activated-source').symlink_to(baseline if mode == 'closure-mismatch' else frozen)
                review = deploy.load_review({'reviewScript': str(Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/deploy-review.py')})
                review.run = mock.Mock(return_value=b'')
                config = dict(target='metal', work=directory, builderUser='builder', reviewerUser='reviewer',
                              reviewHome='/protected/auth', nix='nix', nixStore='nix-store', baseline=str(baseline),
                              python='python', controller='controller', configPath='config', systemdRun='systemd-run',
                              upstreamReviewScript=str(Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/upstream-review.py'))
                request = self.request()
                def user_command(config, user, argv, run, **kwargs):
                    if argv[:3] == ['nix', 'store', 'add-path']:
                        shutil.copytree(argv[3], frozen)
                        return str(frozen).encode()
                    if argv[:2] == ['nix', 'build']:
                        return str(closure).encode()
                    if mode in {'compacted', 'oversized'}:
                        code = 'context-compacted' if mode == 'compacted' else 'review-context-oversized'
                        return json.dumps(dict(status='error', code=code)).encode()
                    if mode == 'model-failed':
                        raise ValueError('authentication or model failed')
                    if mode == 'malformed':
                        return b'not json'
                    binding = json.loads(kwargs['data'])['binding']
                    verdict = dict(binding, approved=(mode != 'rejected'), summary='fixture')
                    if mode == 'forged':
                        verdict['nonce'] = 'wrong'
                    envelope = dict(status='verdict', verdict=verdict)
                    if mode == 'extra-envelope': envelope['upstreamVerdicts'] = []
                    return json.dumps(envelope).encode()
                account = mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
                with mock.patch.object(Path, 'resolve', resolve), contextlib.redirect_stdout(io.StringIO()), mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(deploy, 'as_user', side_effect=user_command), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy.pwd, 'getpwnam', return_value=account):
                    with self.assertRaises(deploy.DeploymentFailure) as failure:
                        deploy.process(config, request, os.getuid(), 22)
                self.assertIn(failure.exception.stage, {'verdict', 'review', 'closure-binding'})
                if mode in {'rejected'}:
                    self.assertIsInstance(failure.exception, deploy.DeploymentDenied)
                    self.assertEqual(failure.exception.summary, 'fixture')
                    self.assertEqual(failure.exception.code, 'model-denied')
                elif mode in {'forged'}:
                    self.assertEqual(failure.exception.code, 'binding-mismatch')
                self.assertFalse(any(call.args[0][0] == 'systemd-run' for call in review.run.call_args_list))

    def test_worker_reports_denial_separately_from_native_or_schema_failure(self):
        review = deploy.load_review({'reviewScript': str(Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/deploy-review.py')})
        verdict = dict(source='/nix/store/frozen', approved=False, summary='Unsafe recovery changes')
        for error, expected in [
            (review.ReviewDenied(verdict), {'status': 'verdict', 'verdict': verdict}),
            (review.ReviewVerdictError('binding-mismatch'), {'status': 'error', 'code': 'binding-mismatch'}),
            (review.ReviewVerdictError('schema-invalid'), {'status': 'error', 'code': 'schema-invalid'}),
            (review.ReviewVerdictError('context-compacted'), {'status': 'error', 'code': 'context-compacted'}),
            (review.ReviewVerdictError('review-context-oversized'), {'status': 'error', 'code': 'review-context-oversized'}),
            (ValueError('API stderr contains SECRET credential'), {'status': 'error', 'code': 'reviewer-invocation-failed'}),
        ]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                output, stderr = io.StringIO(), io.StringIO()
                payload = dict(binding={'source': '/nix/store/frozen'}, files={}, diff='')
                with mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(review, 'review', side_effect=error), mock.patch('sys.stdin', io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(output), contextlib.redirect_stderr(stderr):
                    deploy.worker({}, directory)
                self.assertEqual(json.loads(output.getvalue()), expected)
                self.assertNotIn('SECRET', output.getvalue() + stderr.getvalue())

    def test_model_denial_summary_is_bounded_and_not_in_exception_text(self):
        denial = deploy.DeploymentDenied('private task detail ' * 1000)
        self.assertEqual(len(denial.summary), 1000)
        self.assertNotIn('private task detail', str(denial))
        self.assertEqual(denial.code, 'model-denied')

    def test_bootstrap_rejects_auth_links_and_atomically_replaces_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            login, state = root / 'login', root / 'state'
            login.mkdir(mode=0o700); state.mkdir(mode=0o700)
            original = root / 'original'
            original.write_text('{"credential": "never-print"}')
            auth = login / 'auth.json'
            config = dict(migrationMarker=str(root / 'migrated'), loginHome=str(login), reviewHome=str(state), clientUid=os.getuid() + 1, operatorUid=os.getuid(), reviewerUser='reviewer')
            account = mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(deploy.os, 'getuid', return_value=0), mock.patch.object(deploy.pwd, 'getpwnam', return_value=account):
                auth.symlink_to(original)
                with self.assertRaises(OSError):
                    deploy.bootstrap(config)
                auth.unlink()
                os.link(original, auth)
                with self.assertRaisesRegex(ValueError, 'authentication'):
                    deploy.bootstrap(config)
                auth.unlink(); auth.write_text('{"new": "protected"}')
                destination = state / 'auth.json'
                destination.symlink_to(original)
                deploy.bootstrap(config)
                self.assertFalse(destination.is_symlink())
                self.assertEqual(json.loads(destination.read_text()), {'new': 'protected'})
                self.assertEqual(json.loads(original.read_text()), {'credential': 'never-print'})
                self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
                self.assertFalse(auth.exists())
                self.assertTrue(Path(config['migrationMarker']).is_file())
                deploy.bootstrap(config)

    def test_retained_auth_owned_by_agent_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'auth.json').write_text('{}')
            config = {'operatorUid': os.getuid() + 1, 'clientUid': os.getuid(),
                      'migrationMarker': str(home / 'migrated')}
            fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaisesRegex(ValueError, 'retained reviewer authentication'):
                    deploy.bootstrap_transfer(config, fd)
            finally:
                os.close(fd)
            self.assertTrue((home / 'auth.json').is_file())

    def test_operator_identity_is_separate_and_validated(self):
        self.assertEqual(deploy.operator_uid({'operatorUid': 1000, 'clientUid': 2000}), 1000)
        self.assertEqual(deploy.operator_uid({'clientUid': 1000}), 1000)
        for uid in (None, True, -1, '1000'):
            with self.assertRaises(ValueError):
                deploy.operator_uid({'operatorUid': uid, 'clientUid': 1000})
        with mock.patch.object(deploy.os, 'geteuid', return_value=0):
            with self.assertRaisesRegex(ValueError, 'authenticated root'):
                deploy.override({'operatorUid': 1000, 'clientUid': 2000}, 'a' * 64, 2000, 42)
        config = {'target': 'metal', 'modelReviewEnabled': False, 'operatorUid': 1000, 'clientUid': 2000}
        request = {'action': 'test', 'target': 'metal', 'worktree': '/fixture', 'reason': 'identity boundary'}
        with mock.patch.object(deploy.os, 'geteuid', return_value=0), mock.patch.object(deploy, 'request_valid'):
            with self.assertRaises(deploy.DeploymentFailure) as rejected:
                deploy.process(config, request, 2000, 42, operator=True)
            self.assertEqual(rejected.exception.code, 'operator-authentication-required')
            with mock.patch.object(deploy, 'process_inner', return_value={'ok': True}) as inner:
                self.assertEqual(deploy.process(config, request, 1000, 42, operator=True), {'ok': True})
                inner.assert_called_once()

    def test_activation_executable_cannot_follow_mutable_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            closure = Path(directory) / 'closure'
            (closure / 'bin').mkdir(parents=True)
            external = Path(directory) / 'outside'
            external.write_text('mutable script')
            external.chmod(0o755)
            (closure / 'bin/switch-to-configuration').symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                deploy.activation_executable(closure)

    def test_test_never_updates_profile(self):
        run = mock.Mock()
        config = dict(nixEnv='nix-env', activationEnvironment={'HOME': '/root'})
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            deploy.activate(config, '/nix/store/system', 'test', run)
        self.assertEqual(run.call_args.args[0], ['/nix/store/system/bin/switch-to-configuration', 'test'])
        self.assertEqual(run.call_count, 1)

    def test_boot_requests_require_observed_base_and_profile(self):
        request = dict(self.request(), action='boot')
        with self.assertRaises(ValueError):
            deploy.request_valid(request, 'metal')
        request.update(expectedBase='/trusted/source', expectedProfile='/trusted/profile')
        with mock.patch.object(deploy, 'store_path') as validation:
            deploy.request_valid(request, 'metal')
        self.assertEqual(validation.call_count, 2)

    def routine_sources(self):
        lock = dict(version=7, root='root', nodes={
            'root': {'inputs': {
                'nixpkgs': 'stable', 'nixpkgs-unstable': 'unstable',
                'codex-desktop-linux': 'desktop', 'codex-desktop-sandbox': 'sandbox'}},
            'stable': {'original': {'type': 'github', 'owner': 'NixOS', 'repo': 'nixpkgs', 'ref': 'nixos-26.05'},
                       'locked': {'type': 'github', 'owner': 'NixOS', 'repo': 'nixpkgs', 'rev': 'a' * 40,
                                  'narHash': 'sha256-' + 'A' * 43 + '=', 'lastModified': 1}},
            'unstable': {'original': {'type': 'github', 'owner': 'NixOS', 'repo': 'nixpkgs', 'ref': 'nixos-unstable'},
                         'locked': {'type': 'github', 'owner': 'NixOS', 'repo': 'nixpkgs', 'rev': 'b' * 40,
                                    'narHash': 'sha256-' + 'B' * 43 + '=', 'lastModified': 1}},
            'desktop': {'original': {'type': 'github', 'owner': 'ilysenko', 'repo': 'codex-desktop-linux'},
                        'locked': {'type': 'github', 'owner': 'ilysenko', 'repo': 'codex-desktop-linux', 'rev': 'c' * 40,
                                   'narHash': 'sha256-' + 'C' * 43 + '=', 'lastModified': 1}},
            'sandbox': {'original': {'type': 'github', 'owner': 'ilysenko', 'repo': 'codex-desktop-linux'},
                        'locked': {'type': 'github', 'owner': 'ilysenko', 'repo': 'codex-desktop-linux', 'rev': 'c' * 40,
                                   'narHash': 'sha256-' + 'C' * 43 + '=', 'lastModified': 1}},
        })
        policy = {'version': 1, '_comments': {},
                  'packageSources': {'firefox': 'nixpkgs-unstable',
                                     'codex-desktop': {'native': 'codex-desktop-linux', 'sandbox': 'codex-desktop-sandbox'},
                                     'codex-cli': 'nixpkgs-unstable'},
                  'holds': {}, 'patches': {}}
        source = {'flake.nix': 'root declarations', 'flake.lock': json.dumps(lock),
                  'config/updates.json': json.dumps(policy)}
        modes = {name: '100644' for name in source}
        candidate_lock = json.loads(source['flake.lock'])
        candidate_lock['nodes']['stable']['locked'].update(rev='d' * 40,
            narHash='sha256-' + 'D' * 43 + '=', lastModified=2)
        candidate = dict(source, **{'flake.lock': json.dumps(candidate_lock)})
        return source, modes, candidate, dict(modes)

    def test_routine_candidate_freezes_policy_declarations_and_publishers(self):
        before, before_modes, after, after_modes = self.routine_sources()
        def compare(left, right): return (left > right) - (left < right)
        def unexpected(*_args): raise AssertionError('unexpected exception version lookup')
        verified = []
        routine.validate_source(before, before_modes, after, after_modes, 'x86_64-linux',
                                compare, unexpected, unexpected,
                                lambda alias, _node: verified.append(alias))
        self.assertEqual(verified, ['nixpkgs'])
        for changed in ('declaration', 'policy', 'publisher', 'unlisted-file', 'new-input'):
            candidate = dict(after)
            if changed == 'declaration':
                candidate['flake.nix'] = 'different root input declaration'
            elif changed == 'policy':
                value = json.loads(candidate['config/updates.json'])
                value['packageSources']['firefox'] = 'nixpkgs'
                candidate['config/updates.json'] = json.dumps(value)
            elif changed == 'publisher':
                value = json.loads(candidate['flake.lock'])
                value['nodes']['stable']['locked']['owner'] = 'attacker'
                candidate['flake.lock'] = json.dumps(value)
            elif changed == 'unlisted-file':
                candidate['unrelated.nix'] = 'unreviewed source'
            else:
                value = json.loads(candidate['flake.lock'])
                value['nodes']['root']['inputs']['surprise'] = 'stable'
                candidate['flake.lock'] = json.dumps(value)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                routine.validate_source(before, before_modes, candidate, dict(after_modes),
                                        'x86_64-linux', compare, unexpected, unexpected)
        candidate_lock = json.loads(after['flake.lock'])
        candidate_lock['nodes']['desktop']['locked'].update(rev='d' * 40,
            narHash='sha256-' + 'D' * 43 + '=', lastModified=2)
        candidate = dict(after, **{'flake.lock': json.dumps(candidate_lock)})
        with self.assertRaisesRegex(ValueError, 'update together'):
            routine.validate_source(before, before_modes, candidate, after_modes, 'x86_64-linux',
                                    compare, unexpected, unexpected)
        with self.assertRaisesRegex(ValueError, 'file modes'):
            routine.validate_source(before, before_modes, after, dict(after_modes, **{'flake.lock': '100755'}),
                                    'x86_64-linux', compare, unexpected, unexpected)

    def test_routine_retains_unchanged_other_fetcher_inputs(self):
        before, _, after, _ = self.routine_sources()
        for files in (before, after):
            lock = json.loads(files['flake.lock'])
            lock['nodes']['retained-git'] = {
                'original': {'type': 'git', 'url': 'https://example.invalid/tool'},
                'locked': {'type': 'git', 'url': 'https://example.invalid/tool',
                           'rev': 'a' * 40, 'narHash': 'sha256-retained', 'ref': 'main'}}
            files['flake.lock'] = json.dumps(lock)
        routine.validate_lock(before, after)
        lock = json.loads(after['flake.lock'])
        lock['nodes']['retained-git']['locked']['rev'] = 'b' * 40
        after['flake.lock'] = json.dumps(lock)
        with self.assertRaises(ValueError):
            routine.validate_lock(before, after)

    def test_routine_candidate_removes_only_satisfied_effective_holds(self):
        before, before_modes, after, after_modes = self.routine_sources()
        policy = json.loads(before['config/updates.json'])
        policy['holds']['codex-cli'] = {'pin': 'e' * 40, 'reason': 'compatibility', 'resumeAtVersion': '0.160.0'}
        before['config/updates.json'] = json.dumps(policy)
        after_policy = dict(policy)
        after_policy['holds'] = {}
        after['config/updates.json'] = json.dumps(after_policy)
        queries = []
        def evaluate(alias, revision, attribute, system):
            queries.append((alias, revision, attribute, system))
            return '0.160.1'
        routine.validate_source(before, before_modes, after, after_modes, 'x86_64-linux',
                                lambda left, right: (tuple(map(int, left.split('.'))) > tuple(map(int, right.split('.')))) -
                                                     (tuple(map(int, left.split('.'))) < tuple(map(int, right.split('.')))),
                                evaluate, lambda _lock: '1.2.3')
        self.assertEqual(queries, [('nixpkgs-unstable', 'b' * 40, 'codex', 'x86_64-linux')])
        queries.clear()
        with self.assertRaisesRegex(ValueError, 'threshold'):
            routine.validate_source(before, before_modes, after, after_modes, 'x86_64-linux',
                                    lambda _left, _right: -1,
                                    lambda *args: queries.append(args) or '0.159.9',
                                    lambda _lock: '1.2.3')
        self.assertEqual(queries[0][0], 'nixpkgs-unstable')

    def test_routine_action_keeps_declared_patch_files_immutable(self):
        before, before_modes, after, after_modes = self.routine_sources()
        policy = json.loads(before['config/updates.json'])
        policy['patches']['kando'] = {'reason': 'temporary fix',
                                      'patchFiles': ['config/update-patches/kando.patch'],
                                      'removeAtVersion': '3.0.0'}
        before['config/updates.json'] = json.dumps(policy)
        after['config/updates.json'] = json.dumps(policy)
        before['config/update-patches/kando.patch'] = 'fixed source patch'
        after['config/update-patches/kando.patch'] = 'fixed source patch'
        before_modes['config/update-patches/kando.patch'] = '100644'
        after_modes['config/update-patches/kando.patch'] = '100644'
        compare = lambda left, right: (tuple(map(int, left.split('.'))) > tuple(map(int, right.split('.')))) - \
                                     (tuple(map(int, left.split('.'))) < tuple(map(int, right.split('.'))))
        routine.validate_source(before, before_modes, after, after_modes, 'x86_64-linux',
                                compare, lambda *_args: '2.9.0', lambda _lock: '1.0.0')
        after['config/update-patches/kando.patch'] = 'caller changed patch bytes'
        with self.assertRaisesRegex(ValueError, 'patch files'):
            routine.validate_source(before, before_modes, after, after_modes, 'x86_64-linux',
                                    compare, lambda *_args: '2.9.0', lambda _lock: '1.0.0')

    def test_routine_community_gate_binds_required_checks_and_payload_hashes(self):
        revision = 'a' * 40
        checks = [dict(name=name, head_sha=revision, status='completed', conclusion='success',
                       app={'slug': 'github-actions'}) for name in sorted(routine.COMMUNITY_CHECKS)]
        requests = []
        def open_url(url):
            requests.append(url)
            return {'total_count': len(checks), 'check_runs': checks}
        routine.validate_community_checks(revision, open_url)
        self.assertEqual(len(requests), 1)
        checks[0]['head_sha'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'check failed'):
            routine.validate_community_checks(revision, open_url)
        with tempfile.TemporaryDirectory() as directory:
            import base64
            payload = {'version': '1.2.3'}
            for arch in ('amd64', 'arm64'):
                digest = ('1' if arch == 'amd64' else '2') * 64
                payload[arch] = {'repositoryPath': 'pool/main/c/chatgpt/chatgpt_1.2.3_%s.deb' % arch,
                                 'sha256': digest,
                                 'sri': 'sha256-' + base64.b64encode(bytes.fromhex(digest)).decode()}
            source = Path(directory) / 'nix'
            source.mkdir()
            (source / 'upstream-linux-packages.json').write_text(json.dumps(payload))
            self.assertEqual(routine.validate_community_payload(directory), '1.2.3')

    def non_model_deployment(self, action='update', operator=False, updater_socket=False, malicious=False, progress=False, build_failure=False, stalled_reader=False):
        before, _modes, candidate, modes = self.routine_sources()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / 'baseline'
            baseline.mkdir()
            profile_source = root / 'profile-source'
            profile_source.mkdir()
            profile = root / 'profile'
            marker = profile / 'etc/phoenix-agent'
            marker.mkdir(parents=True)
            for name, content in before.items():
                for target in (baseline, profile_source):
                    path = target / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
            (marker / 'activated-source').symlink_to(profile_source)
            frozen, closure, old_runtime = root / 'frozen', root / 'closure', root / 'old-runtime'
            (closure / 'etc/phoenix-agent').mkdir(parents=True)
            (closure / 'etc/phoenix-agent/activated-source').symlink_to(frozen)
            original_resolve = Path.resolve
            def resolve(path, *args, **kwargs):
                if path == Path('/etc/phoenix-agent/activated-source'):
                    return baseline
                if path == Path('/nix/var/nix/profiles/system'):
                    return profile
                if path == Path('/run/current-system'):
                    return old_runtime
                return original_resolve(path, *args, **kwargs)
            native_review = deploy.load_review({'reviewScript': str(Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/deploy-review.py')})
            class Review:
                run = mock.Mock(return_value=b'')
                run_build = staticmethod(native_review.run_build)
                BuildError = native_review.BuildError
                @staticmethod
                def baseline_files(path):
                    return {item.relative_to(path).as_posix(): item.read_text()
                            for item in path.rglob('*') if item.is_file()}
                @staticmethod
                def source_modes(path, files):
                    return {name: ('100755' if (path / name).stat().st_mode & 0o111 else '100644')
                            for name in files}
            account = mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
            as_user_calls = []
            def as_user(_config, user, argv, _run, **kwargs):
                as_user_calls.append((user, argv))
                if argv[:3] == ['nix', 'store', 'add-path']:
                    shutil.copytree(argv[3], frozen)
                    return str(frozen).encode()
                if argv[:2] == ['nix', 'build']:
                    if progress:
                        script = ('import sys; print("package failure",file=sys.stderr); sys.exit(7)' if build_failure else
                                  'import sys; print("building package",file=sys.stderr); print(' + repr(str(closure)) + ')')
                        return _run([sys.executable, '-c', script], **kwargs)
                    return str(closure).encode()
                if argv[:3] == ['nix', 'flake', 'metadata']:
                    locked = json.loads(candidate['flake.lock'])['nodes']['stable']['locked']
                    return json.dumps(dict(locked=locked, path='/nix/store/' + 'f' * 32 + '-source')).encode()
                raise AssertionError('unexpected unprivileged command')
            config = dict(target='metal', work=directory, builderUser='builder', reviewerUser='reviewer',
                          reviewHome='/protected/auth', nix='nix', nixStore='nix-store', baseline='/etc/phoenix-agent/activated-source',
                          routineUpdateScript=str(Path(__file__).resolve().parents[5] / 'modules/development/ai/agent/routine-update.py'),
                          system='x86_64-linux', systemdRun='systemd-run', configPath='config', controller='controller',
                          python='python', activationEnvironment={}, modelReviewEnabled=False, operatorUid=os.getuid(), clientUid=os.getuid())
            request = dict(files=candidate, modes=modes, commit='a' * 40, action='update', target='metal',
                           reason='Stage deterministic stable package updates',
                           expectedBase=str(baseline), expectedProfile=str(profile))
            request['action'] = action
            if progress:
                request['progress'] = True
            if action not in {'boot', 'update'}:
                del request['expectedBase'], request['expectedProfile']
            if updater_socket:
                config.update(clientUid=2000, operatorUid=1000,
                              authorizationPolicy=dict(deploy.authorization.default_policy(False, 2000, 1000), updaterUid=1000))
            if malicious:
                # A valid source manifest containing an unauthorized source change.
                request['files']['unapproved.nix'] = 'malicious = true;'
                request['modes']['unapproved.nix'] = '100644'
            def socket_workflow():
                handlers = {}
                connection = mock.Mock()
                connection.getsockopt.return_value = deploy.struct.pack('3i', 42, 1000, 1000)
                connection.recv.return_value = json.dumps(request).encode() + b'\n'
                if stalled_reader:
                    def send(data):
                        if json.loads(data).get('event') == 'progress':
                            raise deploy.socket.timeout()
                    connection.sendall.side_effect = send
                listener = mock.Mock()
                calls = iter([0, 1])
                def accept():
                    if next(calls) == 0: return connection, None
                    handlers[deploy.signal.SIGUSR1](None, None)
                    raise deploy.socket.timeout()
                listener.accept.side_effect = accept
                with mock.patch.object(deploy.os, 'getuid', return_value=0), mock.patch.object(deploy.socket, 'socket', return_value=listener), mock.patch.object(deploy.signal, 'signal', side_effect=lambda sig, fn: handlers.update({sig: fn})):
                    deploy.serve(config)
                messages = [json.loads(call.args[0]) for call in connection.sendall.call_args_list]
                if stalled_reader:
                    self.assertEqual(sum(message.get('event') == 'progress' for message in messages), 1)
                    connection.shutdown.assert_called_once_with(deploy.socket.SHUT_WR)
                elif progress:
                    self.assertTrue(any(message.get('event') == 'progress' for message in messages[:-1]))
                    self.assertIn('package failure' if build_failure else 'building package', ''.join(message.get('text', '') for message in messages))
                else:
                    self.assertEqual(len(messages), 1)
                return json.loads(connection.sendall.call_args.args[0])
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(Path, 'resolve', resolve), \
                 mock.patch.object(deploy, 'load_review', return_value=Review), \
                 mock.patch.object(deploy, 'as_user', side_effect=as_user), \
                 mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'store_file', side_effect=lambda path: path), \
                 mock.patch.object(deploy.pwd, 'getpwnam', return_value=account), \
                 mock.patch.object(deploy, 'request_valid', wraps=deploy.request_valid), \
                 mock.patch.object(deploy.os, 'geteuid', return_value=0 if operator else os.getuid()):
                result = socket_workflow() if updater_socket else deploy.process(config, request, os.getuid(), 42, operator=operator)
            if build_failure:
                self.assertFalse(result['ok'])
                self.assertEqual((result['stage'], result['code']), ('build', 'build-failed'))
                self.assertIn('package failure', result['diagnostics'])
                self.assertFalse(any(call.args[0][0] == 'systemd-run' for call in Review.run.call_args_list))
                return
            if updater_socket and action != 'update':
                self.assertFalse(result['ok'])
                self.assertEqual(result['stage'], 'protocol')
                self.assertEqual(as_user_calls, [])
                Review.run.assert_not_called()
                return
            if malicious:
                self.assertFalse(result['ok'])
                self.assertEqual(result['stage'], 'routine-policy')
                self.assertFalse(any(call.args[0][0] == 'systemd-run' for call in Review.run.call_args_list))
                return
            self.assertTrue(result['ok'])
            self.assertEqual(result['action'], action)
            self.assertEqual([user for user, _argv in as_user_calls], ['builder'] * (3 if action == 'update' else 2))
            self.assertEqual(Review.run.call_count, 4)  # realize source/closure/runtime, then transient activation
            activation = next(call.args[0] for call in Review.run.call_args_list
                              if call.args[0][0] == 'systemd-run')
            self.assertEqual(activation[activation.index('activate') + 2], action)
            self.assertFalse(any(user == 'reviewer' for user, _argv in as_user_calls))
            self.assertFalse(any("pkexec" in str(call.args[0]) or "polkit" in str(call.args[0])
                                 for call in Review.run.call_args_list))

    def test_distinct_updater_socket_uses_production_validator_and_boot_only(self):
        self.non_model_deployment(updater_socket=True)
        self.non_model_deployment(updater_socket=True, malicious=True)
        for action in ('test', 'switch', 'boot'):
            self.non_model_deployment(action=action, updater_socket=True)

    def test_routine_update_progress_socket_retains_build_failure_and_success(self):
        self.non_model_deployment(updater_socket=True, progress=True)
        self.non_model_deployment(updater_socket=True, progress=True, build_failure=True)
        self.non_model_deployment(updater_socket=True, progress=True, stalled_reader=True)

    def test_routine_update_reaches_boot_without_invoking_reviewer(self):
        self.non_model_deployment()

    def test_disabled_reviewer_requires_authenticated_operator_for_manual_deploy(self):
        with mock.patch.object(deploy, 'process_inner') as inner:
            with self.assertRaisesRegex(deploy.DeploymentFailure, 'operator-authentication-required'):
                deploy.process({'target':'metal', 'modelReviewEnabled':False}, self.request(), 1000, 42)
            inner.assert_not_called()
        self.non_model_deployment(action='switch', operator=True)

    def test_default_github_branch_uses_canonical_flake_reference(self):
        self.assertEqual(deploy.frozen_github_reference('numtide', 'flake-utils'),
                         'github:numtide/flake-utils')
        self.assertEqual(deploy.frozen_github_reference('NixOS', 'nixpkgs', 'nixos-26.05', 'nixos'),
                         'github:NixOS/nixpkgs/nixos-26.05?dir=nixos')

    def test_boot_never_activates_or_rolls_back_the_running_desktop(self):
        config = dict(nixEnv='nix-env', activationEnvironment={})
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            run = mock.Mock()
            deploy.activate(config, '/new', 'boot', run)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args.args[0], ['/new/bin/switch-to-configuration', 'boot'])
            run = mock.Mock(side_effect=[None, ValueError('staging failed'), None, None])
            with self.assertRaisesRegex(ValueError, 'staging failed'):
                deploy.activate(config, '/new', 'boot', run)
            self.assertFalse(any('test' in call.args[0] or 'switch' in call.args[0] for call in run.call_args_list))
            self.assertEqual(run.call_args.args[0], ['/old/bin/switch-to-configuration', 'boot'])

    def test_update_stages_boot_and_rollback_without_runtime_activation(self):
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            run = mock.Mock()
            deploy.activate(dict(nixEnv='nix-env', activationEnvironment={}), '/new', 'update', run)
            self.assertEqual(run.call_args.args[0], ['/new/bin/switch-to-configuration', 'boot'])
            run = mock.Mock(side_effect=[None, ValueError('staging failed'), None, None])
            with self.assertRaisesRegex(ValueError, 'staging failed'):
                deploy.activate(dict(nixEnv='nix-env', activationEnvironment={}), '/new', 'update', run)
            self.assertEqual(run.call_args.args[0], ['/old/bin/switch-to-configuration', 'boot'])
            self.assertFalse(any('test' in call.args[0] or 'switch' in call.args[0] for call in run.call_args_list))

    def test_failed_test_restores_runtime_only(self):
        run = mock.Mock(side_effect=[ValueError('failed'), None])
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            with self.assertRaises(ValueError):
                deploy.activate(dict(activationEnvironment={}), '/new', 'test', run)
        self.assertEqual(run.call_args.args[0], ['/old/bin/switch-to-configuration', 'test'])
        self.assertEqual(run.call_count, 2)

    def test_failed_switch_restores_profile_and_runtime(self):
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            if argv == ['/new/bin/switch-to-configuration', 'switch']:
                raise ValueError('activation failure')
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            with self.assertRaisesRegex(ValueError, 'activation failure'):
                deploy.activate(dict(nixEnv='nix-env', activationEnvironment={}), '/new', 'switch', run)
        self.assertEqual(calls, [
            ['nix-env', '--profile', '/nix/var/nix/profiles/system', '--set', '/new'],
            ['/new/bin/switch-to-configuration', 'switch'],
            ['nix-env', '--profile', '/nix/var/nix/profiles/system', '--set', '/old'],
            ['/old/bin/switch-to-configuration', 'boot'],
            ['/old/bin/switch-to-configuration', 'test']])

    def test_profile_update_timeout_also_rolls_back(self):
        run = mock.Mock(side_effect=[ValueError('timed out after side effect'), None, None, None])
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            with self.assertRaises(ValueError):
                deploy.activate(dict(nixEnv='nix-env', activationEnvironment={}), '/new', 'switch', run)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(run.call_args.args[0], ['/old/bin/switch-to-configuration', 'test'])

    def test_boot_rollback_failure_still_attempts_runtime(self):
        run = mock.Mock(side_effect=[None, ValueError('activation'), None, ValueError('boot rollback'), None])
        with mock.patch.object(Path, 'resolve', return_value=Path('/old')):
            with self.assertRaises(deploy.DeploymentFailure) as failure:
                deploy.activate(dict(nixEnv='nix-env', activationEnvironment={}), '/new', 'switch', run)
        self.assertEqual(failure.exception.code, 'rollback-incomplete')
        self.assertEqual(run.call_args.args[0], ['/old/bin/switch-to-configuration', 'test'])

    def test_separate_identities_no_groups_and_no_new_privileges(self):
        account = mock.Mock(pw_uid=44, pw_gid=45)
        run = mock.Mock(return_value=b'output')
        with mock.patch.object(deploy.pwd, 'getpwnam', return_value=account):
            deploy.as_user({'setpriv': '/trusted/setpriv'}, 'reviewer', ['/trusted/codex'], run)
        self.assertEqual(run.call_args.args[0], ['/trusted/setpriv', '--reuid', '44', '--regid', '45',
                                               '--clear-groups', '--no-new-privs', '/trusted/codex'])


    def test_worker_makes_one_security_scope_without_upstream_batches(self):
        review=deploy.load_review({'reviewScript':str(Path(__file__).resolve().parents[5]/'modules/development/ai/agent/deploy-review.py')})
        binding={'source':'/immutable/source','nonce':'fresh'}
        payload=dict(binding=binding,files={},baseline={},diff='local diff',upstreamBatches=['untrusted omitted batch'])
        with tempfile.TemporaryDirectory() as directory:
            output=io.StringIO()
            def approve(config,binding,files,diff,temporary,baseline):return dict(binding,approved=True,summary='fixture')
            with mock.patch.object(deploy,'load_review',return_value=review),mock.patch.object(review,'review',side_effect=approve) as calls, \
                 mock.patch('sys.stdin',io.StringIO(json.dumps(payload))),contextlib.redirect_stdout(output):
                deploy.worker({},directory)
            result=json.loads(output.getvalue())
            self.assertEqual(calls.call_count,1)
            self.assertEqual(set(result), {'status','verdict'})
            self.assertEqual(calls.call_args.args[3],'local diff')

    def test_controller_cache_hit_skips_ai_and_denial_records_exact_pending_state(self):
        for cached in [False, True]:
            with self.subTest(cached=cached), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);baseline=root/'baseline';baseline.mkdir()
                for name in ('flake.nix','flake.lock'):(baseline/name).write_text('{}')
                profile=root/'profile';marker=profile/'etc/phoenix-agent';marker.mkdir(parents=True)
                (marker/'activated-source').symlink_to(baseline)
                frozen=root/'frozen';closure=root/'closure';marker=closure/'etc/phoenix-agent';marker.mkdir(parents=True)
                (marker/'activated-source').symlink_to(frozen)
                review=deploy.load_review({'reviewScript':str(Path(__file__).resolve().parents[5]/'modules/development/ai/agent/deploy-review.py')})
                review.run=mock.Mock(return_value=b'')
                security=mock.Mock();security.choose_checkpoint.return_value=(cached,str(baseline),{'flake.nix':'{}','flake.lock':'{}'})
                security.pending.return_value='a'*64
                config=dict(target='metal',work=directory,builderUser='builder',reviewerUser='reviewer',reviewHome='/protected',
                    nix='nix',nixStore='nix-store',baseline=str(baseline),python='python',controller='controller',configPath='config',
                    systemdRun='systemd-run',securityReviewState='/protected/state')
                commands=[]
                def user_command(config,user,argv,run,**kwargs):
                    commands.append((user,argv))
                    if argv[:3]==['nix','store','add-path']:
                        shutil.copytree(argv[3],frozen);return str(frozen).encode()
                    if argv[:2]==['nix','build']:return str(closure).encode()
                    payload=json.loads(kwargs['data'])
                    self.assertEqual(payload['baseline'],{'flake.nix':'{}','flake.lock':'{}'})
                    self.assertNotIn('upstreamBatches',payload)
                    return json.dumps(dict(status='verdict',verdict=dict(payload['binding'],approved=False,summary='security harm'))).encode()
                original=Path.resolve
                def resolve(path,*args,**kwargs):
                    if path==Path('/nix/var/nix/profiles/system'):return profile
                    return original(path,*args,**kwargs)
                account=mock.Mock(pw_uid=os.getuid(),pw_gid=os.getgid())
                with mock.patch.object(deploy,'load_review',return_value=review),mock.patch.object(deploy,'load_security',return_value=security), \
                     mock.patch.object(deploy,'as_user',side_effect=user_command),mock.patch.object(deploy,'store_path'), \
                     mock.patch.object(deploy,'activation_executable'),mock.patch.object(deploy.pwd,'getpwnam',return_value=account), \
                     mock.patch.object(Path,'resolve',resolve),mock.patch.object(deploy,'activate_bound',return_value={'ok':True}) as activation, \
                     contextlib.redirect_stdout(io.StringIO()):
                    if cached:
                        self.assertTrue(deploy.process(config,self.request(),1000,22)['ok'])
                        activation.assert_called_once();security.approve.assert_called_once();security.pending.assert_not_called()
                        self.assertEqual([user for user,_ in commands],['builder','builder'])
                    else:
                        with self.assertRaises(deploy.DeploymentDenied) as denied:deploy.process(config,self.request(),1000,22)
                        self.assertEqual(denied.exception.pending_nonce,'a'*64)
                        self.assertEqual(denied.exception.pending_metadata,dict(pendingSourceFingerprint='frozen',pendingAction='test',pendingTarget='metal'))
                        activation.assert_not_called();security.approve.assert_not_called()
                        bound=security.pending.call_args.args[1]
                        self.assertEqual(bound['source'],str(frozen));self.assertEqual(bound['closure'],str(closure))
                        self.assertEqual(bound['base'],str(baseline));self.assertEqual(bound['profile'],str(profile))
                        self.assertEqual(bound['action'],'test');self.assertEqual(bound['target'],'metal')
                        self.assertEqual(security.pending.call_args.args[2],1000)

    def test_integration_lock_is_private_and_distinct_between_fixture_owners(self):
        owners = []
        for _ in range(2):
            self.test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow()
            self.assertTrue(self.fixture_lock_paths)
            parents = {str(Path(path).parent) for path in self.fixture_lock_paths}
            self.assertEqual(len(parents), 1)
            self.assertNotIn('/tmp', parents)
            owners.append(parents)
        self.assertNotEqual(owners[0], owners[1])

    def test_immutable_source_integration_uses_explicit_fixture_policy(self):
        # Store-packaged authorization deliberately disables worktree-only fallback.
        with mock.patch.object(deploy.authorization, '__file__', '/nix/store/' + 'a' * 32 + '-fixture/request.py'):
            with self.assertRaisesRegex(ValueError, 'installed authorization policy missing'):
                deploy.authorization.policy({})
            self.test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow()

    def test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow(self):
        """Exercise production integration; OS/store/model/activation are explicit stubs."""
        self.live_stage = "fixture-setup"
        self.fixture_lock_paths = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owner = Path(__file__).resolve().parents[5] / 'modules/development/ai/agent'
            baseline = root / 'baseline'
            baseline.mkdir()
            initial = {'flake.nix': '{}\n', 'flake.lock': '{}\n', 'context.nix': 'needed context\n'}
            for name, text in initial.items():
                (baseline / name).write_text(text)
            profile = root / 'profile'
            (profile / 'etc/phoenix-agent').mkdir(parents=True)
            (profile / 'etc/phoenix-agent/activated-source').symlink_to(baseline)
            (profile / 'etc/phoenix-agent/active-provenance.json').write_text(json.dumps(dict(version=1, target='metal', source=str(baseline))))
            state = root / 'security'
            state.mkdir()
            auth = root / 'auth'
            auth.mkdir()
            (auth / 'auth.json').write_text('fixture-only')
            review = deploy.load_review({'reviewScript': str(owner / 'deploy-review.py')})
            security = self.security()
            requests = root / 'requests'
            requests.mkdir(mode=0o700)
            config = dict(target='metal', work=str(requests), builderUser='builder', reviewerUser='reviewer',
                reviewHome=str(auth), nix='nix', nixStore='nix-store', baseline=str(baseline),
                python='python', controller=str(owner / 'deployment.py'), configPath='fixture', systemdRun='systemd-run',
                reviewScript=str(owner / 'deploy-review.py'), securityReviewScript=str(owner / 'security-review.py'),
                securityReviewState=str(state), policy=str(owner / 'review-policy.md'), codex='codex', bwrap='bwrap',
                caBundle='/fixture/cert', model='gpt-6.1-sol', effort='medium', modelReviewEnabled=True, operatorUid=1000, clientUid=1000,
                authorizationPolicy=deploy.authorization.default_policy(True, 1000, 1000))
            frozen_sources, closures, prompts = {}, {}, []
            decision = 'context'
            live = getattr(self, 'live_review', None)
            real_run = review.run
            if live:
                config.update(live)
                config['reviewHome'] = '/var/lib/phoenix-deploy-review'
                decision = 'live'

            def command(argv, **kwargs):
                if argv[0] == 'nix-store':
                    Path(argv[argv.index('--add-root') + 1]).symlink_to(argv[-1])
                    return b''
                self.assertEqual(argv[0], config['bwrap'])
                prompt = kwargs['data'].decode()
                prompts.append(prompt)
                self.assertNotIn('upstreamBatches', prompt)
                self.assertNotIn('unrequested secret content', prompt)
                if live and decision == 'live':
                    if len(prompts) > 2:
                        raise RuntimeError('live invocation budget exhausted')
                    self.live_invocations = len(prompts)
                    return real_run(argv, **kwargs)
                payload = json.loads(prompt.split('Source data follows:\n', 1)[1].split('\nResolved context', 1)[0])
                if decision == 'error':
                    raise ValueError('SECRET credential stderr must not escape')
                verdict = dict(payload['binding'], approved=decision != 'deny', summary='fixture security decision')
                # Bubblewrap work mount is immediately before its /work destination.
                work = Path(argv[argv.index('/work') - 1])
                schema = json.loads((work / 'schema.json').read_text())
                if 'context' in schema['properties']:
                    verdict['context'] = []
                    if decision == 'context':
                        verdict.update(approved=None, context=[dict(source='baseline', path='context.nix', start=1, end=1)])
                else:
                    self.assertIn('needed context', prompt)
                (work / 'verdict.json').write_text(json.dumps(verdict))
                return b''

            def user_command(config, user, argv, run, **kwargs):
                if argv[:3] == ['nix', 'store', 'add-path']:
                    files = review.baseline_files(Path(argv[3]))
                    key = json.dumps(files, sort_keys=True)
                    if key not in frozen_sources:
                        frozen = root / ('frozen-' + str(len(frozen_sources)))
                        shutil.copytree(argv[3], frozen)
                        frozen_sources[key] = frozen
                    return str(frozen_sources[key]).encode()
                if argv[:2] == ['nix', 'eval']:
                    self.assertIn('--offline', argv)
                    self.assertIn('allow-import-from-derivation', argv)
                    return str(profile).encode()
                if argv[:2] == ['nix', 'build']:
                    frozen = Path(argv[-1].split('#')[0][5:])
                    if frozen not in closures:
                        closure = root / ('closure-' + str(len(closures)))
                        (closure / 'etc/phoenix-agent').mkdir(parents=True)
                        (closure / 'etc/phoenix-agent/activated-source').symlink_to(frozen)
                        closures[frozen] = closure
                    return str(closures[frozen]).encode()
                self.assertEqual(user, 'reviewer')
                output = io.StringIO()
                with mock.patch('sys.stdin', io.StringIO(kwargs['data'].decode())), contextlib.redirect_stdout(output):
                    deploy.worker(config, argv[-1])
                return output.getvalue().encode()

            original_open = Path.open
            def owned_open(path, *args, **kwargs):
                if path.name == 'deployment.lock':
                    self.assertEqual(path.parent, root, 'fixture deployment lock escaped owned tree')
                    self.fixture_lock_paths.append(str(path))
                return original_open(path, *args, **kwargs)

            original_resolve = Path.resolve

            def resolve(path, *args, **kwargs):
                if path == Path('/run/current-system'):
                    return profile
                if path == Path('/nix/var/nix/profiles/system'):
                    return profile
                return original_resolve(path, *args, **kwargs)

            request = dict(self.request(), files=dict(initial, **{'flake.nix': '{ changed = true; }\n' + '# unchanged approved context\n' * 12,
                'private.nix': 'unrequested secret content\n'}), branch='feature')
            # An unchanged private file belongs in both frozen states, never prompt data.
            (baseline / 'private.nix').write_text(request['files']['private.nix'])
            if live:
                request['files']['flake.nix'] = '# Isolated acceptance comment; no behavior change.\n{}\n'
            request['modes'] = {name: '100644' for name in request['files']}
            account = mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
            with mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(deploy, 'load_security', return_value=security), \
                 mock.patch.object(review, 'run', side_effect=command), mock.patch.object(deploy, 'as_user', side_effect=user_command), \
                 mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'store_file', side_effect=lambda path: path), \
                 mock.patch.object(deploy.pwd, 'getpwnam', return_value=account), mock.patch.object(Path, 'resolve', resolve), \
                 mock.patch.object(Path, 'open', owned_open), \
                 mock.patch.object(security, 'state_directory', return_value=state), \
                 mock.patch.object(security, 'read_record', side_effect=lambda path: json.loads(path.read_text())), \
                 mock.patch.object(deploy, 'activation_guard', return_value=contextlib.nullcontext(42)), \
                 mock.patch.object(deploy.os, 'geteuid', return_value=0), \
                 mock.patch.object(deploy, 'activate_bound', return_value={'ok': True}) as activation, contextlib.redirect_stdout(io.StringIO()) as journal:
                self.live_stage = 'seed-checkpoint'
                seeded = deploy.trust_active(config, 1000, 22)
                self.assertEqual(seeded['source'], str(baseline))
                self.assertEqual(seeded['closure'], str(profile))
                self.assertEqual(prompts, [], 'trust active never calls AI')
                # Trust seeds an exact independently approved runtime checkpoint.
                self.assertTrue(security.choose_checkpoint(config, 'metal', str(baseline), str(profile),
                    'unrelated-branch', str(baseline), review.baseline_files(baseline), review, deploy.store_path)[0])
                self.live_stage = 'bound-verdict'
                try:
                    self.assertTrue(deploy.process(config, request, 1000, 22)['ok'])
                except (deploy.DeploymentFailure, deploy.DeploymentDenied) as error:
                    if live:
                        self.live_failure = getattr(error, 'code', 'model-denied')
                    raise
                initial_calls = len(prompts)
                if live:
                    self.assertIn(initial_calls, (1, 2))
                else:
                    self.assertEqual(initial_calls, 2)
                if not live:
                    self.assertIn('-{}', prompts[0])
                self.assertIn('+# Isolated acceptance comment' if live else '+{ changed = true; }', prompts[0])
                self.live_stage = 'exact-reuse'
                request['branch'] = 'another-branch'
                self.assertTrue(deploy.process(config, request, 1000, 22)['ok'])
                self.assertEqual(len(prompts), initial_calls, 'exact source/closure approval reuses zero AI')
                if live:
                    # No second model decision: inject a deterministic adapter failure.
                    self.live_stage = 'injected-failure-fallback'
                    decision = 'error'
                    request['files']['flake.nix'] += '# Distinct failure-path binding.\n'
                    before = activation.call_count
                    with self.assertRaises(deploy.DeploymentFailure) as failed:
                        deploy.process(config, request, 1000, 22)
                    self.assertEqual(activation.call_count, before)
                    pending = security.load_pending(config, failed.exception.pending_nonce, 1000, deploy.store_path)
                    self.assertTrue(deploy.override(config, failed.exception.pending_nonce, 1000, 22)['ok'])
                    self.assertEqual(activation.call_args.args[1]['source'], pending['source'])
                    self.live_receipt = dict(status='passed', modelInvocations=initial_calls,
                                             exactReuse=True, injectedFailure=True, stubFallbackBound=True)
                    return
                decision = 'approve'
                request['files']['flake.nix'] = request['files']['flake.nix'].replace(
                    'changed = true;', 'changed = true; extra = true;')
                self.assertTrue(deploy.process(config, request, 1000, 22)['ok'])
                self.assertIn('-{ changed = true; }', prompts[-1], 'approved checkpoint supplies incremental diff')
                self.assertNotIn('-{}', prompts[-1])
                # A combination of separately approved changes remains a new source.
                request['files']['flake.nix'] = request['files']['flake.nix'].replace('extra = true;', 'extra = true; union = true;')
                request['branch'] = 'merged'
                before = len(prompts)
                self.assertTrue(deploy.process(config, request, 1000, 22)['ok'])
                self.assertEqual(len(prompts), before + 1, 'merged integration residual still needs review')
                decision = 'deny'
                request['files']['flake.nix'] = '{ denied = true; }\n'
                before = activation.call_count
                with self.assertRaises(deploy.DeploymentDenied) as denied:
                    deploy.process(config, request, 1000, 22)
                self.assertEqual(activation.call_count, before)
                nonce = denied.exception.pending_nonce
                pending = security.load_pending(config, nonce, 1000, deploy.store_path)
                # Later mutable caller changes cannot replace the protected override.
                request['files']['flake.nix'] = 'mutated after freeze'
                self.assertTrue(deploy.override(config, nonce, 1000, 22)['ok'])
                self.assertEqual(activation.call_args.args[1]['source'], pending['source'])
                self.assertEqual(activation.call_args.args[1]['closure'], pending['closure'])
                request['files']['flake.nix'] = '{ denied = true; }\n'
                before = len(prompts)
                self.assertTrue(deploy.process(config, request, 1000, 22)['ok'])
                self.assertEqual(len(prompts), before, 'human exact approval is reusable without AI')
                request['files']['flake.nix'] = 'mutated after freeze'
                decision = 'error'
                before = activation.call_count
                with self.assertRaises(deploy.DeploymentFailure) as failed:
                    deploy.process(config, request, 1000, 22)
                self.assertEqual(failed.exception.code, 'reviewer-invocation-failed')
                self.assertNotIn('SECRET', str(failed.exception))
                self.assertNotIn('SECRET', security.load_pending(config, failed.exception.pending_nonce, 1000, deploy.store_path)['summary'])
                self.assertTrue(failed.exception.pending_nonce)
                self.assertEqual(activation.call_count, before)
                before = len(prompts)
                config['modelReviewEnabled'] = False
                config['authorizationPolicy'] = deploy.authorization.default_policy(False, 1000, 1000)
                self.assertTrue(deploy.process(config, request, 1000, 22, operator=True)['ok'])
                self.assertEqual(len(prompts), before, 'authenticated disabled review uses zero AI')
                self.assertNotIn('SECRET', journal.getvalue())
                self.assertNotIn('unrequested secret content', journal.getvalue())

    def security(self):
        return deploy.load_security({'securityReviewScript': str(Path(__file__).resolve().parents[5]/'modules/development/ai/agent/security-review.py')})

    def test_checkpoint_exact_closure_policy_target_and_branch_context(self):
        security = self.security()
        approved = dict(source='approved', closure='closure', target='metal', policy='current',
                        branch=security.branch_key('main'))
        review = mock.Mock()
        review.baseline_files.side_effect = lambda path: {'file': 'candidate' if str(path)=='approved' else 'activated'}
        review.source_diff.side_effect = lambda old,new,*_modes: old['file'] if old != new else ''
        with mock.patch.object(security,'policy_digest',return_value='current'), \
             mock.patch.object(Path,'resolve',return_value=Path('approved')), \
             mock.patch.object(security,'records',return_value=[(None,approved)]):
            verify=mock.Mock()
            exact,base,files=security.choose_checkpoint({},'metal','approved','closure','main','activated',{'file':'candidate'},review,verify)
            self.assertTrue(exact); self.assertEqual(base,'approved')
            self.assertFalse(security.choose_checkpoint({},'metal','approved','DIFFERENT','main','activated',{'file':'candidate'},review,verify)[0])
            # New exact merged source always needs review, even when another branch is approved.
            self.assertFalse(security.choose_checkpoint({},'metal','merged','closure','feature','activated',{'file':'candidate'},review,verify)[0])
            self.assertEqual(security.choose_checkpoint({},'metal','merged','closure','feature','activated',{'file':'candidate'},review,verify)[1],'approved')
            approved['policy']='old'
            self.assertFalse(security.choose_checkpoint({},'metal','approved','closure','main','activated',{'file':'candidate'},review,verify)[0])

    def test_trust_active_requires_enabled_review_root_and_exact_operator(self):
        config = dict(modelReviewEnabled=True, operatorUid=1000, clientUid=2000)
        for root, uid, enabled in [(1000, 1000, True), (0, 2000, True), (0, 1000, False)]:
            with mock.patch.object(deploy.os, 'geteuid', return_value=root), self.assertRaises(deploy.DeploymentFailure):
                deploy.trust_active(dict(config, modelReviewEnabled=enabled), uid, 23)

    def test_trust_active_rechecks_runtime_target_and_policy_before_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'; source.mkdir()
            runtime = root / 'runtime'
            staged = root / 'staged'
            for closure in (runtime, staged):
                (closure / 'etc/phoenix-agent').mkdir(parents=True)
                (closure / 'etc/phoenix-agent/activated-source').symlink_to(source)
                (closure / 'etc/phoenix-agent/active-provenance.json').write_text(json.dumps(dict(version=1, target='metal', source=str(source))))
            security = mock.Mock()
            security.policy_digest.return_value = 'installed-policy'
            review = mock.Mock()
            config = dict(modelReviewEnabled=True, target='metal', operatorUid=1000, clientUid=2000,
                          work=directory, baseline=str(source), builderUser='builder', nix='nix')
            original = Path.resolve
            current = runtime
            def resolve(path, *args, **kwargs):
                if path == Path('/run/current-system'): return current
                if path == Path('/nix/var/nix/profiles/system'): return staged
                return original(path, *args, **kwargs)
            def publish(*args, **kwargs):
                kwargs['before_publish']()
            security.approve.side_effect = publish
            with mock.patch.object(deploy.os, 'geteuid', return_value=0), mock.patch.object(Path, 'resolve', resolve), mock.patch.object(deploy, 'activation_guard', return_value=contextlib.nullcontext(42)), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy, 'store_file', side_effect=lambda path: path), mock.patch.object(deploy, 'load_security', return_value=security), mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(deploy, 'as_user', return_value=str(runtime).encode()) as evaluate:
                result = deploy.trust_active(config, 1000, 22)
                self.assertEqual(result['closure'], str(runtime), 'staged boot profile is not the adopted runtime')
                self.assertEqual(security.approve.call_args.args[1]['closure'], str(runtime))
                self.assertNotEqual(result['closure'], str(staged))
                evaluate.assert_not_called()
                provenance = runtime / 'etc/phoenix-agent/active-provenance.json'
                valid = dict(version=1, target='metal', source=str(source))
                for value, code in [(dict(valid, target='vm'), 'baseline-target-mismatch'),
                                    (dict(valid, source=str(staged)), 'baseline-provenance-invalid'),
                                    (dict(valid, extra='caller'), 'baseline-provenance-invalid'),
                                    (dict(valid, version=True), 'baseline-provenance-invalid'),
                                    ([], 'baseline-provenance-invalid')]:
                    provenance.write_text(json.dumps(value))
                    security.approve.reset_mock()
                    with self.assertRaisesRegex(deploy.DeploymentFailure, code):
                        deploy.trust_active(config, 1000, 22)
                    security.approve.assert_not_called()
                provenance.write_text('{broken')
                with self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-provenance-invalid'):
                    deploy.trust_active(config, 1000, 22)
                provenance.unlink()
                with self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-provenance-missing'):
                    deploy.trust_active(config, 1000, 22)
                provenance.write_text(json.dumps(valid))
                def changed(*args, **kwargs):
                    nonlocal current
                    current = staged
                    kwargs['before_publish']()
                security.approve.side_effect = changed
                with self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-state-changed'):
                    deploy.trust_active(config, 1000, 22)
                current = runtime
                security.approve.side_effect = publish
                security.policy_digest.side_effect = ['old', 'changed']
                with self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-state-changed'):
                    deploy.trust_active(config, 1000, 22)

    def test_runtime_provenance_rejects_mutable_escape_and_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mutable = root / 'mutable.json'
            mutable.write_text('{}')
            marker = root / 'marker.json'
            marker.symlink_to(mutable)
            with self.assertRaisesRegex(ValueError, 'escapes immutable store'):
                deploy.store_file(marker)
            provenance = root / 'etc/phoenix-agent/active-provenance.json'
            provenance.parent.mkdir(parents=True)
            provenance.write_text('{"version":1,"version":1,"target":"metal","source":"source"}')
            with mock.patch.object(deploy, 'store_file', side_effect=lambda path: path), self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-provenance-invalid'):
                deploy.active_provenance(str(root), 'source', 'metal')
            provenance.write_text('x' * 4097)
            with mock.patch.object(deploy, 'store_file', side_effect=lambda path: path), self.assertRaisesRegex(deploy.DeploymentFailure, 'baseline-provenance-invalid'):
                deploy.active_provenance(str(root), 'source', 'metal')

    def test_trust_active_main_rejects_caller_paths_and_uses_pkexec_operator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'installed.json'
            path.write_text('{}')
            for tail in [['/caller/source'], ['--expected-source', '/caller/source'], ['--expected-profile', '/caller/closure']]:
                output = io.StringIO()
                with mock.patch.object(deploy.sys, 'argv', ['controller', str(path), 'trust-active', *tail]), mock.patch.object(deploy, 'trust_active') as trust, contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                    deploy.main()
                trust.assert_not_called()
                self.assertEqual(json.loads(output.getvalue())['code'], 'baseline-arguments-denied')
                self.assertNotIn('/caller', output.getvalue())
            with mock.patch.object(deploy.sys, 'argv', ['controller', str(path), 'trust-active']), mock.patch.dict(deploy.os.environ, {'PKEXEC_UID': '1000'}), mock.patch.object(deploy, 'trust_active', return_value={'ok': True}) as trust, contextlib.redirect_stdout(io.StringIO()):
                deploy.main()
            self.assertEqual(trust.call_args.args[1], 1000)

    def test_checkpoint_rejects_unbound_approved_closure_even_as_context(self):
        security = self.security()
        record = dict(source='approved', closure='wrong-closure', target='metal', policy='current', branch=security.branch_key('main'))
        with mock.patch.object(security, 'policy_digest', return_value='current'), mock.patch.object(security, 'records', return_value=[(None, record)]), mock.patch.object(Path, 'resolve', return_value=Path('different-source')), self.assertRaisesRegex(ValueError, 'closure/source binding'):
            security.choose_checkpoint({}, 'metal', 'candidate', 'candidate-closure', 'other-branch', 'active', {}, mock.Mock(), mock.Mock())

    def test_checkpoint_state_ownership_and_atomic_write(self):
        security=self.security()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); record=path/'record.json'
            security.write_record(record, {'approved':False})
            self.assertEqual(record.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(record.read_text()),{'approved':False})
            self.assertEqual(list(path.glob('.record-*')),[])
            link=path/'link.json'; link.symlink_to(record)
            with self.assertRaises(OSError):security.read_record(link)
            record.chmod(0o666)
            with self.assertRaises(ValueError):security.read_record(record)
            with mock.patch.object(security.os,'geteuid',return_value=1000):
                with self.assertRaises(ValueError):security.state_directory({'securityReviewState':directory})
            path.chmod(0o777)
            with mock.patch.object(security.os,'geteuid',return_value=0):
                with self.assertRaises(ValueError):security.state_directory({'securityReviewState':directory})

    def test_policy_digest_changes_with_effective_review_execution_identity(self):
        security=self.security()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trusted-policy';path.write_text('installed review policy')
            config={key:str(path) for key in ('policy','reviewScript','securityReviewScript','controller')}
            config.update(codex='/nix/store/pinned-codex',model='model',effort='medium',bwrap='/nix/store/bwrap',
                          python='/nix/store/python',setpriv='/nix/store/setpriv',caBundle='/nix/store/ca-bundle')
            digest=security.policy_digest(config)
            for key in ('adapter','clientUid','operatorUid','updaterUid','codex','model','effort','bwrap','python','setpriv','caBundle'):
                with self.subTest(key=key):
                    self.assertNotEqual(digest,security.policy_digest(dict(config,**{key:'changed execution identity'})))
            authority = Path(directory) / 'authorization.json'
            authority.write_text(json.dumps({'updaterUid': 1000}))
            bound = dict(config, authorizationPolicy=str(authority))
            before = security.policy_digest(bound)
            authority.write_text(json.dumps({'updaterUid': 2000}))
            self.assertNotEqual(before, security.policy_digest(bound))
            path.write_text('changed installed review policy')
            self.assertNotEqual(digest,security.policy_digest(config))

    def test_security_fingerprint_survives_unrelated_repository_relocation(self):
        security = self.security()
        owner = Path(__file__).resolve().parents[5] / 'modules/development/ai/agent'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = root / 'single-file-packages'; packages.mkdir()
            def package(name, contents):
                identifier = hashlib.sha256(contents.encode()).hexdigest()
                path = packages / (identifier + '-' + name)
                path.write_text(contents)
                return str(path)
            library = package('authorization.py', (owner / 'authorization/request.py').read_text())
            transport = package('transport.json', (owner / 'transport.json').read_text())
            def snapshot(name):
                repo = root / name; repo.mkdir()
                config = {}
                for key, filename in [('policy', 'review-policy.md'), ('reviewScript', 'deploy-review.py'), ('securityReviewScript', 'security-review.py'), ('controller', 'deployment.py')]:
                    contents = (owner / filename).read_text().replace('@authorizationLibrary@', library).replace('@deploymentTransportPolicy@', transport)
                    path = repo / filename; path.write_text(contents); config[key] = str(path)
                config.update(authorizationLibrary=library, deploymentTransportPolicy=transport, adapter='codex', model='gpt-6-luna', effort='high')
                return config
            first, relocated = snapshot('repository-a'), snapshot('repository-b')
            (root / 'repository-b/unrelated-doc.md').write_text('unrelated repository change')
            expected = security.policy_digest(first)
            self.assertEqual(expected, security.policy_digest(relocated))
            for key in ('authorizationLibrary', 'deploymentTransportPolicy'):
                changed = dict(first, **{key: package(key, Path(first[key]).read_text() + '\nchanged')})
                self.assertNotEqual(expected, security.policy_digest(changed))
            Path(relocated['controller']).write_text(Path(relocated['controller']).read_text() + '\n# actual security code change')
            self.assertNotEqual(expected, security.policy_digest(relocated))

    def test_consuming_pruned_pending_record_is_idempotent(self):
        security = self.security()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nonce = 'a' * 64
            # Approval retention may prune the pending JSON before consumption.
            for field in ('source', 'closure'):
                (root / (nonce + '.pending.' + field)).symlink_to('/missing-store-root')
            with mock.patch.object(security, 'state_directory', return_value=root):
                security.consume_pending({}, nonce)
                security.consume_pending({}, nonce)
            self.assertEqual(list(root.iterdir()), [])

    def test_pending_override_identity_policy_and_action_are_fixed(self):
        security=self.security(); nonce='a'*64
        record=dict(nonce=nonce,uid=1000,policy='policy',target='metal',action='test',source='frozen',
                    closure='built',base='activated',profile='system-profile',profileSource='profile-source',branch='main')
        config=dict(target='metal')
        with mock.patch.object(security,'state_directory',return_value=Path('/protected')), \
             mock.patch.object(security,'policy_digest',return_value='policy'), \
             mock.patch.object(security,'read_record',return_value=record):
            verify=mock.Mock()
            self.assertEqual(security.load_pending(config,nonce,1000,verify),record)
            self.assertEqual(verify.call_count,4)
            for changes in [dict(uid=1001),dict(nonce='b'*64),dict(policy='changed'),dict(target='vm'),dict(action='update')]:
                with self.subTest(changes=changes),mock.patch.object(security,'read_record',return_value=dict(record,**changes)):
                    with self.assertRaises(ValueError):security.load_pending(config,nonce,1000,verify)
            with self.assertRaises(ValueError):security.load_pending(config,'../pending',1000,verify)

    def test_override_uses_only_protected_exact_state_and_rechecks_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source'; source.mkdir()
            closure=root/'closure'; marker=closure/'etc/phoenix-agent';marker.mkdir(parents=True)
            (marker/'activated-source').symlink_to(source)
            baseline=root/'baseline';baseline.mkdir()
            profile=root/'profile'; profile_marker=profile/'etc/phoenix-agent';profile_marker.mkdir(parents=True)
            (profile_marker/'activated-source').symlink_to(baseline)
            runtime=root/'runtime';runtime.mkdir()
            binding=dict(source=str(source),closure=str(closure),base=str(baseline),profile=str(profile),
                         profileSource=str(baseline),action='boot',target='metal',nonce='a'*64,branch='main')
            security=mock.Mock();security.load_pending.return_value=binding
            review=mock.Mock()
            config=dict(work=directory,baseline=str(baseline),modelReviewEnabled=True,operatorUid=1000,clientUid=2000,nixStore='nix-store',
                        systemdRun='systemd-run',python='python',controller='controller',configPath='config')
            original=Path.resolve
            def resolve(path,*args,**kwargs):
                if path==Path('/nix/var/nix/profiles/system'):return profile
                if path==Path('/run/current-system'):return runtime
                return original(path,*args,**kwargs)
            with mock.patch.object(deploy.os,'geteuid',return_value=0),mock.patch.object(deploy,'load_security',return_value=security), \
                 mock.patch.object(deploy,'load_review',return_value=review),mock.patch.object(deploy,'store_path'), \
                 mock.patch.object(deploy,'activation_executable'),mock.patch.object(Path,'resolve',resolve),contextlib.redirect_stdout(io.StringIO()):
                result=deploy.override(config,'a'*64,1000,22)
                security.load_pending.assert_called_once_with(config, 'a'*64, 2000, deploy.store_path)
                self.assertTrue(result['securityOverride'])
                argv=review.run.call_args.args[0]
                index=argv.index('activate')
                self.assertEqual(argv[index+1:index+3],[str(closure),'boot'])
                self.assertEqual(argv[argv.index('--expected-source')+1],str(source))
                self.assertEqual(argv[argv.index('--expected-profile')+1],str(profile))
                security.approve.assert_called_once_with(config,binding,'main',review.run)
                security.consume_pending.assert_called_once_with(config,'a'*64)
                review.run.reset_mock();security.approve.reset_mock();security.consume_pending.reset_mock()
                def failed_activation(argv,**kwargs):
                    if argv[0]=='systemd-run':raise ValueError('activation failed')
                    return b''
                review.run.side_effect=failed_activation
                with self.assertRaises(ValueError):deploy.override(config,'a'*64,1000,22)
                security.approve.assert_called_once_with(config,binding,'main',review.run)
                security.consume_pending.assert_called_once_with(config,'a'*64)
                self.assertTrue(any(call.args[0][0]=='systemd-run' for call in review.run.call_args_list))
                review.run.reset_mock();security.approve.reset_mock();security.consume_pending.reset_mock()
                review.run.side_effect=None
                config['baseline']=str(source)
                with self.assertRaises(ValueError):deploy.override(config,'a'*64,1000,22)
                review.run.assert_not_called();security.approve.assert_not_called();security.consume_pending.assert_not_called()
            with mock.patch.object(deploy.os,'geteuid',return_value=1000):
                with self.assertRaises(ValueError):deploy.override(config,'a'*64,1000,22)



if __name__ == '__main__':
    unittest.main()
