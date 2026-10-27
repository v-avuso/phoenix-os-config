#!/usr/bin/env python3
"""Disposable Git and mocked network/deployment acceptance; no live updates."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'modules/services/updates'))
import runner
import candidate


class RunnerTests(unittest.TestCase):
    def test_root_guard_rejects_before_preparation(self):
        config = dict(target='metal', targetGuard='/nix/store/fixed-target/bin/phoenix-target')
        with patch.object(runner.subprocess, 'run', side_effect=subprocess.CalledProcessError(2, 'guard')) as probe:
            source = MagicMock()
            with self.assertRaises(runner.UpdateDenied): runner.run(config, source)
            source.assert_not_called()
            self.assertEqual(source.mock_calls, [])
            self.assertEqual(probe.call_args.args[0], [config['targetGuard'], '--require', 'metal'])
        with patch.object(runner, '__file__', '/nix/store/fixed-updater.py'):
            with self.assertRaises(runner.UpdateDenied): runner.verify_runtime_target({'target': 'metal'})

    def test_help_and_unknown_options_cannot_start_update(self):
        import contextlib
        import io
        for option, status in [('--help', 0), ('--unknown', 2)]:
            with patch.object(sys, 'argv', ['phoenix-update', '/not-read', option]), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit) as result:
                runner.main()
            self.assertEqual(result.exception.code, status)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'fixture')
        self.git('config', 'user.email', 'fixture@localhost')
        self.git('config', 'commit.gpgSign', 'false')
        for name in ('flake.nix', 'flake.lock', 'config/updates.json'):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}\n' if name.startswith('flake') else (ROOT / name).read_text())
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.config = dict(repo=str(self.repo), git=shutil.which('git'), path='/usr/bin:/bin')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True)

    def candidate(self):
        path = self.repo / 'flake.lock'
        path.write_text('{"new": true}\n')
        self.git('add', 'flake.lock')
        self.git('commit', '-qm', 'update')
        commit = self.git('rev-parse', 'HEAD').strip()
        self.git('reset', '--hard', self.head)
        return commit

    def test_existing_typst_links_survive_candidate_transport_and_baseline_comparison(self):
        prefix = 'modules/apps/documents/typst/'
        links = [prefix + 'template-adapters/omd2typst/phoenix-letter.typ',
                 prefix + 'templates/phoenix-letter/lib.typ', prefix + 'templates/phoenix-letter/typst.toml']
        for name in links:
            original = ROOT / name
            canonical = original.resolve().relative_to(ROOT)
            target = self.repo / canonical
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original.resolve().read_bytes())
            link = self.repo / name; link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(original.readlink())
        self.git('add', '.'); self.git('commit', '-qm', 'legitimate Typst links')
        head = self.git('rev-parse', 'HEAD').strip()
        files, modes = candidate._manifest(self.config['git'], self.repo, self.home, head)
        frozen = self.root / 'frozen'
        candidate.source_manifest.materialize(frozen, files, modes)
        self.assertEqual(candidate._commit_inventory(self.config['git'], self.repo, self.home, head),
                         candidate._inventory(frozen))
        for name in links:
            self.assertEqual(modes[name], '120000')
            self.assertEqual((frozen / name).readlink(), (ROOT / name).readlink())

    def test_candidate_submodule_and_unsafe_symlink_commits_are_rejected(self):
        for target in ['/etc/passwd', '../outside', 'missing', 'config', 'link']:
            with self.subTest(target=target):
                link = self.repo / 'link'
                link.unlink(missing_ok=True); link.symlink_to(target)
                self.git('add', 'link'); self.git('commit', '-qm', 'unsafe link')
                with self.assertRaises(ValueError):
                    candidate._manifest(self.config['git'], self.repo, self.home, self.git('rev-parse', 'HEAD').strip())
        self.git('rm', 'link')
        self.git('update-index', '--add', '--cacheinfo', '160000,' + self.head + ',vendor')
        self.git('commit', '-qm', 'submodule')
        with self.assertRaises(candidate.CandidateError):
            candidate._manifest(self.config['git'], self.repo, self.home, self.git('rev-parse', 'HEAD').strip())

    def test_source_transport_accepts_large_escaped_manifest_and_matches_controller(self):
        spec = importlib.util.spec_from_file_location('capacity_deploy', ROOT / 'modules/development/ai/agent/deployment.py')
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        review = deploy.load_review({'reviewScript': str(ROOT / 'modules/development/ai/agent/deploy-review.py')})
        self.assertEqual((candidate.SOURCE_LIMIT, candidate.WIRE_LIMIT), (deploy.SOURCE_LIMIT, deploy.LIMIT))
        self.assertEqual((review.SOURCE_LIMIT, review.WIRE_LIMIT), (candidate.SOURCE_LIMIT, candidate.WIRE_LIMIT))
        self.assertEqual(review.REVIEW_INPUT_LIMIT, 1024 * 1024)
        # A single blob exceeds both the former source cap and generic command-output cap.
        (self.repo / 'large.nix').write_text('\x01' * (3 * 1024 * 1024))
        self.git('add', 'large.nix')
        self.git('commit', '-qm', 'large escaped fixture')
        commit = self.git('rev-parse', 'HEAD').strip()
        files, modes = candidate._manifest(self.config['git'], self.repo, self.home, commit)
        request = dict(files=files, modes=modes, commit=commit, action='test', target='metal', reason='Capacity fixture')
        deploy.request_valid(request, 'metal')
        body = json.dumps(request).encode() + b'\n'
        self.assertGreater(len(body), 4 * 1024 * 1024)
        self.assertLessEqual(len(body), deploy.LIMIT)
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.return_value = b'{"ok":true,"action":"update"}\n'
        with patch.object(runner.socket, 'socket', return_value=connection):
            runner.controller(dict(self.config, target='metal', controllerSocket='/fixture'), candidate,
                              self.home, self.repo, commit, '/base', '/profile')
        sent = connection.sendall.call_args.args[0]
        self.assertLessEqual(len(sent), deploy.LIMIT)
        received = json.loads(sent)
        self.assertEqual(received['files'], files)
        self.assertEqual(received['action'], 'update')
        with tempfile.TemporaryDirectory() as directory:
            for name, content in files.items():
                path = Path(directory) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            self.assertEqual(review.baseline_files(Path(directory)), files)
        (self.repo / 'large.nix').write_text('x' * candidate.SOURCE_LIMIT)
        self.git('add', 'large.nix')
        self.git('commit', '-qm', 'over capacity')
        with self.assertRaises(candidate.SourceTransportError) as failure:
            candidate._manifest(self.config['git'], self.repo, self.home, self.git('rev-parse', 'HEAD').strip())
        self.assertEqual((failure.exception.stage, failure.exception.code), ('source-transport', 'source-capacity-exceeded'))
        request['files']['large.nix'] = 'x' * deploy.SOURCE_LIMIT
        with self.assertRaises(deploy.DeploymentFailure) as failure:
            deploy.request_valid(request, 'metal')
        self.assertEqual((failure.exception.stage, failure.exception.code), ('source-transport', 'source-capacity-exceeded'))

    def test_packaged_standalone_entrypoints_use_explicit_policy(self):
        # Simulate Nix path substitution in a directory with no sibling helpers.
        policy = ROOT / 'modules/development/ai/agent/transport.json'
        with tempfile.TemporaryDirectory() as directory:
            for name, relative in [('deploy', 'modules/development/ai/agent/deployment.py'),
                                   ('review', 'modules/development/ai/agent/deploy-review.py'),
                                   ('candidate', 'modules/services/updates/candidate.py')]:
                script = Path(directory) / (name + '.py')
                script.write_text((ROOT / relative).read_text().replace('@deploymentTransportPolicy@', str(policy)).replace('@authorizationLibrary@', str(ROOT / 'modules/development/ai/agent/authorization/request.py')).replace('@sourceManifestLibrary@', str(ROOT / 'modules/development/ai/agent/source-manifest.py')))
                spec = importlib.util.spec_from_file_location('isolated_' + name, script)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertEqual(module.SOURCE_LIMIT, candidate.SOURCE_LIMIT)
                self.assertEqual(module.LIMIT if name == 'deploy' else module.WIRE_LIMIT, candidate.WIRE_LIMIT)

    def test_updater_wire_failure_is_typed_and_precedes_socket(self):
        with patch.object(candidate, '_manifest', return_value=({'flake.nix': '\x01' * 100}, {'flake.nix': '100644'})), \
             patch.object(candidate, 'WIRE_LIMIT', 100), patch.object(runner.socket, 'socket') as socket:
            with self.assertRaises(candidate.SourceTransportError) as failure:
                runner.controller(dict(self.config, target='metal'), candidate, self.home, self.repo, self.head, '/base', '/profile')
        self.assertEqual((failure.exception.stage, failure.exception.code), ('source-transport', 'wire-capacity-exceeded'))
        socket.assert_not_called()

    def test_integrate_preserves_unrelated_staged_and_unstaged_edits(self):
        commit = self.candidate()
        (self.repo / 'config/updates.json').write_text((self.repo / 'config/updates.json').read_text() + ' ')
        (self.repo / 'new-user-file').write_text('staged user data\n')
        self.git('add', 'new-user-file')
        runner.integrate(self.config, candidate, self.home, self.head, commit, {'flake.lock'})
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), commit)
        self.assertEqual((self.repo / 'flake.lock').read_text(), '{"new": true}\n')
        self.assertEqual(self.git('diff', '--cached', '--name-only').strip(), 'new-user-file')
        self.assertEqual(self.git('diff', '--name-only').strip(), 'config/updates.json')
        self.assertEqual((self.repo / 'new-user-file').read_text(), 'staged user data\n')

    def test_checkout_and_integration_ignore_caller_filters(self):
        commit = self.candidate()
        sentinel = self.root/'filter-executed'
        script = self.root/'filter'
        script.write_text('#!/bin/sh\necho unsafe > "' + str(sentinel) + '"\n/bin/cat\n')
        script.chmod(0o755)
        self.git('config', 'filter.unsafe.smudge', str(script))
        self.git('config', 'filter.unsafe.clean', str(script))
        self.git('config', 'filter.unsafe.required', 'true')
        (self.repo/'.git/info/attributes').write_text('* filter=unsafe\n')
        tree = self.root/'candidate-tree'
        candidate.git(self.config['git'], self.repo, self.home, 'worktree', 'add', '-b', 'codex/fixture', str(tree), self.head)
        self.assertEqual((tree/'flake.lock').read_text(), '{}\n')
        self.assertFalse(sentinel.exists())
        runner.integrate(self.config, candidate, self.home, self.head, commit, {'flake.lock'})
        self.assertFalse(sentinel.exists())
        self.assertEqual((self.repo/'flake.lock').read_text(), '{"new": true}\n')
        candidate.git(self.config['git'], self.repo, self.home, 'worktree', 'remove', '--force', str(tree))

    def test_dirty_affected_file_rejects_without_changing_index_head_or_edit(self):
        commit = self.candidate()
        (self.repo / 'flake.lock').write_text('user lock edit\n')
        self.git('add', 'flake.lock')
        index = (self.repo / '.git/index').read_bytes()
        with self.assertRaisesRegex(ValueError, 'affected user edits'):
            runner.integrate(self.config, candidate, self.home, self.head, commit, {'flake.lock'})
        self.assertEqual((self.repo / '.git/index').read_bytes(), index)
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.head)
        self.assertEqual((self.repo / 'flake.lock').read_text(), 'user lock edit\n')

    def test_busy_index_and_changed_main_are_preserved(self):
        commit = self.candidate()
        (self.repo / '.git/index.lock').write_text('other Git operation')
        with self.assertRaises(FileExistsError):
            runner.integrate(self.config, candidate, self.home, self.head, commit, {'flake.lock'})
        self.assertEqual((self.repo / '.git/index.lock').read_text(), 'other Git operation')
        (self.repo / '.git/index.lock').unlink()
        self.git('commit', '--allow-empty', '-qm', 'concurrent user commit')
        with self.assertRaisesRegex(ValueError, 'main advanced'):
            runner.integrate(self.config, candidate, self.home, self.head, commit, {'flake.lock'})

    def test_policy_rejects_unknown_identifier_opaque_versions_and_missing_pin_reason(self):
        policy = json.loads((ROOT / 'config/updates.json').read_text())
        runner.validate_policy(policy)
        for hold in [{'pin': 'a'*40}, {'pin': 'a'*40, 'reason': ''},
                     {'pin': 'a'*40, 'reason': 'fix', 'resumeAtVersion': 'next'},
                     {'pin': 'HEAD', 'reason': 'fix'}]:
            mutated = dict(policy, holds={'firefox': hold})
            with self.assertRaises(ValueError):
                runner.validate_policy(mutated)
        with self.assertRaisesRegex(ValueError, 'identifier'):
            runner.validate_policy(dict(policy, holds={'invalid/path': {}}))

    def test_unknown_prerelease_version_cannot_release_hold(self):
        with patch.object(candidate, '_run') as command:
            self.assertFalse(runner.compare_version({}, candidate, '1.2.3-rc1', '1.2.3'))
            self.assertFalse(runner.compare_version({}, candidate, '1.2.3', '999-next'))
            command.assert_not_called()

    def test_community_check_pagination_requires_all_exact_successful_contexts(self):
        rev = 'a'*40
        records = [dict(name=n, head_sha=rev, app={'slug': 'github-actions'},
                        status='completed', conclusion='success') for n in candidate.COMMUNITY_CHECKS]
        import base64
        sri = 'sha256-' + base64.b64encode(bytes.fromhex('00'*32)).decode()
        payload = {'version': '26.930.31730'}
        for arch in ('amd64', 'arm64'):
            payload[arch] = dict(repositoryPath='pool/main/c/chatgpt/chatgpt_26.930.31730_%s.deb' % arch,
                                 sha256='00'*32, sri=sri)
        with patch.object(runner, 'fetch', side_effect=[{'check_runs': records[:2], 'total_count': 4},
                         {'check_runs': records[2:], 'total_count': 4}, payload]):
            self.assertEqual(runner.community(candidate, rev), payload['version'])
        records[0]['conclusion'] = 'failure'
        with patch.object(runner, 'fetch', return_value={'check_runs': records, 'total_count': 4}):
            with self.assertRaises(candidate.CandidateError):
                runner.community(candidate, rev)


    def setup_pipeline(self, hold=False):
        lock = {'version': 7, 'root': 'root', 'nodes': {'root': {'inputs': {a:a for a in runner.SOURCES}}}}
        for alias,(owner,repo,ref) in runner.SOURCES.items():
            lock['nodes'][alias] = {'original': {'type':'github','owner':owner,'repo':repo,'ref':ref},
                'locked': {'owner':owner,'repo':repo,'rev':'1'*40}, 'inputs': {}}
        (self.repo/'flake.lock').write_text(json.dumps(lock))
        policy = json.loads((self.repo/runner.POLICY).read_text())
        if hold:
            policy['holds']['codex-cli'] = {'pin': 'a'*40,
                'reason':'wait for fix','resumeAtVersion':'0.160.0'}
            (self.repo/runner.POLICY).write_text(json.dumps(policy))
        self.git('add','.'); self.git('commit','-qm','pipeline baseline')
        self.head=self.git('rev-parse','HEAD').strip()
        approved=self.root/'approved'; shutil.copytree(self.repo,approved,ignore=shutil.ignore_patterns('.git'))
        profile=self.root/'profile'; (profile/'etc/phoenix-agent').mkdir(parents=True)
        (profile/'etc/phoenix-agent/activated-source').symlink_to(approved)
        state=self.root/'state'; state.mkdir()
        nix=self.root/'nix'; nix.write_text("""#!%s
