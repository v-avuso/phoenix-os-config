#!/usr/bin/env python3
"""Generated-file integration checks against the pinned ImageMagick binary."""

import os
import sys
import importlib.util
import subprocess
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("convert_images", Path(__file__).resolve().parents[1] / "home/thunar-image-convert.py")
convert_images = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(convert_images)

MAGICK = sys.argv[1]


def ppm(rgb: tuple[int, int, int], size: int = 2) -> bytes:
    return f"P6\n{size} {size}\n255\n".encode() + bytes(rgb) * size * size


def decoded_rgb(path: Path) -> bytes:
    return subprocess.run(
        [MAGICK, str(path), "-depth", "8", "rgb:-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def main() -> None:
    assert os.path.isfile(MAGICK), f"missing pinned executable: {MAGICK}"
    with tempfile.TemporaryDirectory(prefix="phoenix-image-real-") as temp_dir:
        root = Path(temp_dir)
        red = ppm((255, 0, 0))
        blue = ppm((0, 0, 255))

        # The weird basename is never passed to ImageMagick: only the opened
        # file descriptor reaches the converter.
        odd = root / "-sample[0]:literal.ppm"
        odd.write_bytes(red)
        status, message = convert_images.convert_one("webp", odd, MAGICK, set())
        assert status == "ok", message
        odd_output = root / "-sample[0]:literal.converted.webp"
        assert odd_output.is_file()
        assert decoded_rgb(odd_output) == red[len(b"P6\n2 2\n255\n"):]
        assert {p.name for p in root.iterdir()} == {odd.name, odd_output.name}

        # Construct an actual two-frame GIF from generated PPMs and assert the
        # converted PNG equals the decoded first frame with no numbered files.
        frame0 = root / "frame-zero.ppm"
        frame1 = root / "frame-one.ppm"
        frame0.write_bytes(red)
        frame1.write_bytes(blue)
        animated = root / "animated.gif"
        subprocess.run([MAGICK, str(frame0), str(frame1), str(animated)], check=True)
        count = subprocess.run(
            [MAGICK, "identify", "-format", "%n", str(animated)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        assert count == "22", f"expected two-frame fixture; identify returned {count!r}"
        status, message = convert_images.convert_one("png", animated, MAGICK, set())
        assert status == "ok", message
        animated_output = root / "animated.converted.png"
        assert decoded_rgb(animated_output) == decoded_rgb(frame0)
        assert not list(root.glob("animated.converted-*.png"))
        assert not list(root.glob("animated.converted.[0-9]*.png"))
        assert not list(root.glob(".phoenix-convert-*"))

        # JPEG XL quality 100 must decode to exactly the original sample pixels.
        # Varied RGBA pixels expose accidental lossy modes and alpha loss.
        jxl_source = root / "lossless-source.pam"
        pixels = bytes((i * 37 + 19) % 256 for i in range(16 * 16 * 4))
        jxl_source.write_bytes(b"P7\nWIDTH 16\nHEIGHT 16\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n" + pixels)
        original_pixels = subprocess.check_output([MAGICK, str(jxl_source), "-depth", "8", "rgba:-"])
        status, message = convert_images.convert_one("jxl", jxl_source, MAGICK, set())
        assert status == "ok", message
        jxl_output = root / "lossless-source.converted.jxl"
        assert subprocess.check_output([MAGICK, str(jxl_output), "-depth", "8", "rgba:-"]) == original_pixels

        # Invalid image bytes must fail and leave neither a result nor a temp.
        invalid = root / "invalid.ppm"
        invalid.write_bytes(b"not an image")
        before = set(root.iterdir())
        status, message = convert_images.convert_one("png", invalid, MAGICK, set())
        assert status == "error", message
        assert set(root.iterdir()) == before
        assert not list(root.glob(".phoenix-convert-*"))

        print("PASS: literal filename conversion, first-frame PNG, JXL pixel roundtrip, failed-temp cleanup")


if __name__ == "__main__":
    main()
