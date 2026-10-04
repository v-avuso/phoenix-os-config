#!/usr/bin/env python3
"""Focused fixtures for convert-images.py; all images live in temporary dirs."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "home/thunar-image-convert.py"
spec = importlib.util.spec_from_file_location("convert_images", SCRIPT)
convert_images = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(convert_images)


class ConvertImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="phoenix-image-test-")
        self.root = Path(self.temp_dir.name)
        self.magick = "/nix/store/test-imagemagick/bin/magick"

    def tearDown(self):
        self.temp_dir.cleanup()

    def input(self, name: str, data: bytes = b"original image bytes") -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    @staticmethod
    def fake_success(command, stdin, **kwargs):
        source_bytes = stdin.read()
        assert command[0] == "/nix/store/test-imagemagick/bin/magick"
        assert command[-1].endswith((".jpg", ".png", ".webp", ".jxl"))
        assert "-" in command
        assert str(stdin.name) not in command
        Path(command[-1]).write_bytes(b"converted:" + source_bytes)
        return subprocess.CompletedProcess(command, 0, "", "")

    def test_batch_preserves_originals_and_handles_literal_filename_syntax(self):
        weird = self.input("-frame[0]:literal image.png", b"first")
        other = self.input("http:literal:colon.png", b"second")
        calls = []

        def run(command, stdin, **kwargs):
            calls.append((list(command), Path(stdin.name), stdin.read()))
            Path(command[-1]).write_bytes(b"converted:" + calls[-1][2])
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(convert_images.subprocess, "run", side_effect=run):
            status = convert_images.main(["--magick", self.magick, "webp", str(weird), str(other)])

        self.assertEqual(status, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn(str(weird), calls[0][0])
        self.assertNotIn(str(other), calls[1][0])
        self.assertTrue(Path(calls[0][0][-1]).name.startswith(".phoenix-convert-"))
        self.assertTrue(Path(calls[1][0][-1]).name.startswith(".phoenix-convert-"))
        self.assertEqual(weird.read_bytes(), b"first")
        self.assertEqual(other.read_bytes(), b"second")
        self.assertEqual((self.root / "-frame[0]:literal image.converted.webp").read_bytes(), b"converted:first")
        self.assertEqual((self.root / "http:literal:colon.converted.webp").read_bytes(), b"converted:second")

    def test_existing_file_and_symlink_collisions_get_indexed_without_replacement(self):
        source = self.input("sample.png")
        first = self.input("sample.converted.jpg", b"keep existing file")
        symlink = self.root / "sample.converted.2.jpg"
        symlink.symlink_to(first.name)

        with patch.object(convert_images.subprocess, "run", side_effect=self.fake_success):
            status = convert_images.main(["--magick", self.magick, "jpeg", str(source)])

        self.assertEqual(status, 0)
        self.assertEqual(first.read_bytes(), b"keep existing file")
        self.assertTrue(symlink.is_symlink())
        self.assertEqual((self.root / "sample.converted.3.jpg").read_bytes(), b"converted:original image bytes")
        self.assertEqual(source.read_bytes(), b"original image bytes")

    def test_failure_cleans_partial_temp_and_returns_error(self):
        source = self.input("broken.png")
        before = set(self.root.iterdir())

        def fail_after_partial(command, stdin, **kwargs):
            Path(command[-1]).write_bytes(b"partial")
            raise subprocess.CalledProcessError(1, command, stderr="encoder failed")

        with patch.object(convert_images.subprocess, "run", side_effect=fail_after_partial):
            status = convert_images.main(["--magick", self.magick, "jxl", str(source)])

        self.assertEqual(status, 1)
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertEqual(source.read_bytes(), b"original image bytes")

    def test_already_target_and_duplicate_inputs_are_skipped(self):
        jpeg = self.input("already.JPEG")
        png = self.input("convert-me.png")
        run = patch.object(convert_images.subprocess, "run", side_effect=self.fake_success)
        with run as process:
            status = convert_images.main(["--magick", self.magick, "jpeg", str(jpeg), str(png), str(png)])

        self.assertEqual(status, 0)
        self.assertEqual(process.call_count, 1)
        self.assertTrue((self.root / "convert-me.converted.jpg").exists())

    def test_format_defaults_are_lossless_for_png_and_jxl(self):
        self.assertEqual(convert_images.output_options("png"), [])
        self.assertEqual(convert_images.output_options("jxl"), ["-quality", "100"])
        self.assertIn("-quality", convert_images.output_options("jpeg"))
        self.assertIn("-alpha", convert_images.output_options("jpeg"))
        self.assertIn("-quality", convert_images.output_options("webp"))

    def test_arguments_accept_leading_dash_paths_and_require_absolute_tool(self):
        fmt, files, executable = convert_images.parse_args(["jpeg", "-strange:input.png"])
        self.assertEqual((fmt, files, executable), ("jpeg", ["-strange:input.png"], convert_images.DEFAULT_MAGICK))
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            convert_images.parse_args(["--magick", "magick", "png", "image.jpg"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
