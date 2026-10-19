"""Fast deployment contract checks, using only disposable state."""
import importlib.util
import json
from pathlib import Path
import tempfile

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).parents[1]/'deploy-vault.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as root:
    root = Path(root)
    source, vault = root/'source', root/'vault'
    source.mkdir()
    (source/'phoenix-letter.typ').write_text('first')
    settings = vault/'.obsidian/plugins/omd-to-typst/data.json'
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({'defaultTemplate':'formal', 'unrelated':42, 'templates':[{'name':'formal','path':'formal.typ'}]}))
    module.deploy(source, vault, True)
    target = vault/'3-misc/phoenix-typst/omd2typst/phoenix-letter.typ'
    stamp = target.stat().st_mtime_ns
    module.deploy(source, vault, True)
    assert target.stat().st_mtime_ns == stamp
    data = json.loads(settings.read_text())
    assert data['unrelated'] == 42 and data['defaultTemplate'] == 'formal'
    assert len(data['templates']) == 2 and data['outputMode'] == 'same-folder'
    (source/'phoenix-letter.typ').write_text('second')
    module.deploy(source, vault)
    assert target.read_text() == 'second'
    target.unlink()
    target.symlink_to(source/'phoenix-letter.typ')
    try:
        module.deploy(source, vault)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Must preserve unexpected symlinks')
print('PASS: idempotence, settings preservation, source refresh, symlink preservation')
