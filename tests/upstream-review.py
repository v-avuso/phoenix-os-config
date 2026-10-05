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
            result = upstream.evidence(*files, lambda record: roots[record['rev'] == 'b'*40])
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

if __name__ == '__main__': unittest.main()
