"""Directory-link contract checks using only disposable vaults."""
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest import mock

spec = importlib.util.spec_from_file_location('deploy', Path(__file__).parents[1]/'deploy-vault.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def refuses(call):
    try:
        call()
    except (RuntimeError, OSError):
        return
    raise AssertionError('Expected unsafe or ambiguous destination to be refused')


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source, vault = root/'source', root/'vault'
    source.mkdir()
    (source/'phoenix-letter.typ').write_text('first')
    settings = vault/'.obsidian/plugins/omd-to-typst/data.json'
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({'defaultTemplate':'formal', 'unrelated':42, 'templates':[{'name':'formal','path':'formal.typ'}]}))
    module.deploy(source, vault, True)
    directory = vault/'3-misc/phoenix-typst/omd2typst'
    target = directory/'phoenix-letter.typ'
    assert directory.is_symlink()
    assert directory.resolve() == source.resolve()
    stamp = directory.lstat().st_mtime_ns
    module.deploy(source, vault, True)
    assert directory.lstat().st_mtime_ns == stamp
    data = json.loads(settings.read_text())
    assert data['unrelated'] == 42 and data['defaultTemplate'] == 'formal'
    assert len(data['templates']) == 2 and data['outputMode'] == 'same-folder'
    (source/'phoenix-letter.typ').write_text('second')
    assert target.read_text() == 'second', 'Edits must appear without a refresh command'
    (source/'additional.typ').write_text('new adapter')
    assert (directory/'additional.typ').read_text() == 'new adapter'
    directory.unlink()
    directory.mkdir()
    (directory/'private.typ').write_text('preserve me')
    refuses(lambda: module.deploy(source, vault))
    backup = directory.with_name('.omd2typst.before-symlink')
    backup.mkdir()
    refuses(lambda: module.deploy(source, vault, migrate_copies=True))
    assert (directory/'private.typ').read_text() == 'preserve me'
    backup.rmdir()
    with mock.patch.object(module.os, 'symlink', side_effect=OSError('fixture link failure')):
        refuses(lambda: module.deploy(source, vault, migrate_copies=True))
    assert (directory/'private.typ').read_text() == 'preserve me'
    assert not backup.exists()
    module.deploy(source, vault, migrate_copies=True)
    assert directory.is_symlink()
    assert (directory.with_name('.omd2typst.before-symlink')/'private.typ').read_text() == 'preserve me'
    directory.unlink()
    directory.symlink_to(root/'elsewhere', target_is_directory=True)
    refuses(lambda: module.deploy(source, vault, migrate_copies=True))
    directory.unlink()
    # A normal-looking leaf beneath a redirected parent must never be modified.
    outside = root/'outside'; outside.mkdir()
    parent = vault/'3-misc/phoenix-typst'
    parent.rename(parent.with_name('saved-parent'))
    parent.symlink_to(outside, target_is_directory=True)
    refuses(lambda: module.deploy(source, vault, migrate_copies=True))
    assert not list(outside.iterdir())
    # Explicit settings registration must not follow a redirected data file.
    external_settings = root/'outside-settings.json'
    external_settings.write_text('preserve settings')
    settings.unlink()
    settings.symlink_to(external_settings)
    refuses(lambda: module.register_template(vault))
    assert external_settings.read_text() == 'preserve settings'
print('PASS: directory symlink, immediate source edits/new files, idempotence, settings preservation, migration backup, unsafe parent/target refusal')
