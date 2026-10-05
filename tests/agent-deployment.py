#!/usr/bin/env python3
"""Rejection and profile-recovery fixtures; no actual activation/network."""
import importlib.util
from pathlib import Path
import json
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('deployment', Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/deployment.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
routine_spec = importlib.util.spec_from_file_location('routine_update', Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/routine-update.py')
routine = importlib.util.module_from_spec(routine_spec)
routine_spec.loader.exec_module(routine)


class DeploymentTests(unittest.TestCase):
    def request(self):
        return dict(files={'flake.nix': '{}', 'flake.lock': '{}'},
                    modes={'flake.nix': '100644', 'flake.lock': '100644'},
                    commit='a' * 40, action='test', target='metal', reason='Implement requested isolated controller')

    def test_unsupported_capabilities_and_forged_verdict(self):
        good = self.request()
        deploy.request_valid(good, 'metal')
        for mutation in [dict(approved=True), dict(closure='/nix/store/evil'),
                         dict(argv=['sh']), dict(action='boot'), dict(action='update'), dict(action='sh'),
                         dict(target='vm'), dict(reason=''), dict(commit='HEAD')]:
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

    def test_larger_complete_source_preserves_wire_bound(self):
        request = self.request()
        request['files']['flake.nix'] = 'x' * (512 * 1024 + 1)
        deploy.request_valid(request, 'metal')
        self.assertEqual(deploy.SOURCE_LIMIT, 896 * 1024)
        self.assertEqual(deploy.LIMIT, 1024 * 1024)

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
        for mode in ['rejected', 'forged', 'model-failed', 'malformed', 'closure-mismatch', 'compacted', 'oversized', 'missing-upstream', 'forged-upstream', 'denied-upstream', 'bound-denial-upstream', 'forged-denial-upstream', 'forged-lineage-upstream']:
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
                review = deploy.load_review({'reviewScript': str(Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/deploy-review.py')})
                review.run = mock.Mock(return_value=b'')
                config = dict(target='metal', work=directory, builderUser='builder', reviewerUser='reviewer',
                              reviewHome='/protected/auth', nix='nix', nixStore='nix-store', baseline=str(baseline),
                              python='python', controller='controller', configPath='config', systemdRun='systemd-run',
                              upstreamReviewScript=str(Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/upstream-review.py'))
                request = self.request()
                if mode.endswith('upstream'):
                    upstream = root/'upstream.py'
                    upstream.write_text('MAX_BATCHES = 24\ndef evidence(before, after, resolve): return ["first", "second"]\ndef cli_evidence(before, after, resolve): return []\n')
                    config['upstreamReviewScript'] = str(upstream)
                    request['files']['flake.lock'] = '{"updated":true}'
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
                    if mode in {'forged-upstream', 'denied-upstream'}:
                        envelope['upstreamVerdicts'] = [dict(deploy.upstream_binding(binding,b,i),
                            approved=True,summary='fixture') for i,b in enumerate(['first','second'])]
                        if mode == 'forged-upstream': envelope['upstreamVerdicts'][0]['evidenceDigest']='forged'
                        else: envelope['upstreamVerdicts'][0]['approved']=False
                    if mode in {'bound-denial-upstream', 'forged-denial-upstream', 'forged-lineage-upstream'}:
                        envelope = dict(status='verdict', upstreamDenialIndex=0,
                            verdict=dict(deploy.upstream_binding(binding,'first',0), approved=False, summary='fixture'))
                        if mode == 'forged-denial-upstream': envelope['verdict']['nonce']='forged'
                        if mode == 'forged-lineage-upstream': envelope['verdict']['affectedInputNodes']=['nixpkgs']
                    return json.dumps(envelope).encode()
                account = mock.Mock(pw_uid=os.getuid(), pw_gid=os.getgid())
                with mock.patch.object(Path, 'resolve', resolve), contextlib.redirect_stdout(io.StringIO()), mock.patch.object(deploy, 'load_review', return_value=review), mock.patch.object(deploy, 'as_user', side_effect=user_command), mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), mock.patch.object(deploy.pwd, 'getpwnam', return_value=account):
                    with self.assertRaises(deploy.DeploymentFailure) as failure:
                        deploy.process(config, request, os.getuid(), 22)
                self.assertIn(failure.exception.stage, {'verdict', 'review', 'closure-binding'})
                if mode in {'rejected', 'bound-denial-upstream'}:
                    self.assertIsInstance(failure.exception, deploy.DeploymentDenied)
                    self.assertEqual(failure.exception.summary, 'fixture')
                    self.assertEqual(failure.exception.code, 'model-denied')
                elif mode in {'forged', 'forged-denial-upstream', 'forged-lineage-upstream'}:
                    self.assertEqual(failure.exception.code, 'binding-mismatch')
                self.assertFalse(any(call.args[0][0] == 'systemd-run' for call in review.run.call_args_list))

    def test_worker_reports_denial_separately_from_native_or_schema_failure(self):
        review = deploy.load_review({'reviewScript': str(Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/deploy-review.py')})
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
            config = dict(migrationMarker=str(root / 'migrated'), loginHome=str(login), reviewHome=str(state), clientUid=os.getuid(), reviewerUser='reviewer')
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

    def test_routine_update_reaches_boot_without_invoking_reviewer(self):
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
            class Review:
                run = mock.Mock(return_value=b'')
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
                    return str(closure).encode()
                if argv[:3] == ['nix', 'flake', 'metadata']:
                    locked = json.loads(candidate['flake.lock'])['nodes']['stable']['locked']
                    return json.dumps(dict(locked=locked, path='/nix/store/' + 'f' * 32 + '-source')).encode()
                raise AssertionError('unexpected unprivileged command')
            config = dict(target='metal', work=directory, builderUser='builder', reviewerUser='reviewer',
                          reviewHome='/protected/auth', nix='nix', nixStore='nix-store', baseline='/etc/phoenix-agent/activated-source',
                          routineUpdateScript=str(Path(__file__).resolve().parents[1] / 'modules/development/ai/agent/routine-update.py'),
                          system='x86_64-linux', systemdRun='systemd-run', configPath='config', controller='controller',
                          python='python', activationEnvironment={})
            request = dict(files=candidate, modes=modes, commit='a' * 40, action='update', target='metal',
                           reason='Stage deterministic stable package updates',
                           expectedBase=str(baseline), expectedProfile=str(profile))
            with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(Path, 'resolve', resolve), \
                 mock.patch.object(deploy, 'load_review', return_value=Review), \
                 mock.patch.object(deploy, 'as_user', side_effect=as_user), \
                 mock.patch.object(deploy, 'store_path'), mock.patch.object(deploy, 'activation_executable'), \
                 mock.patch.object(deploy.pwd, 'getpwnam', return_value=account), \
                 mock.patch.object(deploy, 'request_valid', wraps=deploy.request_valid):
                result = deploy.process(config, request, os.getuid(), 42)
            self.assertTrue(result['ok'])
            self.assertEqual(result['action'], 'update')
            self.assertEqual([user for user, _argv in as_user_calls], ['builder', 'builder', 'builder'])
            self.assertEqual(Review.run.call_count, 4)  # realize source/closure/runtime, then transient activation
            activation = next(call.args[0] for call in Review.run.call_args_list
                              if call.args[0][0] == 'systemd-run')
            self.assertEqual(activation[activation.index('activate') + 2], 'update')
            self.assertFalse(any(user == 'reviewer' for user, _argv in as_user_calls))

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


    def test_scoped_upstream_verdicts_bind_every_evidence_batch(self):
        binding={'source':'immutable-source','base':'baseline','closure':'immutable-closure','nonce':'fresh'}
        first=deploy.upstream_binding(binding,'first exact implementation',0)
        second=deploy.upstream_binding(binding,'second exact implementation',1)
        self.assertNotEqual(first['evidenceDigest'],second['evidenceDigest'])
        self.assertNotEqual(first['scope'],second['scope'])
        review=deploy.load_review({'reviewScript':str(Path(__file__).resolve().parents[1]/'modules/development/ai/agent/deploy-review.py')})
        verdict=dict(first,approved=True,summary='fixture')
        review.validate_verdict(verdict,first)
        with self.assertRaises(review.ReviewVerdictError): review.validate_verdict(verdict,second)

    def test_manual_cli_source_evidence_runs_even_when_flake_lock_is_unchanged(self):
        upstream = mock.Mock()
        upstream.evidence.return_value = []
        upstream.cli_evidence.return_value = ['reviewer CLI evidence']
        before = {'flake.lock': 'unchanged lock', 'modules/development/ai/agent/reviewer-codex.nix': 'old'}
        after = dict(before, **{'modules/development/ai/agent/reviewer-codex.nix': 'new'})
        result = deploy.collect_upstream(upstream, 'boot', before, after, mock.Mock(), mock.Mock())
        upstream.evidence.assert_not_called()
        upstream.cli_evidence.assert_called_once_with(before, after, upstream.cli_evidence.call_args.args[2])
        self.assertEqual(result, ['reviewer CLI evidence'])
        self.assertEqual(deploy.collect_upstream(upstream, 'update', before, after, mock.Mock(), mock.Mock()), [])

    def test_worker_reviews_all_upstream_batches_before_complete_repository(self):
        review=deploy.load_review({'reviewScript':str(Path(__file__).resolve().parents[1]/'modules/development/ai/agent/deploy-review.py')})
        binding={'source':'/immutable/source','nonce':'fresh'}
        payload=dict(binding=binding,files={},diff='complete configuration',upstreamBatches=['first implementation','second implementation'])
        with tempfile.TemporaryDirectory() as directory:
            output=io.StringIO()
            def approve(config,binding,files,diff,temporary):return dict(binding,approved=True,summary='fixture')
            with mock.patch.object(deploy,'load_review',return_value=review),mock.patch.object(review,'review',side_effect=approve) as calls, \
                 mock.patch('sys.stdin',io.StringIO(json.dumps(payload))),contextlib.redirect_stdout(output):
                deploy.worker({},directory)
            result=json.loads(output.getvalue())
            self.assertEqual(calls.call_count,3)
            self.assertEqual(len(result['upstreamVerdicts']),2)
            self.assertNotIn('scope',result['verdict'])


if __name__ == '__main__':
    unittest.main()
