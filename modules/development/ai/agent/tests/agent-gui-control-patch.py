"""Exact-source patch seam checks; pass --source for extracted ASAR build files."""
import argparse
import importlib.util
from pathlib import Path
import re
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('patcher', Path(__file__).resolve().parents[1] / 'gui-control-patch.py')
patcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(patcher)
files = list(args.source.glob('main-*.js'))
assert len(files) == 1
original = files[0].read_text()
menu = re.search(r'\{\.\.\.([A-Za-z_$][A-Za-z0-9_$]*)\(`newWindow`\),click:async', original)
assert menu is not None
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / files[0].name
    # Both inspected layouts and independent generated symbol renames must work.
    for symbol in (menu[1], 'renamedTranslation', '$generated_42'):
        source = original[:menu.start(1)] + symbol + original[menu.end(1):]
        descriptor = menu[0].replace(menu[1] + '(', symbol + '(')
        target.write_text(source)
        patcher.patch(directory)
        actual = target.read_text()
        expected = source.replace(descriptor, descriptor.replace(',click:', ',id:`phoenix-shared-new-window`,click:'))
        # Exact equality proves quit, activation and deep-link callback bodies
        # remain byte-for-byte upstream, including new Windows activation routing.
        assert actual == expected
    for invalid in [actual, original.replace('canQuitWithoutPrompt()', 'changed()'),
                    original.replace(menu[0], 'changed'), original + menu[0],
                    original.replace('desktop.quitConfirmation.cancel', 'changed')]:
        target.write_text(invalid)
        try: patcher.patch(directory)
        except ValueError: pass
        else: raise AssertionError('Changed/duplicate upstream source seam accepted')
print('agent-gui-control-patch: exact source changes only menu ID; renamed symbols accepted, incompatible seams rejected')
