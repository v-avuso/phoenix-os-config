"""Real yt-dlp/FFmpeg pipeline: final tags/artwork must precede safe publication."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
YT_DLP = os.environ.get("PHOENIX_YT_DLP_BIN", shutil.which("yt-dlp"))
try:
    from mutagen.oggopus import OggOpus
    from mutagen.flac import Picture
except ImportError:
    OggOpus = None


@unittest.skipUnless(YT_DLP and shutil.which("ffmpeg") and OggOpus,
                     "yt-dlp, FFmpeg and Mutagen runtime required")
class AudioPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inbox = self.root / "music/_unsorted"
        self.inbox.mkdir(parents=True)
        self.env = dict(os.environ, XDG_CACHE_HOME=str(self.root / "cache"),
                        XDG_STATE_HOME=str(self.root / "state"), PHOENIX_YT_DLP_BIN=YT_DLP,
                        PHOENIX_MEDIA_PYTHON=sys.executable,
                        PHOENIX_MEDIA_CLI_HELPER=str(ROOT / "media-cli.py"),
                        PHOENIX_MEDIA_FFMPEG_DIRECTORY=str(Path(shutil.which("ffmpeg")).parent))
        hook = self.root / "ingest"
        hook.write_text(f'''#!{sys.executable}
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("ingest", {str(ROOT / 'media-ingest.py')!r})
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
sys.exit(module.process_file(Path({str(self.inbox)!r}), Path(sys.argv[1]),
    music_root=Path({str(self.root / 'music')!r}), state_directory=Path({str(self.root / 'state')!r}),
    client_key=""))
''')
        hook.chmod(0o755)
        self.env["PHOENIX_MEDIA_INGEST_COMMAND"] = str(hook)
        self.art = self.root / "cover.jpg"
        self.ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=64x64", "-frames:v", "1", str(self.art))

    def ffmpeg(self, *args):
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True)

    def packets(self, path):
        data = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a",
            "-show_packets", "-show_data_hash", "sha256", "-show_entries", "packet=data_hash",
            "-of", "json", str(path)], text=True)
        return [p["data_hash"] for p in json.loads(data)["packets"]]

    def fixture(self, codec):
        source = self.root / ("source.mp4" if codec == "aac" else "source.opus")
        self.ffmpeg("-f", "lavfi", "-i", "sine=r=48000", "-t", "2", "-c:a", codec,
                    "-b:a", "96k", str(source))
        if codec == "libopus":
            # Existing cover art is exposed as an attached video by FFmpeg too.
            audio = OggOpus(source)
            picture = Picture(); picture.mime = "image/jpeg"; picture.type = 3
            picture.data = self.art.read_bytes()
            audio["metadata_block_picture"] = [base64.b64encode(picture.write()).decode("ascii")]
            audio.save()
        info = self.root / "source.json"
        info.write_text(json.dumps({"id": "fixture", "title": "Fixture Track", "uploader": "Fixture Artist",
            "upload_date": "20261008", "webpage_url": source.as_uri(), "original_url": "https://example.test/fixture",
            "url": source.as_uri(), "ext": source.suffix[1:], "vcodec": "none", "acodec": codec,
            "thumbnails": [{"id": "cover", "url": self.art.as_uri(), "ext": "jpg", "width": 64, "height": 64}]}))
        return source, info

    def test_aac_and_existing_opus_keep_artwork_metadata_and_route_to_review(self):
        for codec in ("aac", "libopus"):
            with self.subTest(codec=codec):
                source, info = self.fixture(codec)
                before = self.packets(source)
                result = subprocess.run(["bash", str(ROOT / "download"), "music",
                    "--enable-file-urls", "--load-info-json", str(info), "-P", str(self.inbox)],
                    env=self.env, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                output = self.inbox / "_review/Fixture Artist - Fixture Track.opus"
                self.assertTrue(output.is_file(), result.stdout)
                tags = OggOpus(output).tags
                self.assertEqual(["Fixture Track"], tags["title"])
                self.assertEqual(["Fixture Artist"], tags["artist"])
                self.assertEqual(["2026"], tags["date"])
                self.assertEqual([source.as_uri()], tags["purl"])
                self.assertTrue(tags["metadata_block_picture"])
                self.assertIn("→ Review:", result.stdout)
                self.assertFalse(list(self.inbox.glob("*.opus")))
                self.assertFalse(list((self.root / "cache/phoenix-media").glob("audio.*")))
                self.ffmpeg("-xerror", "-i", str(output), "-map", "0:a", "-f", "null", "-")
                if codec == "libopus":
                    self.assertEqual(before, self.packets(output))
                output.unlink()
    def test_existing_opus_art_survives_without_a_new_thumbnail(self):
        source, info = self.fixture("libopus")
        picture = OggOpus(source)["metadata_block_picture"]
        before = self.packets(source)
        data = json.loads(info.read_text()); data.pop("thumbnails"); info.write_text(json.dumps(data))
        result = subprocess.run(["bash", str(ROOT / "download"), "music", "--enable-file-urls",
            "--load-info-json", str(info), "-P", str(self.inbox)], env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        output = self.inbox / "_review/Fixture Artist - Fixture Track.opus"
        self.assertEqual(picture, OggOpus(output)["metadata_block_picture"])
        self.assertEqual(before, self.packets(output))

    def test_corruption_after_artwork_is_never_published_or_ingested(self):
        _, info = self.fixture("aac")
        helper = self.root / "corrupt-helper.py"
        helper.write_text(f"""import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('real_cli', {str(ROOT / 'media-cli.py')!r})
