import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "download"


class DownloadCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "argv.json"
        self.dl = self.root / "dl"
        self.dl.symlink_to(SCRIPT)
        self.dlm = self.root / "dlm"
        self.dlm.symlink_to(SCRIPT)
        self.dlv = self.root / "dlv"
        self.dlv.symlink_to(SCRIPT)
        self.fake = self.root / "capture.py"
        self.fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['CAPTURE'], 'w') as out: json.dump(args, out)\n"
            "from pathlib import Path\n"
            "counter = Path(os.environ['CAPTURE'] + '.attempts')\n"
            "attempt = int(counter.read_text()) + 1 if counter.exists() else 1\n"
            "counter.write_text(str(attempt))\n"
            "with open(os.environ['CAPTURE'] + '.history', 'a') as out: out.write(json.dumps(args) + '\\n')\n"
            "if attempt <= int(os.environ.get('TRANSIENT_FAILURES', '0')):\n"
            " print('ERROR: unable to download video data: HTTP Error 403: Forbidden')\n"
            " sys.exit(1)\n"
            "is_video = '--print-to-file' in args\n"
            "if os.environ.get('FAKE_STDOUT') and (not is_video or '--verbose' in args): print(os.environ['FAKE_STDOUT'])\n"
            "if os.environ.get('FAKE_STDERR') and (not is_video or '--verbose' in args): print(os.environ['FAKE_STDERR'], file=sys.stderr)\n"
            "if os.environ.get('FAKE_PROGRESS'): print(os.environ['FAKE_PROGRESS'])\n"
            "if os.environ.get('FAKE_MERGE'): print(os.environ['FAKE_MERGE'])\n"
            "if os.environ.get('PIPELINE_ERROR'):\n"
            " print('ERROR: Postprocessing: ' + os.environ['PIPELINE_ERROR'], file=sys.stderr); sys.exit(1)\n"
            "if os.environ.get('FAIL'):\n"
            " print('ERROR: [youtube] Requested video is unavailable', file=sys.stderr)\n"
            " for i, arg in enumerate(args[:-1]):\n"
            "  if arg == '--paths' and args[i + 1].split(':', 1)[0] in ('temp', 'thumbnail'):\n"
            "   from pathlib import Path\n"
            "   path = Path(args[i + 1].split(':', 1)[1]); path.mkdir(parents=True, exist_ok=True); (path / 'partial').write_text('owned')\n"
            " sys.exit(int(os.environ['FAIL']))\n"
            "if is_video:\n"
            " from pathlib import Path\n"
            " result = Path(args[args.index('--print-to-file') + 2])\n"
            " result.parent.mkdir(parents=True, exist_ok=True)\n"
            " result.write_text(os.environ.get('VIDEO_RESULT', '/home/v/Downloads/videos/Video title.webm') + '\\n')\n"
            "if os.environ.get('RUN_AFTER_MOVE'):\n"
            " import shlex, subprocess\n"
            " hook = args[args.index('--exec') + 1].split(':', 1)[1]\n"
            " hook = hook.replace('%(filepath)q', shlex.quote(os.environ['TEST_FILE']))\n"
            " hook = hook.replace('%(album|__phoenix_none__)q', shlex.quote('__phoenix_none__'))\n"
            " hook = hook.replace('%(release_date|__phoenix_none__)q', shlex.quote('__phoenix_none__'))\n"
            " result = subprocess.run(hook, shell=True, check=False)\n"
            " sys.exit(result.returncode)\n"
        )
        self.fake.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(
            PHOENIX_YT_DLP_BIN=str(self.fake),
            CAPTURE=str(self.log),
            PHOENIX_MEDIA_INGEST_COMMAND="/nix/bin/phoenix-media-ingest",
            PHOENIX_MEDIA_CLI_HELPER=str(SCRIPT.with_name("media-cli.py")),
            XDG_STATE_HOME=str(self.root / "state"),
            XDG_CACHE_HOME=str(self.root / "cache"),
        )

    def run_command(self, *args, command=SCRIPT, env=None):
        return subprocess.run(
            ["bash", str(command), *args],
            env=env or self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_help_and_errors(self):
        help_result = self.run_command("--help")
        dl_help_result = self.run_command("--help", command=self.dl)
        self.assertEqual(0, help_result.returncode)
        self.assertEqual(0, dl_help_result.returncode)
        self.assertIn("download music <URL> [yt-dlp options...]", help_result.stdout)
        self.assertIn("download video <URL> [yt-dlp options...]", help_result.stdout)
        self.assertIn("Aliases: m = music, v = video", help_result.stdout)
        self.assertIn("exact URL", help_result.stdout)
        self.assertIn("best available audio-only stream", help_result.stdout)
        self.assertIn("-v or --verbose", help_result.stdout)
        self.assertNotEqual(0, self.run_command().returncode)
        self.assertNotEqual(0, self.run_command("unknown").returncode)
        self.assertNotEqual(0, self.run_command("music").returncode)
        self.assertNotEqual(0, self.run_command("video").returncode)

    def test_all_music_spellings_pass_exact_url_and_clean_embedded_metadata(self):
        extra = ["https://www.youtube.com/watch?v=exact-source", "-o", "%(title)s ; $(safe)"]
        for mode, command in [("music", SCRIPT), ("m", SCRIPT), ("music", self.dl), (None, self.dlm)]:
            result = self.run_command(*(([mode] if mode else []) + extra), command=command)
            self.assertEqual(0, result.returncode, result.stderr)
            args = json.loads(self.log.read_text())
            index = args.index(extra[0])
            self.assertEqual(extra, args[index:index + len(extra)])
            self.assertNotIn("--extract-audio", args)
            self.assertIn("PhoenixCodecs:mode=audio;original=false", args)
            self.assertIn("--write-thumbnail", args)
            self.assertIn("bestaudio[acodec=opus]/bestaudio/best", args)
            self.assertIn("--progress", args)
            self.assertIn("--no-embed-info-json", args)
            self.assertNotIn("--write-info-json", args)
            self.assertIn("%(artist,channel,uploader,creator|)s:%(artist)s", args)
            self.assertIn("%(original_url,webpage_url)s:%(meta_purl)s", args)
            self.assertFalse(any("%(id)" in arg for arg in args))

    def test_x_status_defaults_to_first_playlist_item_for_audio_and_video(self):
        urls = ("https://x.com/artist/status/123", "https://twitter.com/artist/status/123?ref=share",
                "https://mobile.twitter.com/i/web/status/123", "https://www.x.com/i/status/123/video/1")
        for command in (self.dlm, self.dlv):
            for url in urls:
                with self.subTest(command=command.name, url=url):
                    result = self.run_command(url, command=command)
                    self.assertEqual(0, result.returncode, result.stderr)
                    args = json.loads(self.log.read_text())
                    self.assertEqual("1", args[args.index("--playlist-items") + 1])

    def test_explicit_x_playlist_selection_overrides_default(self):
        for command in (self.dlm, self.dlv):
            for selection in (("--playlist-items", "2,3"), ("--playlist-items=2:5",), ("-I", "2"), ("-I2",)):
                with self.subTest(command=command.name, selection=selection):
                    result = self.run_command("https://x.com/artist/status/123", *selection, command=command)
                    self.assertEqual(0, result.returncode, result.stderr)
                    args = json.loads(self.log.read_text())
                    self.assertEqual(list(selection), [arg for arg in args if arg in selection])
                    self.assertEqual(selection.count("--playlist-items"), args.count("--playlist-items"))

    def test_non_x_and_mixed_provider_urls_have_no_playlist_default(self):
        for urls in (("https://www.youtube.com/watch?v=123",), ("https://vimeo.com/123",),
                     ("https://x.com/artist",), ("https://x.com.evil.test/artist/status/123",),
                     ("https://example.test/x.com/artist/status/123",),
                     ("https://x.com/artist/status/123", "https://youtu.be/123")):
            for command in (self.dlm, self.dlv):
                with self.subTest(urls=urls, command=command.name):
                    result = self.run_command(*urls, command=command)
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertNotIn("--playlist-items", json.loads(self.log.read_text()))

    def test_original_bypasses_codec_policy_and_is_not_forwarded(self):
        result = self.run_command("video", "--original", "https://youtu.be/source")
        self.assertEqual(0, result.returncode, result.stderr)
        args = json.loads(self.log.read_text())
        self.assertNotIn("--original", args)
        self.assertIn("PhoenixCodecs:mode=video;original=true", args)
        self.assertEqual("bestvideo+bestaudio/best", args[args.index("--format") + 1])

    def test_default_ingester_and_custom_destination_are_safe(self):
        env = dict(self.env)
        env.pop("PHOENIX_MEDIA_INGEST_COMMAND")
        result = self.run_command("music", "https://youtu.be/source", "--paths", "/tmp/custom", env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        args = json.loads(self.log.read_text())
        self.assertIn("/tmp/custom", args)
        self.assertTrue(args[args.index("--exec") + 1].startswith("after_move:phoenix-media-ingest "))

    def test_failed_music_download_cleans_only_its_private_temporary_directory(self):
        env = dict(self.env)
        env["FAIL"] = "17"
        unrelated = self.root / "keep.jpg"
        unrelated.write_text("user data")
        result = self.run_command("music", "https://youtu.be/source", env=env)
        self.assertEqual(17, result.returncode)
        self.assertIn("✗ Download failed: [youtube] Requested video is unavailable", result.stderr)
        self.assertNotIn("phoenix-download.", result.stderr)
        actual = json.loads(self.log.read_text())
        temporary_paths = [
            actual[index + 1].split(":", 1)[1]
            for index, value in enumerate(actual[:-1])
            if value == "--paths" and actual[index + 1].split(":", 1)[0] in ("temp", "thumbnail")
        ]
        self.assertEqual(2, len(temporary_paths))
        self.assertEqual(Path(temporary_paths[0]) / "attempt-1", Path(temporary_paths[1]))
        self.assertFalse(Path(temporary_paths[0]).exists())
        self.assertEqual("user data", unrelated.read_text())

    def test_dlm_postprocessor_review_success_does_not_become_download_failure(self):
        env = dict(self.env)
        env["RUN_AFTER_MOVE"] = "1"
        env["TEST_FILE"] = str(self.root / "usable audio.opus")
        reviewed = self.root / "reviewed.txt"
        ingester = self.root / "ingester.py"
        ingester.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(reviewed)!r}).write_text('routed to review')\n"
        )
        ingester.chmod(0o755)
        env["PHOENIX_MEDIA_INGEST_COMMAND"] = str(ingester)

        result = self.run_command(
            "https://youtu.be/exact-source", command=self.dlm, env=env
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("Postprocessing", result.stderr)
        self.assertNotIn("music download failed", result.stderr)
        self.assertEqual("routed to review", reviewed.read_text())
        self.assertIn("✓ Download completed.", result.stdout)

    def test_concise_no_match_result_and_private_structured_log(self):
        event = {
            "component": "phoenix-media-ingest", "event": "file_result",
            "file": "Fallback.opus", "route": "review", "reason": "no_match",
            "destination": "/home/v/sync/music/_unsorted/_review/Fallback.opus",
        }
        env = dict(self.env, FAKE_STDOUT=json.dumps(event), FAKE_STDERR="[MetadataParser] internal chatter")
        result = self.run_command("music", "https://youtu.be/source", env=env)
        self.assertEqual(0, result.returncode)
        self.assertEqual(
            "✓ Downloaded: Fallback.opus\nℹ No AcoustID match, manual review required.\n→ Review: ~/sync/music/_unsorted/_review/\n",
            result.stdout,
        )
        self.assertNotIn("MetadataParser", result.stdout)
        self.assertNotIn("phoenix-download.", result.stdout)
        log = Path(env["XDG_STATE_HOME"]) / "phoenix-media" / "ingest.jsonl"
        self.assertEqual(json.loads(log.read_text()), event)
        self.assertEqual(0o600, log.stat().st_mode & 0o777)

    def test_concise_matched_result(self):
        event = {
            "component": "phoenix-media-ingest", "event": "file_result",
            "route": "library", "reason": "accepted",
            "destination": "/home/v/sync/music/Artist/Album/Artist - Title.opus",
        }
        result = self.run_command(
            "music", "https://youtu.be/source", env=dict(self.env, FAKE_STDOUT=json.dumps(event))
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual(
            "✓ Downloaded: Artist - Title.opus\n✓ Metadata: confidently matched\n→ Library: ~/sync/music/Artist/Album/\n",
            result.stdout,
        )

    def test_concise_metadata_operational_warning_is_success(self):
        event = {
            "component": "phoenix-media-ingest", "event": "file_result",
            "route": "review", "reason": "acoustid_request_failure",
            "error_message": "AcoustID returned status=error (HTTP 503)",
            "destination": "/home/v/sync/music/_unsorted/_review/Fallback.opus",
        }
        result = self.run_command(
            "music", "https://youtu.be/source", env=dict(self.env, FAKE_STDOUT=json.dumps(event))
        )
        self.assertEqual(0, result.returncode)
        self.assertIn("⚠ Metadata: AcoustID lookup failed: AcoustID returned status=error (HTTP 503)", result.stdout)
        self.assertIn("→ Review: ~/sync/music/_unsorted/_review/", result.stdout)

    def test_weak_and_ambiguous_matches_request_manual_review_without_repeating_file(self):
        for reason, expected in (
            ("low_fingerprint_score", "ℹ No confident AcoustID match; manual review required"),
            ("ambiguous_candidates", "ℹ AcoustID match was ambiguous; manual review required"),
        ):
            event = {
                "component": "phoenix-media-ingest", "event": "file_result",
                "route": "review", "reason": reason,
                "destination": "/home/v/sync/music/_unsorted/_review/Fallback.opus",
            }
            result = self.run_command(
                "music", "https://youtu.be/source", env=dict(self.env, FAKE_STDOUT=json.dumps(event))
            )
            self.assertEqual(0, result.returncode)
            self.assertIn(expected, result.stdout)
            self.assertIn("→ Review: ~/sync/music/_unsorted/_review/", result.stdout)

    def test_verbose_flag_exposes_yt_dlp_and_worker_diagnostics(self):
        event = {"component": "phoenix-media-ingest", "event": "file_result", "route": "review", "reason": "no_match", "destination": "/home/v/sync/music/_unsorted/_review/Fallback.opus"}
        env = dict(self.env, FAKE_STDOUT=json.dumps(event), FAKE_STDERR="extractor diagnostic")
        for args, command in (
            (("--verbose", "music", "https://youtu.be/source"), SCRIPT),
            (("music", "https://youtu.be/source", "-v"), SCRIPT),
            (("https://youtu.be/source", "--verbose"), self.dlm),
        ):
            result = self.run_command(*args, command=command, env=env)
            self.assertEqual(0, result.returncode)
            actual = json.loads(self.log.read_text())
            self.assertIn("--verbose", actual)
            self.assertNotIn("--quiet", actual)
            self.assertIn("extractor diagnostic", result.stdout)
            self.assertIn('"event": "file_result"', result.stdout)
            self.assertIn("→ Review: ~/sync/music/_unsorted/_review/", result.stdout)

    def test_dlv_and_video_forms_forward_all_options_and_keep_default_path(self):
        video_args = ["-S", "res:1080", "https://youtu.be/video?id=one&title=two"]
        for args, command in (
            (("video", *video_args), SCRIPT), (("v", *video_args), SCRIPT),
            (("video", *video_args), self.dl), (("v", *video_args), self.dl),
            (("-F", "https://youtu.be/video"), self.dlv),
        ):
            result = self.run_command(*args, command=command)
            self.assertEqual(0, result.returncode, result.stderr)
            actual = json.loads(self.log.read_text())
            self.assertIn("--paths", actual)
            self.assertIn("/home/v/Downloads/videos/", actual)
            self.assertIn("--output", actual)
            self.assertEqual("%(title)s.%(ext)s", actual[actual.index("--output") + 1])
            self.assertIn("--print-to-file", actual)
            self.assertIn("--no-overwrites", actual)
            self.assertEqual("--no-overwrites", actual[-3])
            forwarded = list(args if command == self.dlv else args[1:])
            index = actual.index(forwarded[0])
            self.assertEqual(forwarded, actual[index:index + len(forwarded)])
            self.assertIn("--quiet", actual)
            self.assertIn("--progress", actual)
            self.assertIn("--newline", actual) # Machine records; renderer owns terminal updates
            self.assertIn("--progress-template", actual)
            self.assertEqual(
                'postprocess:PHOENIX_PP %(progress)j',
                actual[actual.index("--progress-template") + 1],
            )

        verbose = self.run_command("--verbose", "video", "https://youtu.be/video", command=SCRIPT)
        self.assertEqual(0, verbose.returncode)
        verbose_args = json.loads(self.log.read_text())
        self.assertIn("--verbose", verbose_args)
        self.assertNotIn("--quiet", verbose_args)
        self.assertEqual("--no-overwrites", verbose_args[-3])

    def test_video_concise_output_keeps_progress_merge_status_and_title_filename(self):
        env = dict(
            self.env,
            VIDEO_RESULT="/home/v/Downloads/videos/Video title.webm",
            FAKE_STDOUT="[debug] extractor details",
            FAKE_STDERR="ffmpeg command line: internal details",
            FAKE_PROGRESS='PHOENIX_DL {"status":"downloading","_percent_str":"78%","vcodec":"av01"}\nPHOENIX_DL {"status":"finished","_percent_str":"100%","vcodec":"av01"}\nPHOENIX_DL {"status":"finished","_percent_str":"100%","vcodec":"none"}',
            FAKE_MERGE='PHOENIX_PP {"postprocessor":"Merger","status":"started"}\nPHOENIX_PP {"postprocessor":"Merger","status":"finished"}\nPHOENIX_PP {"postprocessor":"MoveFiles","status":"started"}\nPHOENIX_PP {"postprocessor":"MoveFiles","status":"finished"}',
        )
        result = self.run_command("video", "https://youtu.be/video", env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Downloading [██████████] 100%", result.stdout)
        self.assertEqual(1, result.stdout.count("Downloading ["))
        self.assertEqual(0, result.stdout.count("Merging video and audio…"))
        self.assertNotIn("started", result.stdout)
        self.assertNotIn("PHOENIX_", result.stdout)
        self.assertNotIn("78%", result.stdout)
        self.assertNotIn("\r", result.stdout)
        self.assertNotIn("extractor details", result.stdout)
        self.assertNotIn("youtube id", result.stdout)

    def test_video_progress_real_tty_updates_in_place_and_shows_elapsed_activity(self):
        import pty
        import select
        import sys
        import time
        producer = self.root / "progress.py"
        producer.write_text(
            "import time\n"
            "print('PHOENIX_DL {\"status\":\"downloading\",\"vcodec\":\"av01\",\"downloaded_bytes\":78,\"total_bytes\":100}', flush=True)\n"
            "print('PHOENIX_DL {\"status\":\"finished\",\"vcodec\":\"av01\",\"_percent_str\":\"100%\"}', flush=True)\n"
            "print('PHOENIX_PP {\"postprocessor\":\"Merger\",\"status\":\"started\"}', flush=True)\n"
            "time.sleep(1.2)\n"
            "print('WARNING: retained warning', flush=True)\n"
            "print('PHOENIX_PP {\"postprocessor\":\"Merger\",\"status\":\"finished\"}', flush=True)\n"
        )
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable, str(SCRIPT.parent / "media-cli.py"),
                                    "run-download", "--video", "--output", str(self.root / "tty.log"),
                                    "--temporary-root", str(self.root), "--", sys.executable, str(producer)],
                                   stdout=slave, stderr=slave, env=dict(self.env, TERM="xterm"))
        os.close(slave)
        output = bytearray()
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.2)[0]:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    output.extend(data)
            self.assertEqual(0, process.wait(timeout=2))
        finally:
            os.close(master)
            if process.poll() is None:
                process.kill()
        text = output.decode()
        self.assertIn("\r\x1b[2KDownloading [███████░░░] 70%", text)
        self.assertNotIn("70%\r\n", text)
        self.assertIn("1s elapsed", text)
        self.assertEqual(1, text.count("finished ("))
        self.assertIn("WARNING: retained warning", text)

    def test_recoverable_403_retries_fresh_extraction_and_hides_recovered_error(self):
        for mode in ("music", "video"):
            for path in self.root.glob("argv.json.*"):
                path.unlink()
            result = self.run_command(mode, "https://youtu.be/source", env=dict(self.env, TRANSIENT_FAILURES="1"))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn("403", result.stdout + result.stderr)
            calls = [json.loads(line) for line in Path(str(self.log) + ".history").read_text().splitlines()]
            self.assertEqual(2, len(calls))
            self.assertNotEqual(calls[0][-1], calls[1][-1])
            self.assertFalse(Path(calls[0][-1].split(":", 1)[1]).exists())
        logs = list((self.root / "state/phoenix-media/downloads").glob("*.log"))
        self.assertTrue(any("403" in path.read_text() for path in logs))
        self.assertTrue(all(path.stat().st_mode & 0o077 == 0 for path in logs))

    def test_three_attempt_limit_and_delays_with_terminal_failure(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("media_cli", SCRIPT.with_name("media-cli.py"))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch.dict(os.environ, dict(self.env, TRANSIENT_FAILURES="9")), patch.object(cli.time, "sleep") as sleep:
            status = cli.run_download([str(self.fake)], self.root / "output.log", self.root, video=False, verbose=False)
        self.assertEqual(1, status)
        self.assertEqual([((1,),), ((5,),)], [(call.args,) for call in sleep.call_args_list])
        self.assertEqual("3", Path(str(self.log) + ".attempts").read_text())

    def test_video_temp_cleanup_and_keep_video_preservation(self):
        unrelated = self.root / "personal.webm"
        unrelated.write_text("keep")
        failed = self.run_command("video", "https://youtu.be/source", env=dict(self.env, FAIL="17"))
        self.assertEqual(17, failed.returncode)
        args = json.loads(self.log.read_text())
        staging = Path(args[-1].split(":", 1)[1])
        self.assertFalse(staging.exists())
        kept = self.run_command("video", "--keep-video", "https://youtu.be/source", env=dict(self.env, FAIL="17"))
        self.assertEqual(17, kept.returncode)
        staging = Path(json.loads(self.log.read_text())[-1].split(":", 1)[1])
        self.assertTrue((staging / "partial").exists())
        self.assertIn("Diagnostic staging retained", kept.stderr)
        self.assertEqual("keep", unrelated.read_text())

    def test_combined_progress_weights_sizes_and_does_not_finish_after_video(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("media_cli", SCRIPT.with_name("media-cli.py"))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        progress = cli.CombinedProgress()
        progress.plan([{"format_id": "401", "filesize": 60}, {"format_id": "251", "filesize": 40}])
        self.assertEqual((60, False), progress.update({"format_id": "401", "status": "finished"}))
        self.assertEqual((80, False), progress.update({"format_id": "251", "status": "downloading", "downloaded_bytes": 20, "total_bytes": 40}))
        self.assertEqual((100, True), progress.update({"format_id": "251", "status": "finished"}))
        progress.plan([{"format_id": "401", "vcodec": "av01"}, {"format_id": "251", "vcodec": "none"}])
        self.assertEqual((0, False), progress.update({"format_id": "401", "status": "downloading", "downloaded_bytes": 1000}))
        self.assertEqual((90, False), progress.update({"format_id": "401", "status": "finished"}))
        self.assertEqual((100, True), progress.update({"format_id": "251", "status": "finished"}))
        progress.plan(None)
        self.assertEqual((90, False), progress.update({"vcodec": "av01", "acodec": "none", "status": "finished"}))
        self.assertEqual((100, True), progress.update({"vcodec": "none", "acodec": "opus", "status": "finished"}))

    def test_audio_only_progress_uses_full_range_without_format_plan(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("media_cli", SCRIPT.with_name("media-cli.py"))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        progress = cli.CombinedProgress(audio_only=True)
        for plan in (None, [], [{"format_id": "251", "vcodec": "none"}]):
            progress.plan(plan)
            for downloaded, expected in ((0, 0), (50, 50), (90, 90)):
                self.assertEqual((expected, False), progress.update({
                    "format_id": "251", "vcodec": "none", "acodec": "opus",
                    "status": "downloading", "downloaded_bytes": downloaded, "total_bytes": 100,
                }))
            self.assertEqual((100, True), progress.update({
                "format_id": "251", "vcodec": "none", "status": "finished",
            }))
        # yt-dlp single-format sources may emit no requested_formats plan.
        events = 'PHOENIX_PLAN null\nPHOENIX_DL {"format_id":"251","vcodec":"none","status":"finished"}'
        result = self.run_command("music", "https://example.com/source", env=dict(self.env, FAKE_PROGRESS=events))
        self.assertEqual(0, result.returncode)
        self.assertIn("Downloading [██████████] 100%", result.stdout)

    def test_opaque_single_file_video_completes_download_progress(self):
        events = 'PHOENIX_PLAN null\nPHOENIX_DL {"status":"finished","vcodec":null,"acodec":null}'
        result = self.run_command("video", "https://example.com/source", env=dict(self.env, FAKE_PROGRESS=events))
        self.assertEqual(0, result.returncode)
        self.assertIn("Downloading [██████████] 100%", result.stdout)

    def test_audio_and_video_share_progress_and_hide_completion_speed(self):
        event = 'PHOENIX_DL {"status":"finished","vcodec":"none","acodec":"opus","_speed_str":"8MiB/s"}'
        for mode in ("music", "video"):
            # Single audio source: one selected format in the plan.
            events = 'PHOENIX_PLAN [{"format_id":"audio","filesize":100}]\n' + event
            result = self.run_command(mode, "https://example.com/source", env=dict(self.env, FAKE_PROGRESS=events))
            self.assertEqual(0, result.returncode)
            self.assertIn("Downloading [██████████] 100%", result.stdout)
            self.assertNotIn("8MiB/s", result.stdout)

    def test_recovered_extractor_warning_suppressed_but_actionable_warning_kept(self):
        warnings = "WARNING: Falling back to alternate player response\nWARNING: Your output folder is nearly full"
        result = self.run_command("music", "https://example.com/source", env=dict(self.env, FAKE_STDERR=warnings))
        self.assertEqual(0, result.returncode)
        self.assertNotIn("Falling back", result.stdout + result.stderr)
        self.assertIn("nearly full", result.stderr)

    def test_ignored_audio_is_a_failure_instead_of_false_success(self):
        ignored = json.dumps({"component":"phoenix-media-ingest", "event":"file_ignored", "reason":"unsupported_or_excluded"})
        result = self.run_command("music", "https://example.com/source", env=dict(self.env, FAKE_STDOUT=ignored))
        self.assertEqual(1, result.returncode)
        self.assertIn("ingestion rejected", result.stderr)

    def test_video_collision_protection_overrides_force_overwrite_option(self):
        result = self.run_command(
            "video", "https://youtu.be/video", "--force-overwrites", env=self.env
        )
        self.assertEqual(0, result.returncode, result.stderr)
        actual = json.loads(self.log.read_text())
        self.assertIn("--force-overwrites", actual)
        self.assertEqual("--no-overwrites", actual[-3])

    def test_optimizer_logs_are_private_in_normal_mode_and_visible_in_verbose_mode(self):
        diagnostic = 'PHOENIX_ENCODE ' + json.dumps({"status": "diagnostic", "stderr": "INFO optimizer internals\nDEBUG full command"})
        env = dict(self.env, FAKE_PROGRESS=diagnostic)
        normal = self.run_command("video", "https://youtu.be/video", env=env)
        self.assertEqual(0, normal.returncode)
        self.assertNotIn("optimizer internals", normal.stdout + normal.stderr)
        logs = list((self.root / "state/phoenix-media/downloads").glob("*.log"))
        self.assertTrue(any("optimizer internals" in log.read_text() for log in logs))
        verbose = self.run_command("video", "https://youtu.be/video", "--verbose", env=env)
        self.assertIn("INFO optimizer internals", verbose.stdout)
        self.assertIn("DEBUG full command", verbose.stdout)

    def test_processing_failures_are_distinct_and_encoding_is_not_overall_success(self):
        completed = 'PHOENIX_ENCODE ' + json.dumps({"status": "finished", "encoder": "Opus", "elapsed": 1.7})
        for error in ("Encoding failed: encoder error", "Metadata processing failed: invalid header",
                      "Artwork processing failed: invalid picture", "Media validation failed: truncated output"):
            with self.subTest(error=error):
                result = self.run_command("video", "https://youtu.be/video",
                    env=dict(self.env, FAKE_PROGRESS=completed, PIPELINE_ERROR=error))
                self.assertNotEqual(0, result.returncode)
                self.assertIn("✗ Processing failed: " + error, result.stderr)
                self.assertNotIn("✓ Downloaded:", result.stdout)
                self.assertNotIn("finished (1.7s)", result.stdout)

    def test_video_verbose_mode_exposes_ffmpeg_diagnostics_and_download_failures(self):
        env = dict(
            self.env,
            FAKE_STDOUT="[debug] selected video format 399 and audio format 251",
            FAKE_STDERR="[debug] ffmpeg command line: ffmpeg -c copy",
        )
        result = self.run_command("--verbose", "https://youtu.be/video", command=self.dlv, env=env)
        self.assertEqual(0, result.returncode)
        self.assertIn("[debug] selected video format 399 and audio format 251", result.stdout)
        self.assertIn("[debug] ffmpeg command line: ffmpeg -c copy", result.stdout)
        self.assertIn("✓ Downloaded: Video title.webm", result.stdout)

        failure = self.run_command(
            "video", "https://youtu.be/video", env=dict(self.env, FAIL="23")
        )
        self.assertEqual(23, failure.returncode)
        self.assertIn("ERROR: [youtube] Requested video is unavailable", failure.stderr)
        self.assertIn("✗ Video download failed: [youtube] Requested video is unavailable", failure.stderr)


if __name__ == "__main__":
    unittest.main()
