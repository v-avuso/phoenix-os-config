"""Codec decisions plus real FFmpeg fixtures (when FFmpeg is on PATH)."""
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location("media_cli", Path(__file__).resolve().parents[1] / "media-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class AudioBitrateTests(unittest.TestCase):
    def test_only_reliable_per_stream_bitrate_caps_configured_default(self):
        self.assertEqual(96, cli.audio_bitrate({"bit_rate": "96000"}, 160))
        self.assertEqual(160, cli.audio_bitrate({"bit_rate": "256000"}, 160))
        self.assertEqual(80, cli.audio_bitrate({"bit_rate": "96000"}, 80))
        for value in (None, "N/A", 0, -1, "nan", "inf"):
            self.assertEqual(160, cli.audio_bitrate({"bit_rate": value, "abr": 64}, 160))

    def test_packet_timestamps_avoid_accumulated_rounded_duration_error(self):
        packets = "".join(f"stream_index=0|size=100|pts_time={i * 1024 / 48000:.6f}|duration_time=0.021\n"
                          for i in range(1000))
        process = Mock(stdout=io.StringIO(packets))
        process.wait.return_value = 0
        process.poll.return_value = 0
        stream = {"index": 0, "codec_name": "aac"}
        with patch.object(cli.subprocess, "Popen", return_value=process):
            cli.measure_audio_bitrates(Path("fixture.mkv"), [stream])
        self.assertAlmostEqual(37500, stream["bit_rate"], delta=10)

    def test_empty_packet_probe_uses_configured_default(self):
        process = Mock(stdout=io.StringIO(""))
        process.wait.return_value = 0
        process.poll.return_value = 0
        stream = {"index": 0, "codec_name": "aac"}
        with patch.object(cli.subprocess, "Popen", return_value=process):
            cli.measure_audio_bitrates(Path("fixture.mkv"), [stream])
        self.assertEqual(160, cli.audio_bitrate(stream, 160))


class QualitySearchTests(unittest.TestCase):
    def test_upstream_nvenc_search_is_used_and_result_is_read(self):
        result = subprocess.CompletedProcess([], 0, "crf 36 VMAF 96.13 predicted video stream size 73 MiB (33%) taking 36 seconds\n", "")
        with patch.object(cli, "ab_av1_command", return_value=result) as command:
            quality = cli.select_video_quality(Path("clip.mkv"), {"pix_fmt": "yuv420p"}, True, lambda line: None)
        self.assertEqual(36, quality)
        args = command.call_args.args[0]
        self.assertIn("av1_nvenc", args)
        self.assertIn("rc=vbr", args)
        self.assertEqual("96", args[args.index("--min-vmaf") + 1])
        self.assertEqual("100", args[args.index("--max-encoded-percent") + 1])
        self.assertNotIn("--crf", args)

    def test_infeasible_or_invalid_search_fails_without_fixed_quality_fallback(self):
        for result in (subprocess.CompletedProcess([], 1, "", "Failed to find a suitable crf"),
                       subprocess.CompletedProcess([], 0, "invalid summary", ""),
                       subprocess.CompletedProcess([], 0, "crf 45 VMAF 91.0 predicted size", "")):
            with self.subTest(result=result), patch.object(cli, "ab_av1_command", return_value=result):
                with self.assertRaises(RuntimeError):
                    cli.select_video_quality(Path("clip.mkv"), {}, True, lambda line: None)

    def test_failed_optimizer_cleans_its_sample_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mkv"
            def fail(args):
                temporary = Path(args[args.index("--temp-dir") + 1])
                (temporary / "partial.mkv").write_bytes(b"partial")
                return subprocess.CompletedProcess(args, 1, "", "unexpected optimizer failure")
            with patch.object(cli, "ab_av1_command", side_effect=fail):
                with self.assertRaises(cli.OptimizationUnavailable):
                    cli.select_video_quality(source, {}, True, lambda line: None)
            self.assertFalse(list(Path(directory).iterdir()))

    def test_completed_size_and_quality_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mkv"; source.write_bytes(b"s" * 1000)
            output = Path(directory) / "output.webm"; output.write_bytes(b"o" * 1001)
            with patch.object(cli, "ab_av1_command") as command:
                with self.assertRaisesRegex(RuntimeError, "size limit"):
                    cli.validate_video_budget(output, source, lambda line: None)
                command.assert_not_called()
            output.write_bytes(b"o" * 500)
            for score, accepted in (("94.9", False), ("nan", False), ("95.2", True)):
                with patch.object(cli, "ab_av1_command", return_value=subprocess.CompletedProcess([], 0, score, "")):
                    if accepted:
                        cli.validate_video_budget(output, source, lambda line: None)
                    else:
                        with self.assertRaisesRegex(cli.OptimizationUnavailable, "not published"):
                            cli.validate_video_budget(output, source, lambda line: None)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg runtime required")
class CodecRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # These fixtures exercise codec conversion/cleanup independently of search.
        quality = patch.object(cli, "select_video_quality", return_value=24)
        budget = patch.object(cli, "validate_video_budget")
        quality.start(); budget.start()
        self.addCleanup(quality.stop); self.addCleanup(budget.stop)

    def source(self, video="libx264", audio="aac", ext="mkv"):
        path = self.root / f"input.{ext}"
        args = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=24",
                "-f", "lavfi", "-i", "sine=r=48000", "-t", "2", "-c:v", video,
                "-c:a", audio, "-b:a", "96k", "-metadata", "title=Fixture", "-y", str(path)]
        if video == "libsvtav1":
            args[-2:-2] = ["-preset", "10", "-svtav1-params", "lp=2"]
        subprocess.run(args, check=True, capture_output=True)
        return path

    def packets(self, path, kind):
        result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", kind,
                                 "-show_packets", "-show_data_hash", "sha256", "-of", "json", str(path)],
                                check=True, capture_output=True, text=True)
        return [p["data_hash"] for p in json.loads(result.stdout)["packets"]]

    def convert(self, source, mode="video"):
        return cli.enforce_codecs(source, mode, prefer_gpu=False, emit=lambda event: None)

    def test_av1_opus_packets_are_copied_to_webm(self):
        source = self.source("libsvtav1", "libopus")
        before = [self.packets(source, kind) for kind in ("v", "a")]
        output = self.convert(source)
        self.assertEqual(".webm", output.suffix)
        self.assertEqual(before, [self.packets(output, kind) for kind in ("v", "a")])
        self.assertEqual("Fixture", cli.probe_media(output)["format"]["tags"]["title"])

    def test_h264_aac_becomes_av1_opus_preserving_geometry_and_timing(self):
        source = self.source(ext="mp4")
        output = self.convert(source)
        streams = cli.probe_media(output)["streams"]
        self.assertEqual(["av1", "opus"], [s["codec_name"] for s in streams])
        self.assertEqual((320, 240, "24/1"), (streams[0]["width"], streams[0]["height"], streams[0]["avg_frame_rate"]))

    def test_mixed_codecs_only_convert_incompatible_stream(self):
        for video, audio, copied in (("libsvtav1", "aac", "v"), ("libx264", "libopus", "a")):
            with self.subTest(video=video, audio=audio):
                source = self.source(video, audio)
                expected = self.packets(source, copied)
                output = self.convert(source)
                self.assertEqual(expected, self.packets(output, copied))
                output.unlink()

    def test_merged_audio_recovers_exact_rate_without_container_bitrate(self):
        source = self.source()
        stream = [s for s in cli.probe_media(source)["streams"] if s["codec_type"] == "audio"][0]
        stream.pop("bit_rate", None)
        cli.measure_audio_bitrates(source, [stream])
        self.assertGreater(stream["bit_rate"], 80000)
        self.assertLess(stream["bit_rate"], 110000)
        self.assertLess(cli.audio_bitrate(stream, 160), 110)

    def test_audio_copy_and_source_bitrate_policy_use_same_path(self):
        source = self.source("libx264", "libopus")
        packets = self.packets(source, "a")
        output = self.convert(source, "audio")
        self.assertEqual(packets, self.packets(output, "a"))
        self.assertEqual(["opus"], [s["codec_name"] for s in cli.probe_media(output)["streams"]])

    def test_original_is_byte_identical(self):
        source = self.source(ext="mp4")
        before = source.read_bytes()
        self.assertEqual(source, cli.enforce_codecs(source, "video", original=True))
        self.assertEqual(before, source.read_bytes())

    def test_failed_validation_does_not_publish_or_damage_source(self):
        source = self.source(ext="mp4")
        before = source.read_bytes()
        with patch.object(cli, "validate_media", side_effect=RuntimeError("failed playback")):
            with self.assertRaisesRegex(RuntimeError, "failed playback"):
                self.convert(source)
        self.assertEqual(before, source.read_bytes())
        self.assertFalse(source.with_suffix(".webm").exists())
        self.assertFalse(list(self.root.glob(".phoenix-codecs-*")))

    def test_failed_quality_gate_preserves_source_and_cleans_output(self):
        source = self.source(ext="mp4")
        before = source.read_bytes()
        with patch.object(cli, "validate_video_budget", side_effect=RuntimeError("below quality floor")):
            with self.assertRaisesRegex(RuntimeError, "below quality floor"):
                self.convert(source)
        self.assertEqual(before, source.read_bytes())
        self.assertFalse(source.with_suffix(".webm").exists())
        self.assertFalse(list(self.root.glob(".phoenix-codecs-*")))

    def test_search_failure_keeps_valid_source_without_encoding(self):
        for reason in ("quality/size constraints were not met", "optimizer crashed"):
            with self.subTest(reason=reason):
                source = self.source(ext="mp4")
                before = source.read_bytes()
                with patch.object(cli, "select_video_quality", side_effect=cli.OptimizationUnavailable(reason)):
                    output = self.convert(source)
                self.assertEqual(source, output)
                self.assertEqual(before, source.read_bytes())
                self.assertFalse(source.with_suffix(".webm").exists())
                self.assertFalse(list(self.root.glob(".phoenix-codecs-*")))

    def test_size_or_vmaf_rejection_keeps_source_and_removes_candidate(self):
        source = self.source(ext="mp4")
        before = source.read_bytes()
        with patch.object(cli, "validate_video_budget", side_effect=cli.OptimizationUnavailable("below quality floor")):
            output = self.convert(source)
        self.assertEqual(source, output)
        self.assertEqual(before, source.read_bytes())
        self.assertFalse(source.with_suffix(".webm").exists())
        self.assertFalse(list(self.root.glob(".phoenix-codecs-*")))

    def test_fallback_corrects_non_webm_codecs_labelled_webm(self):
        source = self.source()  # Matroska with H.264/AAC
        source = source.rename(source.with_suffix(".webm"))
        before = source.read_bytes()
        with patch.object(cli, "select_video_quality", side_effect=cli.OptimizationUnavailable("no candidate")):
            output = self.convert(source)
        self.assertEqual(".mkv", output.suffix)
        self.assertEqual(before, output.read_bytes())
        self.assertFalse(source.exists())

    def test_corrupt_source_fails_instead_of_optimizer_fallback(self):
        source = self.root / "broken.mp4"
        source.write_bytes(b"not a media file")
        with patch.object(cli, "select_video_quality") as search:
            with self.assertRaises(cli.MediaIntegrityError):
                self.convert(source)
            search.assert_not_called()
        self.assertFalse(source.with_suffix(".webm").exists())

    def test_unavailable_nvenc_uses_software(self):
        source = self.source(ext="mp4")
        with patch.object(cli, "nvenc_available", return_value=False):
            output = cli.enforce_codecs(source, "video", emit=lambda event: None)
        self.assertEqual("av1", cli.probe_media(output)["streams"][0]["codec_name"])


if __name__ == "__main__":
    unittest.main()
