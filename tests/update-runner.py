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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'modules/services/updates'))
import runner
import candidate


class RunnerTests(unittest.TestCase):
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
        for name in ('flake.nix', 'flake.lock', 'config/updates.json', runner.CLI):
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
            lock['nodes'][alias] = {'original': {'owner':owner,'repo':repo,'ref':ref},
                'locked': {'owner':owner,'repo':repo,'rev':'1'*40}, 'inputs': {}}
        (self.repo/'flake.lock').write_text(json.dumps(lock))
        policy = json.loads((self.repo/runner.POLICY).read_text())
        if hold:
            policy['holds']['codex-cli'] = {'pin': {'version':'0.159.0','hash':'sha256-Ndpl1+hkTijqCk1OPYwVtAxrSSNW1M8hmGx+NB+Dok4='},
                'reason':'wait for fix','resumeAtVersion':'0.160.0'}
            (self.repo/runner.POLICY).write_text(json.dumps(policy))
        self.git('add','.'); self.git('commit','-qm','pipeline baseline')
        self.head=self.git('rev-parse','HEAD').strip()
        approved=self.root/'approved'; shutil.copytree(self.repo,approved,ignore=shutil.ignore_patterns('.git'))
        profile=self.root/'profile'; (profile/'etc/phoenix-agent').mkdir(parents=True)
        (profile/'etc/phoenix-agent/activated-source').symlink_to(approved)
        state=self.root/'state'; state.mkdir()
        nix=self.root/'nix'; nix.write_text("""#!%s
import json,pathlib,re,sys
if sys.argv[1] == 'eval':
 if '--expr' in sys.argv: print(1)
 else: print(re.search(r'version = \"([0-9.]+)\";',pathlib.Path('%s').read_text()).group(1))
else:
 path=pathlib.Path('flake.lock'); data=json.loads(path.read_text())
 alias=sys.argv[sys.argv.index('--override-input')+1]
 data['nodes'][alias]['locked']['rev']=sys.argv[sys.argv.index('--override-input')+2].rsplit('/',1)[-1]
 path.write_text(json.dumps(data))
""" % (sys.executable,runner.CLI)); nix.chmod(0o755)
        updater=self.root/'nix-update'; updater.write_text("""#!%s
from pathlib import Path
p=Path('%s');p.write_text(p.read_text().replace('version = \"0.159.0\";', 'version = \"0.160.0\";'))
""" % (sys.executable,runner.CLI)); updater.chmod(0o755)
        self.config.update(state=str(state),nixHome=str(state/'nix-home'),nix=str(nix),nixUpdate=str(updater),
            baseline=str(approved),systemProfile=str(profile),target='metal',controllerSocket='/fixture')

    def public_fetch(self,url):
        if 'releases?' in url:
            return [{'tag_name':'rust-v0.160.0','draft':False,'prerelease':False,'published_at':'2026-10-05T00:00:00Z'}]
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
                         ['config/updates.json','flake.lock',runner.CLI])

    def test_failed_review_keeps_hold_and_current_pins(self):
        self.setup_pipeline(hold=True)
        original=(self.repo/'flake.lock').read_bytes()
        with patch.object(runner,'revision',return_value='2'*40), patch.object(runner,'community',return_value='26.930.31730'), \
             patch.object(runner,'fetch',side_effect=self.public_fetch),patch.object(runner,'controller',side_effect=ValueError('denied')):
            with self.assertRaisesRegex(ValueError,'denied'):
                runner.run(self.config,candidate)
        self.assertEqual(self.git('rev-parse','HEAD').strip(),self.head)
        self.assertEqual((self.repo/'flake.lock').read_bytes(),original)
        self.assertIn('codex-cli',json.loads((self.repo/runner.POLICY).read_text())['holds'])

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
