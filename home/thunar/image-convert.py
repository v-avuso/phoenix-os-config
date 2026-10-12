#!/usr/bin/env python3
"""Convert images without replacing sources or existing destination files."""

from __future__ import annotations

import os
import subprocess
import stat
import sys
import tempfile
from pathlib import Path

# A Thunar action should pass its pinned Nix-store executable with --magick.
# This absolute fallback keeps direct invocation independent of PATH lookup.
DEFAULT_MAGICK = "/run/current-system/sw/bin/magick"

FORMATS = {
    "jpeg": {"extension": "jpg", "source_extensions": {".jpg", ".jpeg", ".jpe"}},
    "png": {"extension": "png", "source_extensions": {".png"}},
    "webp": {"extension": "webp", "source_extensions": {".webp"}},
    "jxl": {"extension": "jxl", "source_extensions": {".jxl"}},
}


def output_options(image_format: str) -> list[str]:
    if image_format == "jpeg":
        # JPEG cannot carry alpha; composite transparency onto white.
        return ["-background", "white", "-alpha", "remove", "-alpha", "off", "-quality", "88"]
    if image_format == "webp":
        return ["-quality", "82"]
    if image_format == "jxl":
        # Quality 100 is the ImageMagick JPEG XL lossless mode.
        return ["-quality", "100"]
    return []


def absolute_input(value: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(value)))


def candidate_path(source: Path, extension: str, index: int) -> Path:
    suffix = ".converted" if index == 1 else f".converted.{index}"
    return source.with_name(f"{source.stem}{suffix}.{extension}")


def convert_one(
    image_format: str,
    source: Path,
    magick: str,
    seen_inputs: set[str],
) -> tuple[str, str]:
    spec = FORMATS[image_format]
    source_key = os.path.normcase(str(source))
    if source_key in seen_inputs:
        return "skip", f"{source}: repeated input"
    seen_inputs.add(source_key)

    if source.suffix.lower() in spec["source_extensions"]:
        return "skip", f"{source}: already {image_format}"
    if not source.is_file():
        return "error", f"{source}: not a regular file"

    temporary: str | None = None
    try:
        # Put the temporary beside the source so os.link publishes atomically
        # on the same filesystem and cannot replace an existing name.
        fd, temporary = tempfile.mkstemp(
            prefix=".phoenix-convert-",
            suffix=f".{spec['extension']}",
            dir=source.parent,
        )
        os.close(fd)

        with source.open("rb") as input_stream:
            command = [
                magick,
                "-define",
                "image:frames=0",
                "-",
                "-auto-orient",
                *output_options(image_format),
                temporary,
            ]
            subprocess.run(
                command,
                stdin=input_stream,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )

        if not os.path.isfile(temporary) or os.path.getsize(temporary) == 0:
            return "error", f"{source}: converter produced no image data"

        # A mkstemp file starts private (0600); carry the source's ordinary
        # read/write permissions to the published image.
        os.chmod(temporary, stat.S_IMODE(source.stat().st_mode) & 0o666)

        index = 1
        while True:
            destination = candidate_path(source, spec["extension"], index)
            try:
                # link() is atomic and fails for existing files and symlinks.
                os.link(temporary, destination)
                return "ok", f"{source} -> {destination}"
            except FileExistsError:
                index += 1
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None)
        detail = detail.strip() if isinstance(detail, str) else ""
        message = f"{source}: conversion failed: {detail or exc}"
        return "error", message
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def parse_args(argv: list[str]) -> tuple[str, list[str], str]:
    magick = DEFAULT_MAGICK
    args = list(argv)
    if args and args[0] == "--magick":
        if len(args) < 3:
            raise ValueError("--magick requires an absolute executable path")
        magick = args[1]
        args = args[2:]
    elif args and args[0].startswith("--magick="):
        magick = args[0].partition("=")[2]
        args = args[1:]
    if not os.path.isabs(magick):
        raise ValueError("ImageMagick path must be absolute")
    if len(args) < 2:
        raise ValueError("usage: convert-images.py [--magick ABSOLUTE_PATH] FORMAT FILE...")
    image_format, *files = args
    if image_format not in FORMATS:
        raise ValueError(f"unsupported format {image_format!r}; choose jpeg, png, webp, or jxl")
    return image_format, files, magick


def main(argv: list[str] | None = None) -> int:
    try:
        image_format, files, magick = parse_args(sys.argv[1:] if argv is None else argv)
    except ValueError as exc:
        print(f"convert-images.py: {exc}", file=sys.stderr)
        return 2

    seen_inputs: set[str] = set()
    failures = 0
    for raw_path in files:
        status, message = convert_one(image_format, absolute_input(raw_path), magick, seen_inputs)
        print(message)
        failures += status == "error"
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
