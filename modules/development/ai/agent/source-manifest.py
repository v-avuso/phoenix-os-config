"""Frozen text-source manifests. Symlink values are targets, never target contents.

Only direct relative links to regular manifest entries are supported. Directory
links and link chains stay unsupported, keeping reconstruction and review simple.
Mutable source reads use directory descriptors and never follow source symlinks.
"""
import os
from pathlib import Path, PurePosixPath
import stat

REGULAR = {'100644', '100755'}


def source_name(name):
    if (not isinstance(name, str) or not name or any(c in name for c in '\n\r\0') or
            name.startswith('/') or any(p in {'', '.', '..', '.git'} for p in name.split('/'))):
        raise ValueError('unsafe source name')
    return PurePosixPath(name)


def validate(files, modes, *, tracked=None):
    if not isinstance(files, dict) or not isinstance(modes, dict) or files.keys() != modes.keys():
        raise ValueError('invalid source manifest')
    directories = set()
    for name, content in files.items():
        path = source_name(name)
        if not isinstance(content, str) or modes[name] not in REGULAR | {'120000'}:
            raise ValueError('unsupported source type')
        directories.update(str(parent) for parent in path.parents if str(parent) != '.')
    if directories & files.keys():
        raise ValueError('file/directory prefix collision')
    for name in ('flake.nix', 'flake.lock'):
        if name in files and modes[name] not in REGULAR:
            raise ValueError('flake files must be regular source files')
    for name, target in files.items():
        if modes[name] != '120000':
            continue
        if not target or target.startswith('/') or any(ord(c) < 32 or ord(c) == 127 for c in target):
            raise ValueError('unsafe source symlink target')
        parts = name.split('/')[:-1]
        components = target.split('/')
        for index, part in enumerate(components):
            if part in {'', '.', '.git'}:
                raise ValueError('unsafe source symlink target')
            if part == '..':
                if not parts:
                    raise ValueError('source symlink escapes snapshot')
                parts.pop()
            else:
                parts.append(part)
            if index < len(components) - 1 and '/'.join(parts) not in directories | {''}:
                raise ValueError('source symlink traverses a non-directory')
        resolved = '/'.join(parts)
        if modes.get(resolved) not in REGULAR:
            raise ValueError('source symlink must target a regular manifest file (no dangling, directory or cyclic links)')
        if tracked is not None and resolved not in tracked:
            raise ValueError('source symlink target must be tracked')


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def _read_entry(parent_fd, name, limit):
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode):
        data = os.readlink(name, dir_fd=parent_fd).encode('utf-8')
        mode = '120000'
        after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    else:
        # NONBLOCK avoids hanging if a mutable regular file is replaced by a FIFO.
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent_fd)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError('unsupported source file')
            if _identity(before) != _identity(opened):
                raise ValueError('working-tree source changed during snapshot; retry deployment')
            data = bytearray()
            while len(data) <= limit:
                block = os.read(fd, min(65536, limit + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
            data = bytes(data)
            mode = '100755' if opened.st_mode & 0o111 else '100644'
            after = os.fstat(fd)
        finally:
            os.close(fd)
    if _identity(before) != _identity(after):
        raise ValueError('working-tree source changed during snapshot; retry deployment')
    if len(data) > limit:
        raise ValueError('source exceeds transport capacity; reduce source scope before deployment')
    return data, mode


def read_entry(root, name, limit):
    parts = source_name(name).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        return _read_entry(fd, parts[-1], limit)
    except FileNotFoundError:
        return None
    finally:
        os.close(fd)


def read_tree(root, limit):
    files, modes, total = {}, {}, 0
    def walk(fd, prefix=''):
        nonlocal total
        for name in sorted(os.listdir(fd)):
            relative = prefix + name
            source_name(relative)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                try:
                    walk(child, relative + '/')
                finally:
                    os.close(child)
            else:
                raw, modes[relative] = _read_entry(fd, name, limit - total)
                total += len(raw)
                files[relative] = raw.decode('utf-8')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        walk(fd)
    finally:
        os.close(fd)
    validate(files, modes)
    return files, modes


def materialize(root, files, modes):
    """Write only to a private, empty destination after validating the whole graph."""
    validate(files, modes)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or any(root.iterdir()):
        raise ValueError('source destination must be a private empty directory')
    # The controller's umask is 0077; its isolated builder still needs traversal.
    root.chmod(0o755)
    directories = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != '.'}
    for name in sorted(directories, key=lambda name: (name.count('/'), name)):
        directory = root / name
        directory.mkdir(mode=0o755)
        directory.chmod(0o755)
    for name, content in files.items():
        if modes[name] == '120000':
            continue
        path = root / name
        path.write_bytes(content.encode('utf-8'))
        path.chmod(0o755 if modes[name] == '100755' else 0o644)
    for name, target in files.items():
        if modes[name] == '120000':
            path = root / name
            path.symlink_to(target)