import json,pathlib,sys
if sys.argv[1] == 'eval':
 if '--expr' in sys.argv: print(1)
 else: print('0.160.0')
else:
 path=pathlib.Path('flake.lock'); data=json.loads(path.read_text())
 alias=sys.argv[sys.argv.index('--override-input')+1]
 data['nodes'][alias]['locked']['rev']=sys.argv[sys.argv.index('--override-input')+2].rsplit('/',1)[-1]
 path.write_text(json.dumps(data))
""" % sys.executable); nix.chmod(0o755)
        self.config.update(state=str(state),nixHome=str(state/'nix-home'),nix=str(nix),
            baseline=str(approved),systemProfile=str(profile),target='metal',controllerSocket='/fixture')

    def public_fetch(self,url):
        if 'releases/latest' in url:
            return {'tag_name':'rust-v0.160.0','draft':False,'prerelease':False,'published_at':'2026-10-05T00:00:00Z'}
        import base64
        payload={'version':'26.930.31730'}
        for arch in ('amd64','arm64'):
            payload[arch]=dict(repositoryPath='pool/main/c/chatgpt/chatgpt_26.930.31730_%s.deb'%arch,
                sha256='00'*32,sri='sha256-'+base64.b64encode(bytes.fromhex('00'*32)).decode())
        return payload

    def test_complete_update_releases_hold_only_in_successful_update_commit(self):
        self.setup_pipeline(hold=True)
        (self.repo/'user-note').write_text('keep staged work');self.git('add','user-note')
        def approved(config,c,home,tree,commit,base,profile):
            policy=json.loads((tree/runner.POLICY).read_text())
            self.assertNotIn('codex-cli',policy['holds'])
            self.assertEqual(self.git('rev-parse','HEAD').strip(),self.head)
            self.assertIn('codex-cli',json.loads((self.repo/runner.POLICY).read_text())['holds'])
            return dict(ok=True,action='boot',source='/reviewed/source')
        with patch.object(runner,'revision',return_value='2'*40), patch.object(runner,'community',return_value='26.930.31730'), \
             patch.object(runner,'fetch',side_effect=self.public_fetch),patch.object(runner,'controller',side_effect=approved):
            result=runner.run(self.config,candidate)
        self.assertEqual(result['status'],'staged')
        self.assertNotIn('codex-cli',json.loads((self.repo/runner.POLICY).read_text())['holds'])
        self.assertEqual(self.git('diff','--cached','--name-only').strip(),'user-note')
        self.assertEqual(self.git('show','--format=','--name-only','HEAD').strip().splitlines(),
                         ['config/updates.json','flake.lock'])

    def test_different_checked_out_branch_defers_before_network(self):
        self.setup_pipeline()
        self.git('checkout','-qb','feature')
        with patch.object(runner,'revision') as network:
            self.assertEqual(runner.run(self.config,candidate)['status'],'deferred')
            network.assert_not_called()

    def test_patch_threshold_removes_only_satisfied_entry(self):
        self.setup_pipeline()
        policy=json.loads((self.repo/runner.POLICY).read_text())
        policy['patches']={'codex-cli': {'reason':'temporary fix',
            'patchFiles':['config/update-patches/codex-fix.patch'], 'removeAtVersion':'0.160.0'}}
        (self.repo/runner.POLICY).write_text(json.dumps(policy))
        self.git('add','.');self.git('commit','-qm','approved fix')
        self.head=self.git('rev-parse','HEAD').strip()
        approved=Path(self.config['baseline']);shutil.rmtree(approved)
        shutil.copytree(self.repo,approved,ignore=shutil.ignore_patterns('.git'))
        with patch.object(runner,'revision',return_value='2'*40), patch.object(runner,'community',return_value='26.930.31730'), \
             patch.object(runner,'fetch',side_effect=self.public_fetch),patch.object(runner,'controller',return_value={'source':'/fixture'}):
            result=runner.run(self.config,candidate)
        self.assertEqual(result['status'],'staged')
        self.assertEqual(json.loads((self.repo/runner.POLICY).read_text())['patches'],{})
        self.assertEqual(self.git('branch','--list','codex/updates/*').strip(),'')

    def test_cleanup_deletes_owned_stale_candidates_but_preserves_debug_and_other_branches(self):
        self.setup_pipeline()
        original=self.head
        (self.repo/'flake.lock').write_text((self.repo/'flake.lock').read_text()+' ')
        self.git('add','flake.lock')
        self.git('-c','user.email=phoenix-updates@localhost','commit','-qm','service candidate')
        self.git('branch','codex/updates/'+'a'*32)
        self.git('branch','codex/updates/user-work')
        self.git('reset','--hard',original)
        self.config['cleanupBranches']=False
        runner.cleanup_branches(self.config,candidate,self.home)
        self.assertTrue(self.git('branch','--list','codex/updates/'+'a'*32).strip())
        self.config['cleanupBranches']=True
        runner.cleanup_branches(self.config,candidate,self.home)
        self.assertEqual(self.git('branch','--list','codex/updates/'+'a'*32).strip(),'')
        self.assertTrue(self.git('branch','--list','codex/updates/user-work').strip())

    def test_controller_streams_progress_and_preserves_failure_details(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.side_effect = [b'{"event":"progress","text":"Building candidate"}\n',
            b'{"ok":false,"stage":"build","code":"build-failed","summary":"Nix exited 1"}\n']
        with patch.object(runner.socket, 'socket', return_value=connection), \
             patch.object(candidate, '_manifest', return_value=({}, {})), \
             patch.object(runner, 'emit_progress') as output:
            with self.assertRaises(runner.UpdateDenied) as failure:
                runner.controller(dict(self.config, target='metal', controllerSocket='/fixture'), candidate,
                                  self.home, self.repo, self.head, '/base', '/profile')
        self.assertEqual(failure.exception.stage, 'build')
        self.assertEqual(failure.exception.code, 'build-failed')
        output.assert_called_with('Building candidate')
        self.assertTrue(json.loads(connection.sendall.call_args.args[0])['progress'])

    def test_startup_collects_failed_branch_even_when_baseline_defers(self):
        self.setup_pipeline()
        (self.repo/'flake.lock').write_text('old candidate')
        self.git('add', 'flake.lock')
        self.git('-c', 'user.email=phoenix-updates@localhost', 'commit', '-qm', 'failed candidate')
        stale = 'codex/updates/20261024-210015'
        pending = 'codex/updates/20261024-220015'
        checked = 'codex/updates/20261024-230015'
        for branch in (stale, pending, checked):
            self.git('branch', branch)
        self.git('reset', '--hard', self.head)
        self.git('worktree', 'add', str(self.root/'checked'), checked)
        state = Path(self.config['state'])
        details = dict(branch=stale, diagnostics='retained build error')
        (state/'failed-candidate.json').write_text(json.dumps(details))
        (state/'pending.json').write_text(json.dumps(dict(branch=pending)))
        # Defer before even reading the incomplete pending recovery record.
        self.git('checkout', '-b', 'other-work')
        with patch.object(runner, 'revision') as network:
            self.assertEqual(runner.run(self.config, candidate)['status'], 'deferred')
            network.assert_not_called()
        self.assertFalse(self.git('branch', '--list', stale).strip())
        for branch in (pending, checked):
            self.assertTrue(self.git('branch', '--list', branch).strip())
        self.assertEqual(json.loads((state/'failed-candidate.json').read_text()), details)

    def test_precommit_failure_preserves_previous_failed_candidate_details(self):
        self.setup_pipeline()
        retained = Path(self.config['state']) / 'failed-candidate.json'
        prior = dict(candidate='prior', branch='codex/updates/prior',
                     diagnostics='original error', log='/original.log')
        retained.write_text(json.dumps(prior))
        with patch.object(runner, 'revision', return_value='2'*40), \
             patch.object(runner, 'community', return_value='26.930.31730'), \
             patch.object(runner, 'fetch', side_effect=self.public_fetch), \
             patch.object(runner, 'validate_lock', side_effect=ValueError('precommit failure')):
            with self.assertRaisesRegex(ValueError, 'precommit failure'):
                runner.run(self.config, candidate)
        self.assertEqual(json.loads(retained.read_text()), prior)

    def test_progress_compacts_only_after_slack_is_exhausted(self):
        import io
        log = self.root / 'run.log'
        with patch.object(runner, 'RUN_LOG', log), patch.object(runner, 'LOG_LIMIT', 12), \
             patch.object(runner, 'LOG_SLACK', 4), patch.object(runner.sys, 'stderr', new_callable=io.StringIO):
            runner.emit_progress('a'*12)
            runner.emit_progress('bbb')
            self.assertEqual(log.stat().st_size, 15)
            runner.emit_progress('cc')
            self.assertEqual(log.read_bytes(), b'a'*7 + b'bbbcc')

    def test_human_result_is_readable(self):
        self.assertEqual(runner.format_result({'status': 'unchanged'}), 'Already up to date.')
        text = runner.format_result(dict(status='failed', reason='Nix exited 1', stage='build', code='build-failed'))
        self.assertIn('Update failed: Nix exited 1', text)
        self.assertIn('stage: build', text)

    def test_persistent_deferral_escalates_after_day_and_resets(self):
        initial = dict(status='deferred', reason='baseline differs')
        runner.track_deferral(self.root, initial, now=100)
        self.assertNotIn('attentionRequired', initial)
        repeated = dict(initial)
        runner.track_deferral(self.root, repeated, now=100+86400)
        self.assertTrue(repeated['attentionRequired'])
        self.assertIn('Attention required', runner.format_result(repeated))
        changed = dict(status='deferred', reason='checkout busy')
        runner.track_deferral(self.root, changed, now=100+86401)
        self.assertNotIn('attentionRequired', changed)
        self.assertEqual(json.loads((self.root/'deferral.json').read_text())['firstSeen'], 86501)
        runner.track_deferral(self.root, dict(status='unchanged'), now=90000)
        self.assertFalse((self.root/'deferral.json').exists())

    def test_progress_preserves_chunks_and_bounds_log_tail(self):
        import io
        log = self.root / 'run.log'
        with patch.object(runner, 'RUN_LOG', log), patch.object(runner, 'LOG_LIMIT', 12), patch.object(runner, 'LOG_SLACK', 0), \
             patch.object(runner.sys, 'stderr', new_callable=io.StringIO) as output:
            runner.emit_progress('first line\n')
            runner.emit_progress('second line\n')
        self.assertEqual(output.getvalue(), 'first line\nsecond line\n')
        self.assertEqual(log.read_bytes(), b'second line\n')

    def test_preparation_streams_before_exit_and_keeps_bounded_failure_tail(self):
        marker = self.root / 'feedback-seen'
        script = ("import pathlib,sys,time\n"
                  "sys.stderr.write('preparing\\n');sys.stderr.flush()\n"
                  "time.sleep(.3)\n"
                  "assert pathlib.Path(sys.argv[1]).exists()\n"
                  "sys.stderr.write('x'*20000+'final failure\\n');sys.stderr.flush()\n"
                  "sys.exit(7)\n")
        messages = []
        def feedback(text):
            messages.append(text)
            marker.touch()
        with self.assertRaises(candidate.CandidateError) as failure:
            candidate._run([sys.executable, '-c', script, str(marker)],
                           output_limit=100, progress=feedback)
        self.assertIn('exit 7', str(failure.exception))
        self.assertTrue(''.join(messages).startswith('preparing\n'))
        self.assertTrue(failure.exception.diagnostics.endswith('final failure\n'))
        self.assertLessEqual(len(failure.exception.diagnostics), 16384)

    def test_policy_summary_survives_failed_candidate_retention(self):
        self.setup_pipeline()
        summary = 'community-checks revision=' + 'a' * 40 + ': required check nix failed'
        error = runner.UpdateDenied(dict(stage='routine-policy', code='community-check-failed', summary=summary))
        with patch.object(runner,'revision',return_value='2'*40), patch.object(runner,'community',return_value='26.930.31730'), \
             patch.object(runner,'fetch',side_effect=self.public_fetch), patch.object(runner,'controller',side_effect=error):
            with self.assertRaises(runner.UpdateDenied):
                runner.run(self.config, candidate)
        retained = json.loads((Path(self.config['state'])/'failed-candidate.json').read_text())
        self.assertIn(summary, retained['reason'])
        self.assertIn(summary, runner.format_result(dict(status='failed', reason=str(error))))

    def test_failed_staging_keeps_hold_and_current_pins(self):
        self.setup_pipeline(hold=True)
        original=(self.repo/'flake.lock').read_bytes()
        with patch.object(runner,'revision',return_value='2'*40), patch.object(runner,'community',return_value='26.930.31730'), \
             patch.object(runner,'fetch',side_effect=self.public_fetch),patch.object(runner,'controller',side_effect=runner.UpdateDenied(dict(stage='build', code='build-failed', summary='denied', diagnostics='actual Nix failure'))):
            with self.assertRaisesRegex(ValueError,'denied'):
                runner.run(self.config,candidate)
        self.assertEqual(self.git('rev-parse','HEAD').strip(),self.head)
        self.assertEqual((self.repo/'flake.lock').read_bytes(),original)
        self.assertIn('codex-cli',json.loads((self.repo/runner.POLICY).read_text())['holds'])
        retained = json.loads((Path(self.config['state'])/'failed-candidate.json').read_text())
        self.assertEqual(retained['diagnostics'], 'actual Nix failure')
        self.assertEqual(retained['stage'], 'build')
        self.assertEqual(self.git('rev-parse', retained['branch']).strip(), retained['candidate'])
        runner.cleanup_branches(self.config, candidate, self.home)
        self.assertTrue(self.git('branch', '--list', retained['branch']).strip())
        self.assertFalse(list((Path(self.config['state'])/'worktrees').iterdir()))

    def test_unapproved_main_and_affected_local_edits_defer_before_network(self):
        self.setup_pipeline()
        (self.repo/'flake.lock').write_text('local work')
        with patch.object(runner,'revision') as network:
            self.assertEqual(runner.run(self.config,candidate)['status'],'deferred')
            network.assert_not_called()
        self.git('add','flake.lock');self.git('commit','-qm','user commit')
        with patch.object(runner,'revision') as network:
            self.assertEqual(runner.run(self.config,candidate)['status'],'deferred')
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
