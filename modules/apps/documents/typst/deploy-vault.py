"""Link the adapter directory into a vault; no copying or background refresh."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import stat


@contextmanager
def vault_directory(vault, parts, create=False):
    """Anchor writes to real vault directories, refusing redirected parents."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(vault, flags)
    try:
        for name in parts:
            if create:
                try:
                    os.mkdir(name, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(name, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def register_template(vault):
    with vault_directory(vault, ('.obsidian', 'plugins', 'omd-to-typst')) as directory:
        descriptor = os.open('data.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        with os.fdopen(descriptor) as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise RuntimeError('Plugin settings must be a regular file')
            settings = json.load(stream)
        entries = settings.setdefault('templates', [])
        entry = next((e for e in entries if e['name'] == 'phoenix-letter'), None)
        if entry is None:
            entry = {'name': 'phoenix-letter'}
            entries.append(entry)
        entry.update(path='3-misc/phoenix-typst/omd2typst/phoenix-letter.typ', languages=['de', 'en'])
        settings.update(defaultOutputFormat='pdf', outputMode='same-folder')
        temporary = 'data.json.phoenix-' + secrets.token_hex(8)
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(json.dumps(settings, ensure_ascii=False, indent=2) + '\n')
            os.replace(temporary, 'data.json', src_dir_fd=directory, dst_dir_fd=directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass


def deploy(source, vault, register=False, migrate_copies=False):
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise RuntimeError(f'Adapter source unavailable: {source}')
    # Only the adapter leaf is a link. No adapter contents are written via it.
    with vault_directory(vault, ('3-misc', 'phoenix-typst'), create=True) as parent:
        name, backup = 'omd2typst', '.omd2typst.before-symlink'
        try:
            existing = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and stat.S_ISLNK(existing.st_mode):
            if os.readlink(name, dir_fd=parent) != str(source):
                raise RuntimeError('Adapter link points elsewhere; refusing to replace it')
        elif existing is not None:
            if not migrate_copies or not stat.S_ISDIR(existing.st_mode):
                raise RuntimeError('Existing adapter directory requires --migrate-copies; it will be preserved as .omd2typst.before-symlink')
            # mkdir reserves the backup name without replacing any existing entry.
            os.mkdir(backup, dir_fd=parent)
            os.rename(name, backup, src_dir_fd=parent, dst_dir_fd=parent)
            try:
                os.symlink(str(source), name, dir_fd=parent)
            except OSError:
                os.rename(backup, name, src_dir_fd=parent, dst_dir_fd=parent)
                raise
        else:
            os.symlink(str(source), name, dir_fd=parent)
    if register:
        register_template(vault)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--register', action='store_true', help='Register plugin settings once; reload Omd2Typst afterwards')
    parser.add_argument('--migrate-copies', action='store_true', help='Preserve the existing adapter directory as .omd2typst.before-symlink')
    parser.add_argument('vault', type=Path)
    args = parser.parse_args()
    deploy(args.source, args.vault.resolve(strict=True), args.register, args.migrate_copies)


if __name__ == '__main__':
    main()
