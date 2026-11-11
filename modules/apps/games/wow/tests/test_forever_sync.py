"""Exercise Forever sync decisions without touching game files or the network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'forever-sync.sh'


class ForeverSyncTests(unittest.TestCase):
    def run_sync(self, response, manifest='["wowi:123", "github:author/addon"]'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'manifest.json').write_text(manifest)
            script = '''set -euo pipefail
instawow() {
  echo "$*" >> "$TEST_ROOT/calls"
  if [[ "$*" == *" list "* ]]; then echo '[]'; return 0; fi
  printf '%s\\n' "$RESPONSE"
  [[ "$RESPONSE" == success ]]
}
source "$1"
wow_sync_forever "$TEST_ROOT/manifest.json"
'''
            result = subprocess.run(['bash', '-c', script, 'test', str(HELPER)],
                env={**os.environ, 'TEST_ROOT': tmp, 'RESPONSE': response}, capture_output=True, text=True)
            calls = (root / 'calls').read_text() if (root / 'calls').exists() else ''
            return result, calls

    def test_ignores_wowi_and_installs_matching_release(self):
        result, calls = self.run_sync('success')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('wowi:123', calls)
        self.assertIn('install github:author/addon', calls)

    def test_skips_no_matching_release(self):
        result, _ = self.run_sync('no files found for: any_flavour=False')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installs_tomtom_but_skips_other_wowi_packages(self):
        result, calls = self.run_sync('success', '["wowi:7032", "wowi:123"]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('install wowi:7032', calls)
        self.assertNotIn('wowi:123', calls)

    def test_network_error_fails(self):
        result, _ = self.run_sync('internal error: timeout')
        self.assertNotEqual(result.returncode, 0)

if __name__ == '__main__':
    unittest.main()
