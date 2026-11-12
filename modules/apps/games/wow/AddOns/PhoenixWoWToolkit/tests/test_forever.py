"""Check the Forever manifest without accessing a game installation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ForeverManifestTests(unittest.TestCase):
    def test_forever_loads_the_shared_core_without_retail_features(self):
        retail = (ROOT / 'PhoenixWoWToolkit.toc').read_text().splitlines()
        forever = (ROOT / 'PhoenixWoWToolkit_Camelot.toc').read_text().splitlines()
        self.assertIn('## Interface: 16001', forever)
        self.assertIn('## SavedVariables: PhoenixWoWToolkitDB', retail)
        self.assertIn('## SavedVariables: PhoenixWoWToolkitDB', forever)
        files = [line for line in forever if line and not line.startswith('#')]
        self.assertEqual(files, ['Core.lua', 'Options.lua', 'features/elvui-hold-to-cast/Feature.lua'])
        for filename in files:
            self.assertTrue((ROOT / filename).is_file())


if __name__ == '__main__':
    unittest.main()
