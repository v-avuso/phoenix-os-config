#!/usr/bin/env python3
"""Exact immutable-dependency evidence fixtures; no Nix/network/root actions."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('upstream', ROOT / 'modules/development/ai/agent/upstream-review.py')
upstream = importlib.util.module_from_spec(spec); spec.loader.exec_module(upstream)


class EvidenceTests(unittest.TestCase):
    def test_exact_module_diff_includes_candidate_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            roots = [Path(directory) / 'old', Path(directory) / 'new']
            for root, content in zip(roots, ['old authority\n', 'new authority\n']):
                (root / 'nixos/modules').mkdir(parents=True)
                (root / 'nixos/modules/service.nix').write_text(content)
                (root / 'package').write_text('binary-looking ordinary package')
            records = [dict(type='github', owner='NixOS', repo='nixpkgs', rev=rev*40, narHash='sha256-value') for rev in ['a', 'b']]
            files = [{'flake.lock': json.dumps({'nodes': {'nixpkgs': {'locked': record}}})} for record in records]
            result = ''.join(upstream.evidence(*files, lambda record: roots[record['rev'] == 'b'*40]))
            self.assertIn('-old authority', result)
            self.assertIn('+new authority', result)
            self.assertIn('Exact candidate implementation:', result)
            self.assertIn('a'*40 + ' -> ' + 'b'*40, result)
            self.assertNotIn('binary-looking ordinary package', result)

    def test_unknown_source_and_excessive_authority_fail_closed(self):
        old = {'flake.lock': json.dumps({'nodes': {'x': {'locked': {'type': 'git'}}}})}
        new = {'flake.lock': json.dumps({'nodes': {'x': {'locked': {'type': 'path'}}}})}
        with self.assertRaises(ValueError):
            upstream.evidence(old, new, lambda _: None)
        with tempfile.TemporaryDirectory() as directory:
            roots = [Path(directory)/'old', Path(directory)/'new']
            for root in roots: root.mkdir()
            (roots[1]/'module.nix').write_text('x' * upstream.LIMIT)
            records = [dict(type='github', owner='publisher', repo='module', rev=r*40, narHash='sha256-value') for r in ['a','b']]
            files = [{'flake.lock': json.dumps({'nodes': {'x': {'locked': r}}})} for r in records]
            with self.assertRaisesRegex(ValueError, 'bound'):
                upstream.evidence(*files, lambda r: roots[r['rev'] == 'b'*40])


    def test_batches_preserve_every_whole_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            roots=[Path(directory)/'old',Path(directory)/'new']
            for root in roots: root.mkdir()
            for i in range(3): (roots[1]/('module%d.nix'%i)).write_text('line\n'*50000)
            records=[dict(type='github',owner='publisher',repo='module',rev=r*40,narHash='sha256-value') for r in ['a','b']]
            files=[{'flake.lock':json.dumps({'nodes':{'x':{'locked':r}}})} for r in records]
            batches=upstream.evidence(*files,lambda r:roots[r['rev']=='b'*40])
            self.assertGreater(len(batches),1)
            self.assertTrue(all(len(b.encode())<=upstream.LIMIT for b in batches))
            for i in range(3):
                self.assertEqual(sum(b.count('Exact candidate implementation: x/module%d.nix'%i) for b in batches),1)

    def test_cli_effective_version_and_guard_contract(self):
        recipe = 'modules/development/ai/agent/reviewer-codex.nix'
        before = {recipe: 'version = "0.159.0";'}
        after = {recipe: 'version = "0.160.0";'}
        held = dict(after, **{'config/updates.json': json.dumps({'holds': {'codex-cli': {'pin': {'version': '0.159.0'}}}})})
        self.assertEqual(upstream.cli_version(held), '0.160.0')
        self.assertEqual(upstream.cli_evidence(after, held, lambda _: self.fail('user hold changed reviewer')), [])
        self.assertEqual(upstream.cli_evidence({}, {}, lambda _: self.fail('absent adapter fetched')), [])
        with tempfile.TemporaryDirectory() as directory:
            roots = {version: Path(directory)/version for version in ['0.159.0', '0.160.0']}
            paths = ['codex-rs/exec/src/lib.rs', 'codex-rs/exec/src/event_processor_with_human_output.rs',
                     'codex-rs/core/src/compact.rs', 'codex-rs/protocol/src/protocol.rs']
            for version, root in roots.items():
                for name in paths:
                    path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('context compacted\nversion ' + version + '\n')
            batches = upstream.cli_evidence(before, after, roots.__getitem__)
            self.assertEqual(sum(b.count("Exact candidate implementation:") for b in batches), 4)
            self.assertTrue(all('Exact candidate implementation:' in b and 'version 0.160.0' in b for b in batches))
            (roots['0.160.0']/paths[1]).write_text('unknown reporting contract')
            with self.assertRaisesRegex(ValueError, 'compaction guard'):
                upstream.cli_evidence(before, after, roots.__getitem__)

if __name__ == '__main__': unittest.main()
