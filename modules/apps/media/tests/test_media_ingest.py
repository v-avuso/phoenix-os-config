import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "media-ingest.py"
SPEC = importlib.util.spec_from_file_location("media_ingest", SCRIPT)
media_ingest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = media_ingest
SPEC.loader.exec_module(media_ingest)


def candidate(recording_id, score, title, artist, acoustid_id="acid-1"):
    return {
        "recording_id": recording_id,
        "score": score,
        "title": title,
        "artist": artist,
        "acoustid_id": acoustid_id,
    }


class IdentificationPolicyTests(unittest.TestCase):
    def test_accepts_one_high_confidence_recording_identity(self):
        selected, decision = media_ingest.select_candidate(
            [candidate("mbid-a", 0.96, "Song", "Artist")],
            {"title": "Artist - Song (Official Video)", "artist": "Channel"},
        )
        self.assertEqual("mbid-a", selected["recording_id"])
        self.assertEqual("unique_high_score", decision["reason"])

    def test_rejects_low_fingerprint_score_even_with_exact_text(self):
        selected, decision = media_ingest.select_candidate(
            [candidate("mbid-a", 0.79, "Song", "Artist")],
            {"title": "Song", "artist": "Artist"},
        )
        self.assertIsNone(selected)
        self.assertEqual("low_fingerprint_score", decision["reason"])

    def test_rejects_close_candidates_without_a_clear_metadata_winner(self):
        selected, decision = media_ingest.select_candidate(
            [
                candidate("mbid-a", 0.96, "Song", "Artist"),
                candidate("mbid-b", 0.95, "Song", "Artist"),
            ],
            {"title": "Song", "artist": "Artist"},
        )
        self.assertIsNone(selected)
        self.assertEqual("ambiguous_candidates", decision["reason"])

    def test_fallback_text_can_break_a_close_strong_fingerprint_tie(self):
        selected, decision = media_ingest.select_candidate(
            [
                candidate("mbid-a", 0.96, "Other Song", "Other Artist"),
                candidate("mbid-b", 0.95, "Song", "Artist"),
            ],
            {"title": "ARTIST – Song [Official Video]", "artist": "Artist"},
        )
        self.assertEqual("mbid-b", selected["recording_id"])
        self.assertEqual("metadata_tiebreak", decision["reason"])

    def test_metadata_cannot_rescue_a_poor_fingerprint_match(self):
        selected, decision = media_ingest.select_candidate(
            [
                candidate("mbid-a", 0.82, "Song", "Artist"),
                candidate("mbid-b", 0.81, "Different Song", "Other Artist"),
            ],
            {"title": "Song", "artist": "Artist"},
        )
        self.assertIsNone(selected)
        self.assertEqual("low_fingerprint_score", decision["reason"])

    def test_version_tokens_break_tie_between_original_and_remaster(self):
        selected, decision = media_ingest.select_candidate(
            [
                candidate("original", 0.96, "Night Song", "Artist"),
                candidate("remaster", 0.95, "Night Song - 2011 Remastered", "Artist"),
            ],
            {"title": "Artist - Night Song Remastered", "artist": "Artist"},
        )
        self.assertEqual("remaster", selected["recording_id"])
        self.assertEqual("metadata_tiebreak", decision["reason"])

    def test_duplicate_acoustid_results_for_one_recording_are_one_identity(self):
        selected, decision = media_ingest.select_candidate(
            [
                candidate("mbid-a", 0.93, "Song", "Artist", "acid-1"),
                candidate("mbid-a", 0.96, "Song", "Artist", "acid-2"),
            ],
            {"title": "Song", "artist": "Artist"},
        )
        self.assertEqual("mbid-a", selected["recording_id"])
        self.assertEqual("unique_high_score", decision["reason"])
        self.assertEqual(1, decision["recording_count"])


