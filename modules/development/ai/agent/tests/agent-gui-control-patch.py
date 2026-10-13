"""Exact-source patch seam checks; pass --source for pinned extracted ASAR."""
import argparse
import importlib.util
from pathlib import Path
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
spec = importlib.util.spec_from_file_location('patcher', Path(__file__).resolve().parents[1] / 'gui-control-patch.py')
patcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(patcher)
files = list(args.source.glob('main-*.js'))
assert len(files) == 1
original = files[0].read_text()
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / files[0].name
    target.write_text(original)
    patcher.patch(directory)
    actual = target.read_text()
    link = 'w(e=>{let t=Rd(e),n=f.r(t);if(We.deepLinks.queueProcessArgs(e)){n&&Je();return}if(n){Je();return}Je({channel:`shortcut`,source:`shortcut`})})'
    expected = original.replace(link, 'w((e=>{g.app.on(`phoenix-shared-open-link`,t=>e([process.execPath,t]));return e;})(' + link[2:-1] + '))')
    expected = expected.replace('{...j(`newWindow`),click:async', '{...j(`newWindow`),id:`phoenix-shared-new-window`,click:async')
    assert actual == expected
    for invalid in [actual, original.replace('canQuitWithoutPrompt()', 'changed()'),
                    original.replace('{...j(`newWindow`),click:async','changed'),
                    original.replace(link, 'changed'), original + link,
                    original + '{...j(`newWindow`),click:async']:
        target.write_text(invalid)
        try: patcher.patch(directory)
        except ValueError: pass
        else: raise AssertionError('Changed/duplicate pinned source seam accepted')
print('agent-gui-control-patch: exact source retains menu/callback bodies; incompatible seams rejected')