real = importlib.util.module_from_spec(spec); spec.loader.exec_module(real)
globals().update({{key: value for key, value in vars(real).items() if not key.startswith('__')}})
def validate_media(path, mode, source, **kwargs):
    Path(path).write_bytes(b'corrupt after final metadata/artwork')
    return real.validate_media(path, mode, source, **kwargs)
if __name__ == '__main__':
    raise SystemExit(real.main())
""")
        # Override only the plugin's final validator; conversion uses real's globals.
        env = dict(self.env, PHOENIX_MEDIA_CLI_HELPER=str(helper))
        result = subprocess.run(["bash", str(ROOT / "download"), "music", "--enable-file-urls",
            "--load-info-json", str(info), "-P", str(self.inbox)], env=env, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(list(self.inbox.rglob("*.opus")))
        self.assertNotIn("✓ Downloaded:", result.stdout)

    def test_metadata_failure_never_publishes_or_claims_processing_success(self):
        _, info = self.fixture("aac")
        result = subprocess.run(["bash", str(ROOT / "download"), "music", "--enable-file-urls",
            "--load-info-json", str(info), "-P", str(self.inbox), "--postprocessor-args",
            "Metadata+ffmpeg_i:-f not_a_container"], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(list(self.inbox.rglob("*.opus")))
        self.assertNotIn("✓ Downloaded:", result.stdout)
        self.assertNotIn("Encoding (Opus)… finished", result.stdout)
        logs = list((self.root / "state/phoenix-media/downloads").glob("*.log"))
        self.assertTrue(any("Metadata processing failed" in log.read_text() for log in logs))


@unittest.skipUnless(YT_DLP and shutil.which("ffmpeg"), "yt-dlp and FFmpeg runtime required")
class VideoPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=24",
            "-f", "lavfi", "-i", "sine=r=48000", "-t", "2", "-c:v", "libx264", "-crf", "12", "-c:a", "aac",
            str(self.source)], check=True, capture_output=True)
        self.info = self.root / "source.json"
        self.info.write_text(json.dumps({"id": "video", "title": "Fixture Video", "url": self.source.as_uri(),
            "webpage_url": self.source.as_uri(), "ext": "mp4", "vcodec": "h264", "acodec": "aac",
            "uploader": "Fixture Artist", "upload_date": "20261008"}))
        optimizer = self.root / "ab-av1"
        optimizer.write_text("""#!/usr/bin/env python3
import os, sys
from pathlib import Path
mode = os.environ.get('TEST_OPTIMIZER', 'success')
if sys.argv[1] == 'crf-search':
 Path(sys.argv[sys.argv.index('--temp-dir') + 1], 'partial.mkv').write_bytes(b'partial')
 if mode != 'success':
  print('INFO internal optimizer log', file=sys.stderr)
  print('Failed to find a suitable crf' if mode == 'infeasible' else 'unexpected failure', file=sys.stderr)
  sys.exit(1)
 print('crf 24 VMAF 96.2 predicted video stream size 10 KiB (50%) taking 1 second')
else:
 print('96.2')
""")
        optimizer.chmod(0o755)
        self.env = dict(os.environ, XDG_CACHE_HOME=str(self.root / "cache"), XDG_STATE_HOME=str(self.root / "state"),
            PHOENIX_YT_DLP_BIN=YT_DLP, PHOENIX_MEDIA_PYTHON=sys.executable,
            PHOENIX_MEDIA_CLI_HELPER=str(ROOT / "media-cli.py"), PHOENIX_MEDIA_AB_AV1=str(optimizer),
            PHOENIX_MEDIA_FFMPEG_DIRECTORY=str(Path(shutil.which("ffmpeg")).parent))

    def test_missing_upload_year_is_not_invented(self):
        data = json.loads(self.info.read_text())
        data.pop("upload_date")
        self.info.write_text(json.dumps(data))
        destination = self.root / "missing-year"
        result = subprocess.run(["bash", str(ROOT / "download"), "video", "--original",
            "--enable-file-urls", "--load-info-json", str(self.info), "-P", str(destination)],
            env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        output = destination / "Fixture Video.mp4"
        tags = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
            "format_tags", "-of", "json", str(output)], text=True))["format"]["tags"]
        self.assertFalse({key.lower() for key in tags} & {"date", "year"})

    def test_optimization_and_failures_publish_only_valid_final_extensions(self):
        for mode, extension, codecs in (("success", "webm", ["av1", "opus"]),
                                        ("infeasible", "mp4", ["h264", "aac"]),
                                        ("unexpected", "mp4", ["h264", "aac"])):
            with self.subTest(mode=mode):
                destination = self.root / mode
                result = subprocess.run(["bash", str(ROOT / "download"), "video", "--enable-file-urls",
                    "--load-info-json", str(self.info), "-P", str(destination)],
                    env=dict(self.env, TEST_OPTIMIZER=mode), capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                output = destination / f"Fixture Video.{extension}"
                self.assertEqual([output], list(destination.iterdir()))
                data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams",
                    "-of", "json", str(output)], text=True))
                self.assertEqual(codecs, [s["codec_name"] for s in data["streams"]])
                tags = json.loads(subprocess.check_output(["ffprobe", "-v", "error",
                    "-show_entries", "format_tags", "-of", "json", str(output)], text=True))["format"]["tags"]
                tags = {key.lower(): value for key, value in tags.items()}
                self.assertEqual("2026", tags["date"])
                self.assertEqual("Fixture Artist", tags["artist"])
                subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"],
                               check=True, capture_output=True)
                self.assertIn(str(destination), result.stdout)
                self.assertNotIn("INFO internal", result.stdout + result.stderr)
                self.assertFalse(list((self.root / "cache/phoenix-media").glob("video.*")))
                if mode != "success":
                    self.assertIn("Keeping original (h264/aac)", result.stdout)



if __name__ == "__main__":
    unittest.main()