class MetadataPolicyTests(unittest.TestCase):
    def test_empty_yt_dlp_exec_hints_decode_to_none(self):
        self.assertIsNone(media_ingest.decode_exec_hint("__phoenix_none__"))
        self.assertEqual("Found Album", media_ingest.decode_exec_hint("Found Album"))

    def test_source_metadata_is_not_written_as_release_metadata_without_release(self):
        values = media_ingest.canonical_tag_values(
            {
                "recording_id": "mbid-recording",
                "acoustid_id": "acid-1",
                "title": "Canonical Track",
                "artist": "Canonical Artist",
                "date": "1998",
                "genres": ["rock"],
                "release": None,
            }
        )
        self.assertEqual(["Canonical Track"], values["title"])
        self.assertEqual(["Canonical Artist"], values["artist"])
        self.assertEqual(["mbid-recording"], values["musicbrainz_trackid"])
        self.assertEqual(["acid-1"], values["acoustid_id"])
        for field in ("album", "albumartist", "tracknumber", "discnumber"):
            self.assertNotIn(field, values)

    def test_confident_release_contributes_album_artist_track_disc_and_date(self):
        enrichment = {
            "recording_id": "mbid-recording",
            "acoustid_id": "acid-1",
            "title": "Canonical Track",
            "artist": "Canonical Artist",
            "date": "2004-02-03",
            "genres": [],
            "release": {
                "id": "release-id",
                "album": "Chosen Album",
                "albumartist": "Album Artist",
                "date": "2004-02-03",
                "tracknumber": "04",
                "discnumber": "2",
            },
        }
        self.assertEqual(
            {
                "album": ["Chosen Album"],
                "albumartist": ["Album Artist"],
                "tracknumber": ["04"],
                "discnumber": ["2"],
            },
            {key: media_ingest.canonical_tag_values(enrichment)[key]
             for key in ("album", "albumartist", "tracknumber", "discnumber")},
        )

    def test_release_selection_requires_a_clear_supported_hint(self):
        releases = [
            {"id": "r1", "title": "Original Album", "date": "2000-01-01"},
            {"id": "r2", "title": "Deluxe Remaster", "date": "2012-01-01"},
        ]
        selected, reason = media_ingest.select_release(releases, album_hint=None, date_hint=None)
        self.assertIsNone(selected)
        self.assertEqual("release_ambiguous", reason)
        selected, reason = media_ingest.select_release(
            releases, album_hint="Deluxe Remaster", date_hint="2012-01-01"
        )
        self.assertEqual("r2", selected["id"])
        self.assertEqual("album_hint", reason)

    def test_a_single_musicbrainz_release_is_selectable_without_inventing_another(self):
        selected, reason = media_ingest.select_release(
            [{"id": "only", "title": "Only Release", "date": "2001"}],
            album_hint=None,
            date_hint=None,
        )
        self.assertEqual("only", selected["id"])
        self.assertEqual("sole_release", reason)

    def test_genres_require_votes_and_relative_support_and_are_limited_to_five(self):
        genres = [{"name": f"genre-{i}", "count": count} for i, count in enumerate((10, 8, 6, 5, 5, 4, 1))]
        self.assertEqual(
            ["genre-0", "genre-1", "genre-2", "genre-3", "genre-4"],
            media_ingest.select_genres(genres),
        )
        self.assertEqual([], media_ingest.select_genres([{"name": "weak", "count": 1}]))

    def test_filename_uses_canonical_title_and_removes_youtube_title_noise_naturally(self):
        self.assertEqual(
            "Canonical Artist - Canonical Track.opus",
            media_ingest.canonical_filename("/inbox/Artist - Track (Official Video).opus", "Canonical Artist", "Canonical Track"),
        )

    def test_duplicate_destination_uses_deterministic_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "Artist" / "Song.opus"
            destination.parent.mkdir()
            destination.write_bytes(b"existing")
            chosen = media_ingest.available_destination(destination)
            self.assertEqual(root / "Artist" / "Song (1).opus", chosen)
            self.assertEqual(b"existing", destination.read_bytes())


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.inbox = self.base / "_unsorted"
        self.inbox.mkdir()
        self.music = self.base / "music"
        self.music.mkdir()
        self.state = self.base / "runtime"
        self.source = self.inbox / "Artist - Track (Official Video).opus"
        self.source.write_bytes(b"fallback tags and embedded art")
        self.fallback = {"title": "Artist - Track (Official Video)", "artist": "Uploader", "date": "2024", "purl": "https://source.invalid/watch/1"}
        self.recording = {
            "recording": {
                "id": "mbid-a",
                "title": "Canonical Track",
                "artist-credit-phrase": "Canonical Artist",
                "first-release-date": "1998",
                "genre-list": [{"name": "rock", "count": 8}, {"name": "pop", "count": 2}],
                "release-list": [],
            }
        }

    def adapters(self, response=None, *, recording=None, release=None, tag_writer=None):
        class Acoustid:
            def __init__(self):
                self.fingerprints = []
                self.lookups = []

            def fingerprint_file(inner, path, maxlength=120, force_fpcalc=False):
                inner.fingerprints.append((str(path), force_fpcalc))
                return 180, "test-fingerprint"

            def lookup(inner, client, fingerprint, duration, *, meta, timeout):
                inner.lookups.append((client, fingerprint, duration, meta, timeout))
                return response or {"status": "ok", "results": []}

            def parse_lookup_result(inner, data):
                for result in data.get("results", []):
                    for recording in result.get("recordings", []):
                        artist = "".join(
                            item.get("name", "") + item.get("joinphrase", "")
                            for item in recording.get("artists", [])
                        )
                        yield result["score"], recording["id"], recording.get("title"), artist

        return media_ingest.ServiceAdapters(
            acoustid=Acoustid(),
            musicbrainz_recording=lambda mbid, state: recording or self.recording,
            musicbrainz_release=lambda release_id, state: release or {},
            tag_reader=lambda path: dict(self.fallback),
            tag_writer=tag_writer or (lambda path, data: ["title", "artist"]),
            rate_limiter=lambda service, interval, state_dir, call: call(),
        )

    def test_worker_invokes_pyacoustid_fingerprint_and_lookup(self):
        adapters = self.adapters({"status": "ok", "results": []})
        result = media_ingest.identify_file(
            self.source, self.fallback, {}, "test-client-key", self.state, adapters=adapters
        )
        self.assertEqual("no_match", result["reason"])
        self.assertEqual((str(self.source), True), adapters.acoustid.fingerprints[0])
        self.assertEqual("test-client-key", adapters.acoustid.lookups[0][0])
        self.assertEqual(5, adapters.acoustid.lookups[0][4])

    def test_worker_automatically_reads_key_from_secret_service(self):
        adapters = self.adapters({"status": "ok", "results": []})
        result = media_ingest.subprocess.CompletedProcess([], 0, "test-client-key\n", "")
        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(media_ingest.subprocess, "run", return_value=result) as run:
                media_ingest.process_file(
                    self.inbox, self.source, music_root=self.music, state_directory=self.state,
                    fallback_metadata=self.fallback, adapters=adapters,
                )
        self.assertEqual(
            ["secret-tool", "lookup", "service", "phoenix-media", "key", "acoustid-client"],
            run.call_args.args[0],
        )
        self.assertEqual("test-client-key", adapters.acoustid.lookups[0][0])

    def test_process_routes_no_match_with_original_fallback_file_unchanged(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback,
                adapters=self.adapters(),
            )
        reviewed = self.inbox / "_review/Artist - Track (Official Video).opus"
        self.assertEqual(0, status)
        self.assertEqual(b"fallback tags and embedded art", reviewed.read_bytes())
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual("no_match", record["reason"])
        self.assertEqual("review", record["route"])

    def test_strong_match_writes_canonical_tags_and_organizes_by_artist(self):
        response = {"status": "ok", "results": [{"id": "acid-1", "score": 0.98, "recordings": [{"id": "mbid-a", "title": "Canonical Track", "artists": [{"name": "Canonical Artist"}]}]}]}
        writes = []
        def write_tags(path, values):
            writes.append(values)
            path.write_bytes(b"canonical tags and preserved embedded art")
            return list(values)
        adapters = self.adapters(response, tag_writer=write_tags)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        target = self.music / "Canonical Artist" / "Canonical Artist - Canonical Track.opus"
        self.assertEqual(0, status)
        self.assertEqual(b"canonical tags and preserved embedded art", target.read_bytes())
        self.assertEqual("Canonical Track", writes[0]["title"][0])
        self.assertEqual("Canonical Artist", writes[0]["artist"][0])
        self.assertNotIn("album", writes[0])
        self.assertFalse(self.source.exists())
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual("accepted", record["reason"])
        self.assertEqual("unique_high_score", record["acceptance_reason"])

    def test_release_match_writes_release_metadata_and_uses_album_directory(self):
        response = {"status": "ok", "results": [{"id": "acid-1", "score": 0.98, "recordings": [{"id": "mbid-a", "title": "Canonical Track", "artists": [{"name": "Canonical Artist"}]}]}]}
        recording = {"recording": {**self.recording["recording"], "release-list": [{"id": "release-a", "title": "Chosen Album", "date": "1998-04-02"}]}}
        release = {"release": {"id": "release-a", "title": "Chosen Album", "artist-credit": [{"name": "Album Artist", "artist": {"id": "artist-id", "name": "Album Artist"}}], "date": "1998-04-02", "media": [{"position": "2", "tracks": [{"position": "4", "number": "04", "recording": {"id": "mbid-a"}}]}]}}
        writes = []
        adapters = self.adapters(response, recording=recording, release=release, tag_writer=lambda path, values: (writes.append(values), path.write_bytes(b"tagged"), list(values))[2])
        with contextlib.redirect_stdout(io.StringIO()):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback,
                release_hints={"album": "Chosen Album", "date": "1998-04-02"}, adapters=adapters,
            )
        target = self.music / "Canonical Artist" / "Chosen Album" / "Canonical Artist - Canonical Track.opus"
        self.assertEqual(0, status)
        self.assertTrue(target.exists())
        self.assertEqual(["4"], writes[0]["tracknumber"])
        self.assertEqual(["2"], writes[0]["discnumber"])
        self.assertEqual(["release-a"], writes[0]["musicbrainz_albumid"])
        self.assertEqual(["artist-id"], writes[0]["musicbrainz_albumartistid"])

    def test_tag_write_failure_is_distinct_and_routes_fallback_to_review(self):
        response = {"status": "ok", "results": [{"id": "acid-1", "score": 0.98, "recordings": [{"id": "mbid-a", "title": "Canonical Track", "artists": [{"name": "Canonical Artist"}]}]}]}
        adapters = self.adapters(response, tag_writer=lambda path, values: (_ for _ in ()).throw(OSError("tag failure")))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        result = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(0, status)
        self.assertEqual("tag_write_failure", result["reason"])
        self.assertEqual("tag failure", result["error_message"])
        self.assertEqual(b"fallback tags and embedded art", (self.inbox / "_review/Artist - Track (Official Video).opus").read_bytes())

    def test_missing_client_key_fails_fast_and_preserves_fallback_in_review(self):
        output = io.StringIO()
        started = media_ingest.time.monotonic()
        with contextlib.redirect_stdout(output):
            with patch.object(
                media_ingest.subprocess,
                "run",
                return_value=media_ingest.subprocess.CompletedProcess([], 1, "", "missing"),
            ):
                status = media_ingest.process_file(
                    self.inbox, self.source, music_root=self.music, state_directory=self.state,
                    fallback_metadata=self.fallback, adapters=self.adapters(),
                )
        elapsed = media_ingest.time.monotonic() - started
        result = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(0, status)
        self.assertLess(elapsed, 0.5)
        self.assertEqual("missing_acoustid_client_key", result["reason"])
        self.assertEqual(b"fallback tags and embedded art", (self.inbox / "_review/Artist - Track (Official Video).opus").read_bytes())

    def test_invalid_acoustid_key_logs_api_error_without_exposing_key_and_succeeds_download(self):
        adapters = self.adapters({
            "status": "error",
            "error": {"code": 4, "message": "invalid API key"},
        })
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-secret-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(0, status)
        self.assertEqual("acoustid_request_failure", record["reason"])
        self.assertEqual("ValueError", record["error_type"])
        self.assertEqual("AcoustID status='error' code=4: invalid API key", record["error_message"])
        self.assertNotIn("test-secret-key", output.getvalue())
        self.assertEqual(b"fallback tags and embedded art", (self.inbox / "_review/Artist - Track (Official Video).opus").read_bytes())

    def test_unusable_audio_is_routed_to_review_but_returns_failure(self):
        adapters = self.adapters()
        adapters.tag_reader = lambda path: (_ for _ in ()).throw(ValueError("invalid container data"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                adapters=adapters,
            )
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(1, status)
        self.assertEqual("unusable_audio", record["reason"])
        self.assertEqual("invalid container data", record["error_message"])
        self.assertEqual("review", record["route"])

    def test_fingerprint_service_failure_routes_usable_audio_to_review_successfully(self):
        adapters = self.adapters()
        adapters.acoustid.fingerprint_file = lambda *args, **kwargs: (_ for _ in ()).throw(
            TimeoutError("fpcalc timed out")
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(0, status)
        self.assertEqual("fingerprint_failure", record["reason"])
        self.assertEqual("review", record["route"])
        self.assertEqual(b"fallback tags and embedded art", (self.inbox / "_review/Artist - Track (Official Video).opus").read_bytes())

    def test_exception_diagnostic_is_sanitized_and_operational_review_succeeds(self):
        class BrokenAcoustid:
            def fingerprint_file(self, path, maxlength=120, force_fpcalc=False):
                return 100.0, "fp"
            def lookup(self, *args, **kwargs):
                raise RuntimeError("request included test-secret-key at https://example.invalid/?client=test-secret-key")
        adapters = self.adapters()
        adapters.acoustid = BrokenAcoustid()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-secret-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        record = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(0, status)
        self.assertEqual("request included [redacted] at [url]", record["error_message"])
        self.assertNotIn("test-secret-key", output.getvalue())

    def test_review_route_preserves_source_subdirectories(self):
        nested = self.inbox / "mixes" / "set-one" / "Track.opus"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"fallback tags and embedded art")
        with contextlib.redirect_stdout(io.StringIO()):
            status = media_ingest.process_file(
                self.inbox, nested, music_root=self.music, state_directory=self.state,
                client_key="test-key", fallback_metadata=self.fallback, adapters=self.adapters(),
            )
        self.assertEqual(0, status)
        self.assertTrue((self.inbox / "_review/mixes/set-one/Track.opus").exists())

    def test_scanner_excludes_review_and_temporary_worker_outputs(self):
        ordinary = self.inbox / "new.opus"
        temporary = self.inbox / ".new.phoenix-write.opus"
        reviewed = self.inbox / "_review" / "already-reviewed.opus"
        for path in (ordinary, temporary, reviewed):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
        self.assertEqual([self.source, ordinary], media_ingest.audio_files(self.inbox))

    def test_api_failure_is_distinct_from_no_match_and_key_is_never_logged(self):
        class BrokenAcoustid:
            def fingerprint_file(self, path, maxlength=120, force_fpcalc=False):
                return 100, "fp"
            def lookup(self, *args, **kwargs):
                raise RuntimeError("request included test-secret-key")
        adapters = self.adapters()
        adapters.acoustid = BrokenAcoustid()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = media_ingest.process_file(
                self.inbox, self.source, music_root=self.music, state_directory=self.state,
                client_key="test-secret-key", fallback_metadata=self.fallback, adapters=adapters,
            )
        log = output.getvalue()
        self.assertEqual(0, status)
        self.assertNotIn("test-secret-key", log)
        result = json.loads(log.splitlines()[-1])
        self.assertEqual("acoustid_request_failure", result["reason"])
        self.assertEqual("request included [redacted]", result["error_message"])

    def test_key_read_comes_from_secret_service_without_logging_or_secret_arguments(self):
        result = media_ingest.subprocess.CompletedProcess([], 0, " \tclient-key-value \r\n", "")
        with patch.object(media_ingest.subprocess, "run", return_value=result) as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                key = media_ingest.read_client_key()
        self.assertEqual("client-key-value", key)
        self.assertEqual(
            ["secret-tool", "lookup", "service", "phoenix-media", "key", "acoustid-client"],
            run.call_args.args[0],
        )
        self.assertEqual(60, run.call_args.kwargs["timeout"])
        self.assertEqual("", output.getvalue())

    def test_missing_secret_returns_no_key_without_printing_lookup_output(self):
        result = media_ingest.subprocess.CompletedProcess([], 1, "", "No such item")
        with patch.object(media_ingest.subprocess, "run", return_value=result):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertIsNone(media_ingest.read_client_key())
        self.assertEqual("", output.getvalue())

    def test_no_beets_library_database_or_beets_package_dependency_remains(self):
        module = (SCRIPT.parent / "default.nix").read_text()
        docs = (SCRIPT.parent / "MEDIA_WORKFLOW.md").read_text()
        desktop = (SCRIPT.parents[2] / "desktop.nix").read_text()
        self.assertNotIn("beets", module.casefold())
        self.assertNotIn("library.db", module)
        self.assertNotIn("beets", docs.casefold())
        self.assertNotIn("beetsStateDirectory", module)
        self.assertIn("libsecret", module)
        self.assertNotIn("sops", module + docs + desktop)
        self.assertNotIn("/run/secrets/acoustid-client-key", module + docs)
        self.assertIn("services.gnome.gnome-keyring.enable = lib.mkIf", desktop)


if __name__ == "__main__":
    unittest.main()
