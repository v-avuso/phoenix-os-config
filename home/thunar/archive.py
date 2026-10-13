#!/usr/bin/env python3
"""Create a moderate-compression ZIP beside selected Thunar items."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path


def archive_path(items: list[Path], destination_dir: Path, index: int) -> Path:
    stem = items[0].stem if len(items) == 1 else "Archive"
    suffix = "" if index == 1 else f".{index}"
    return destination_dir / f"{stem}{suffix}.zip"


def add_path(archive: zipfile.ZipFile, path: Path, root: Path, excluded: str) -> None:
    """Write regular files, directories and links without following links."""
    if os.path.abspath(path) == excluded:
        return
    info = path.lstat()
    arcname = path.relative_to(root).as_posix()
    if stat.S_ISLNK(info.st_mode):
        link = zipfile.ZipInfo(arcname)
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, os.fsencode(os.readlink(path)))
    elif stat.S_ISDIR(info.st_mode):
        archive.write(path, arcname)
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            add_path(archive, child, root, excluded)
    elif stat.S_ISREG(info.st_mode):
        archive.write(path, arcname)
    else:
        raise ValueError(f"{path}: unsupported special file (only files, directories and links are supported)")


def create_archive(raw_paths: list[str]) -> tuple[bool, str]:
    items: list[Path] = []
    seen: set[str] = set()
    for raw in raw_paths:
        path = Path(os.path.abspath(os.path.expanduser(raw)))
        key = os.path.normcase(str(path))
        if key not in seen:
            items.append(path)
            seen.add(key)
    if not items:
        return False, "No files selected"
    if any(not os.path.lexists(path) for path in items):
        missing = next(path for path in items if not os.path.lexists(path))
        return False, f"{missing}: item does not exist"

    selected_directories = [path for path in items if stat.S_ISDIR(path.lstat().st_mode)]
    items = [
        path for path in items
        if not any(path != directory and path.is_relative_to(directory) for directory in selected_directories)
    ]
    try:
        for path in items:
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
                return False, f"{path}: unsupported special file (only files, directories and links are supported)"
        destination_dir = Path(os.path.commonpath([str(path.parent) for path in items]))
    except (OSError, ValueError) as exc:
        return False, f"ZIP creation failed: {exc}"

    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=".phoenix-zip-", suffix=".zip", dir=destination_dir
        )
        os.close(fd)
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            strict_timestamps=False,
        ) as archive:
            for item in items:
                add_path(archive, item, destination_dir, os.path.abspath(temporary))

        index = 1
        while True:
            destination = archive_path(items, destination_dir, index)
            try:
                # Linking publishes atomically and refuses to replace any name.
                os.link(temporary, destination)
                return True, f"Created {destination}"
            except FileExistsError:
                index += 1
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return False, f"ZIP creation failed: {exc}"
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    success, message = create_archive(sys.argv[1:] if argv is None else argv)
    print(message, file=sys.stdout if success else sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
