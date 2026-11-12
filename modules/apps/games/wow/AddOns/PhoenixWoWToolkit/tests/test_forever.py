"""Check the Forever manifest without accessing a game installation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ForeverManifestTests(unittest.TestCase):
    def test_forever_loads_checked_features_in_dependency_order(self):
        retail = (ROOT / 'PhoenixWoWToolkit.toc').read_text().splitlines()
        forever = (ROOT / 'PhoenixWoWToolkit_Camelot.toc').read_text().splitlines()
        self.assertIn('## Interface: 16001', forever)
        self.assertIn('## SavedVariables: PhoenixWoWToolkitDB', retail)
        self.assertIn('## SavedVariables: PhoenixWoWToolkitDB', forever)
        files = [line for line in forever if line and not line.startswith('#')]
        self.assertEqual(files, [
            'Core.lua', 'Options.lua',
            'features/objective-tracker/Feature.lua',
            'features/opie-visual-delay/Renderer.lua',
            'features/opie-visual-delay/Feature.lua',
            'features/universal-item-tooltips/Comparison.lua',
            'features/universal-item-tooltips/Attachments.lua',
            'features/universal-item-tooltips/DialogueUI.lua',
            'features/universal-item-tooltips/Preview.lua',
            'features/universal-item-tooltips/AuraBackground.lua',
            'features/universal-item-tooltips/Style.lua',
            'features/universal-item-tooltips/Feature.lua',
            'features/comparison-cleanup/Feature.lua',
            'features/combat-tracking/Model.lua',
            'features/combat-tracking/Display.lua',
            'features/combat-tracking/Feature.lua',
            'features/combat-tracking/Options.lua',
            'features/elvui-hold-to-cast/Feature.lua',
            'features/wowpro-button-bar/Feature.lua',
        ])
        for filename in files:
            self.assertTrue((ROOT / filename).is_file())


if __name__ == '__main__':
    unittest.main()
