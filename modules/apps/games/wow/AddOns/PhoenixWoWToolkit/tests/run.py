"""Standalone checks. No NixOS checkout, third-party downloads or game writes required."""
import argparse
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--lua', default=shutil.which('lua'))
parser.add_argument('--opie', help='Installed OPie 8.10.2 source for the optional real-renderer proof')
parser.add_argument('--comparison-source', help='Blizzard TooltipComparisonManager.lua for the optional real-source proof')
parser.add_argument('--dialogue-ui', help='Installed Dialogue UI 1.0.7 source for the optional actual-renderer reuse proof')
args = parser.parse_args()
if not args.lua:
    parser.error('Lua is required: use --lua /path/to/lua')
root = Path(__file__).resolve().parents[1]
subprocess.run([args.lua, str(root / 'tests/core.lua'), str(root)], check=True)
for fixture in sorted(root.glob('features/*/tests/test.lua')):
    extra = []
    if fixture.parents[1].name == 'opie-visual-delay':
        if not args.opie:
            print('SKIP OPie real-source proof: supply --opie', flush=True)
            continue
        extra = [args.opie]
    elif fixture.parents[1].name == 'comparison-cleanup' and args.comparison_source:
        extra = [args.comparison_source]
    subprocess.run([args.lua, str(fixture), str(root), *extra], check=True)
if args.dialogue_ui:
    subprocess.run([args.lua, str(root / 'features/universal-item-tooltips/tests/dialogue-ui.lua'),
                    str(root), args.dialogue_ui, *([args.comparison_source] if args.comparison_source else [])], check=True)
