"""Deploy only the Phoenix-owned adapter directory; never reconcile a vault."""
import argparse
import json
import os
from pathlib import Path


def write_changed(path, data):
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.phoenix-tmp')
    temporary.write_bytes(data)
    os.replace(temporary, path)


def deploy(source, vault, register=False):
    if not source.is_dir():
        raise RuntimeError(f'Adapter source unavailable: {source}')
    target = vault / '3-misc/phoenix-typst/omd2typst'
    if target.is_symlink():
        raise RuntimeError(f'Refusing to overwrite symlink: {target}')
    for item in source.glob('*.typ'):
        destination = target / item.name
        if destination.is_symlink():
            raise RuntimeError(f'Refusing to overwrite symlink: {destination}')
        write_changed(destination, item.read_bytes())
    if register:
        settings_file = vault / '.obsidian/plugins/omd-to-typst/data.json'
        settings = json.loads(settings_file.read_text())
        path = (target / 'phoenix-letter.typ').relative_to(vault).as_posix()
        entries = settings.setdefault('templates', [])
        entry = next((e for e in entries if e['name'] == 'phoenix-letter'), None)
        if entry is None:
            entry = {'name': 'phoenix-letter'}
            entries.append(entry)
        entry.update(path=path, languages=['de', 'en'])
        settings.update(defaultOutputFormat='pdf', outputMode='same-folder')
        write_changed(settings_file, (json.dumps(settings, ensure_ascii=False, indent=2)+'\n').encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--register', action='store_true', help='Register template/settings once; reload Omd2Typst afterwards')
    parser.add_argument('vault', type=Path, nargs='?')
    args = parser.parse_args()
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state'))) / 'phoenix-typst/vaults.json'
    vaults = json.loads(state.read_text()) if state.exists() else []
    if args.vault:
        vault = str(args.vault.resolve())
        state.parent.mkdir(parents=True, exist_ok=True)
        deploy(args.source, Path(vault), args.register)
        if vault not in vaults:
            vaults.append(vault)
            write_changed(state, (json.dumps(vaults)+'\n').encode())
    else:
        for vault in vaults:
            if Path(vault).is_dir():
                deploy(args.source, Path(vault))


if __name__ == '__main__':
    main()
