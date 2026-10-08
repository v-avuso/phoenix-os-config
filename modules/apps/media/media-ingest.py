#!/usr/bin/env python3
"""Fingerprint one completed audio file, enrich a strong match, or route it to review."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, quote_plus
from urllib.request import Request, urlopen


AUDIO_SUFFIXES = {
    ".aac", ".aif", ".aiff", ".alac", ".ape", ".flac", ".m4a", ".mp3",
    ".mpc", ".oga", ".ogg", ".opus", ".wav", ".wma", ".wv",
}
EXCLUDED_DIRS = {"_review"}
ACOUSTID_TIMEOUT = 5
MUSICBRAINZ_TIMEOUT = 5
SECRET_SERVICE_TIMEOUT = 60
ACOUSTID_INTERVAL = 1 / 3 + 0.01
MUSICBRAINZ_INTERVAL = 1.1
RATE_LOCK_TIMEOUT = 2
MIN_ACOUSTID_SCORE = 0.90
CLEAR_SCORE_MARGIN = 0.12
MIN_TEXT_SCORE = 0.82
MIN_TEXT_MARGIN = 0.12
MIN_GENRE_VOTES = 2
MIN_GENRE_SHARE = 0.5
MAX_GENRES = 5
NOISE_TOKENS = {"official", "video", "audio", "music", "lyrics", "lyric", "visualizer", "hd", "4k"}
VERSION_PATTERNS = {
    "remaster": re.compile(r"\bremaster(?:ed|ing)?\b", re.I),
    "live": re.compile(r"\blive\b", re.I),
    "remix": re.compile(r"\bremix(?:ed)?\b", re.I),
    "acoustic": re.compile(r"\bacoustic\b", re.I),
    "instrumental": re.compile(r"\binstrumental\b", re.I),
    "edit": re.compile(r"\bedit\b", re.I),
    "version": re.compile(r"\bversion\b", re.I),
    "mix": re.compile(r"\bmix\b", re.I),
}


def safe_error_message(error: BaseException, sensitive_values: tuple[str, ...] = ()) -> str:
    """Return bounded diagnostic text with credentials, URLs, and controls removed."""
    message = str(error)
    for value in sensitive_values:
        if value:
            for form in (value, quote(value, safe=""), quote_plus(value)):
                message = message.replace(form, "[redacted]")
    message = re.sub(r"https?://\S+", "[url]", message)
    message = re.sub(
        r"(?i)\b(client(?:[_-]?key)?|api[_-]?key|apikey)=([^&\s]+)",
        r"\1=[redacted]",
        message,
    )
    message = " ".join(message.split())
    return message[:240]


class StageFailure(Exception):
    """A classified failure with a sanitized diagnostic for operational logs."""

    def __init__(
        self,
        reason: str,
        error: BaseException | None = None,
        *,
        sensitive_values: tuple[str, ...] = (),
    ):
        super().__init__(reason)
        self.reason = reason
        self.error_type = type(error).__name__ if error is not None else None
        self.error_message = safe_error_message(error, sensitive_values) if error is not None else None


class UnusableAudioError(ValueError):
    """The completed file is not a readable supported audio container."""


@dataclass
class ServiceAdapters:
    """Side-effect boundaries, injectable so decisions can be fixture-tested."""

    acoustid: Any
    musicbrainz_recording: Callable[[str, Path], dict[str, Any]]
    musicbrainz_release: Callable[[str, Path], dict[str, Any]]
    tag_reader: Callable[[Path], dict[str, str]]
    tag_writer: Callable[[Path, dict[str, list[str]]], list[str]]
    rate_limiter: Callable[[str, float, Path, Callable[[], Any]], Any]


def emit(event: str, **fields: Any) -> None:
    """Emit one safe, structured line suitable for journald and later diagnosis."""
    record = {"component": "phoenix-media-ingest", "event": event, **fields}
    print(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")), flush=True)


def normalized_words(value: str | None, *, keep_versions: bool = False) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = text.casefold()
    if not keep_versions:
        for pattern in VERSION_PATTERNS.values():
            text = pattern.sub(" ", text)
    tokens = re.findall(r"[a-z0-9]+", text)
    return " ".join(token for token in tokens if token not in NOISE_TOKENS)


def text_similarity(left: str | None, right: str | None) -> float:
    a = normalized_words(left)
    b = normalized_words(right)
    if not a or not b:
        return 0.0
    sequence = difflib.SequenceMatcher(None, a, b).ratio()
    a_words, b_words = set(a.split()), set(b.split())
    overlap = len(a_words & b_words) / max(len(a_words | b_words), 1)
    return 0.7 * sequence + 0.3 * overlap


def version_tokens(value: str | None) -> set[str]:
    text = value or ""
    return {name for name, pattern in VERSION_PATTERNS.items() if pattern.search(text)}


def metadata_similarity(candidate: dict[str, Any], fallback: dict[str, str]) -> dict[str, float]:
    artist_score = text_similarity(fallback.get("artist"), candidate.get("artist"))
    fallback_title = fallback.get("title", "")
    fallback_artist = str(fallback.get("artist", "")).strip()
    if fallback_artist:
        prefix = re.compile(rf"^\s*{re.escape(fallback_artist)}\s*[-–—:]\s*", re.I)
        fallback_title = prefix.sub("", fallback_title, count=1)
    title_score = text_similarity(fallback_title, candidate.get("title"))
    source_versions = version_tokens(fallback.get("title"))
    candidate_versions = version_tokens(candidate.get("title"))
    if not source_versions:
        version_score = 0.0
    elif source_versions == candidate_versions:
        version_score = 0.18
    elif source_versions & candidate_versions:
        version_score = 0.08
    else:
        version_score = -0.18
    return {
        "artist": round(artist_score, 4),
        "title": round(title_score, 4),
        "version": version_score,
        "total": round(min(1.0, 0.48 * artist_score + 0.52 * title_score + version_score), 4),
    }


def _candidate_fields(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return {
            "recording_id": candidate.get("recording_id") or candidate.get("id"),
            "score": float(candidate.get("score", 0.0)),
            "title": candidate.get("title") or "",
            "artist": candidate.get("artist") or "",
            "acoustid_id": candidate.get("acoustid_id") or "",
        }
    score, recording_id, title, artist = candidate[:4]
    return {
        "recording_id": recording_id,
        "score": float(score),
        "title": title or "",
        "artist": artist or "",
        "acoustid_id": "",
    }


def collapse_recording_candidates(candidates: list[Any]) -> list[dict[str, Any]]:
    """Treat repeated AcoustID rows for the same MusicBrainz recording as one identity."""
    by_recording: dict[str, dict[str, Any]] = {}
    for raw in candidates:
        candidate = _candidate_fields(raw)
        recording_id = candidate["recording_id"]
        if not recording_id:
            continue
        current = by_recording.get(recording_id)
        if current is None or candidate["score"] > current["score"]:
            by_recording[recording_id] = candidate
    return sorted(by_recording.values(), key=lambda item: (-item["score"], item["recording_id"]))


def select_candidate(
    candidates: list[Any], fallback: dict[str, str]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Require strong fingerprint evidence, then use text only to resolve close strong candidates."""
    ranked = collapse_recording_candidates(candidates)
    details: dict[str, Any] = {
        "recording_count": len(ranked),
        "candidate_scores": [
            {key: candidate[key] for key in ("recording_id", "score", "title", "artist")}
            for candidate in ranked
        ],
    }
    if not ranked:
        return None, {**details, "reason": "no_match"}
    strong = [item for item in ranked if item["score"] >= MIN_ACOUSTID_SCORE]
    if not strong:
        return None, {**details, "reason": "low_fingerprint_score"}
    if len(strong) == 1 or strong[0]["score"] - strong[1]["score"] >= CLEAR_SCORE_MARGIN:
        reason = "unique_high_score" if len(strong) == 1 else "fingerprint_margin"
        return strong[0], {**details, "reason": reason}

    text_ranked = []
    for item in strong:
        similarities = metadata_similarity(item, fallback)
        text_ranked.append((similarities["total"], item["score"], item, similarities))
    text_ranked.sort(key=lambda row: (-row[0], -row[1], row[2]["recording_id"]))
    text_report = [
        {"recording_id": row[2]["recording_id"], "fingerprint_score": row[1], **row[3]}
        for row in text_ranked
    ]
    if (
        len(text_ranked) > 1
        and text_ranked[0][0] >= MIN_TEXT_SCORE
        and text_ranked[0][0] - text_ranked[1][0] >= MIN_TEXT_MARGIN
        and text_ranked[0][3]["artist"] >= 0.70
        and text_ranked[0][3]["title"] >= 0.70
    ):
        return text_ranked[0][2], {
            **details,
            "reason": "metadata_tiebreak",
            "metadata_scores": text_report,
        }
    return None, {
        **details,
        "reason": "ambiguous_candidates",
        "metadata_scores": text_report,
    }


def _entity(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    return value if isinstance(value, dict) else payload


def artist_credit(entity: dict[str, Any]) -> tuple[str, str]:
    phrase = entity.get("artist-credit-phrase")
    credit = entity.get("artist-credit") or entity.get("artist-credit-list") or []
    artist_ids: list[str] = []
    if not phrase:
        pieces: list[str] = []
        for item in credit:
            if isinstance(item, str):
                pieces.append(item)
                continue
            artist = item.get("artist", item)
            pieces.append(item.get("name") or artist.get("name", ""))
            if artist.get("id"):
                artist_ids.append(artist["id"])
            pieces.append(item.get("joinphrase", ""))
        phrase = "".join(pieces).strip()
    for item in credit:
        if isinstance(item, dict):
            artist = item.get("artist", item)
            if artist.get("id") and artist["id"] not in artist_ids:
                artist_ids.append(artist["id"])
    return str(phrase or "").strip(), artist_ids[0] if artist_ids else ""


def _list_field(entity: dict[str, Any], *names: str) -> list[dict[str, Any]]:
    for name in names:
        value = entity.get(name)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def select_release(
    releases: list[dict[str, Any]], *, album_hint: str | None, date_hint: str | None
) -> tuple[dict[str, Any] | None, str]:
    """Select a release only from a sole option or a clear source album-title match."""
    if not releases:
        return None, "no_release_data"
    if len(releases) == 1 and not album_hint:
        return releases[0], "sole_release"
    if not album_hint:
        return None, "release_ambiguous"

    scored: list[tuple[float, float, dict[str, Any]]] = []
    for release in releases:
        title_score = text_similarity(album_hint, release.get("title"))
        date_score = 0.0
        if date_hint and release.get("date"):
            source_year = str(date_hint)[:4]
            release_year = str(release["date"])[:4]
            if source_year.isdigit() and source_year == release_year:
                date_score = 0.03
        scored.append((title_score + date_score, title_score, release))
    scored.sort(key=lambda row: (-row[0], str(row[2].get("id", ""))))
    if scored[0][1] < 0.92:
        return None, "release_hint_weak"
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.12:
        return None, "release_ambiguous"
    return scored[0][2], "album_hint"


def select_genres(genres: list[dict[str, Any]]) -> list[str]:
    """Use only MusicBrainz genre entities with positive, meaningful vote counts."""
    normalized: dict[str, int] = {}
    for genre in genres:
        name = str(genre.get("name", "")).strip()
        try:
            count = int(genre.get("count", 0))
        except (TypeError, ValueError):
            continue
        if name and count > 0:
            normalized[name] = max(count, normalized.get(name, 0))
    if not normalized:
        return []
    maximum = max(normalized.values())
    eligible = [
        (count, name) for name, count in normalized.items()
        if count >= MIN_GENRE_VOTES and count >= maximum * MIN_GENRE_SHARE
    ]
    eligible.sort(key=lambda pair: (-pair[0], pair[1].casefold()))
    return [name for _, name in eligible[:MAX_GENRES]]


def canonical_tag_values(enrichment: dict[str, Any]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for field in ("title", "artist", "date", "acoustid_id", "musicbrainz_artistid"):
        value = enrichment.get(field)
        if value:
            values[field] = [str(value)]
    recording_id = enrichment.get("musicbrainz_trackid") or enrichment.get("recording_id")
    if recording_id:
        values["musicbrainz_trackid"] = [str(recording_id)]
    genres = enrichment.get("genres") or []
    if genres:
        values["genre"] = [str(genre) for genre in genres[:MAX_GENRES]]
    release = enrichment.get("release")
    if release:
        for field in (
            "album", "albumartist", "tracknumber", "discnumber", "musicbrainz_albumid",
            "musicbrainz_albumartistid", "musicbrainz_releasetrackid",
        ):
            value = release.get(field)
            if value:
                values[field] = [str(value)]
        if release.get("date"):
            values["date"] = [str(release["date"])]
    return values


def canonical_filename(source: str | Path, artist: str, title: str) -> str:
    suffix = Path(source).suffix.lower()
    artist_part = safe_component(artist)
    title_part = safe_component(title)
    if not artist_part or not title_part:
        raise ValueError("canonical artist/title is empty")
    return f"{artist_part} - {title_part}{suffix}"


def safe_component(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", str(value)).strip().strip(".")
    value = re.sub(r"\s+", " ", value)
    return value[:180].rstrip(" .")


def available_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination
    suffix = destination.suffix
    stem = destination.name[:-len(suffix)] if suffix else destination.name
    index = 1
    while True:
        candidate = destination.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def library_destination(music_root: Path, source: Path, enrichment: dict[str, Any]) -> Path:
    artist = safe_component(enrichment["artist"])
    filename = canonical_filename(source, artist, enrichment["title"])
    release = enrichment.get("release")
    directory = music_root / artist
    if release and release.get("album"):
        directory /= safe_component(release["album"])
    return available_destination(directory / filename)


def _release_position(payload: dict[str, Any], recording_id: str) -> dict[str, str]:
    release = _entity(payload, "release")
    for medium in _list_field(release, "medium-list", "media"):
        tracks = _list_field(medium, "track-list", "tracks", "track")
        for track in tracks:
            recording = track.get("recording") or {}
            if recording.get("id") == recording_id:
                return {
                    "tracknumber": str(track.get("position") or track.get("number") or ""),
                    "discnumber": str(medium.get("position") or ""),
                    "musicbrainz_releasetrackid": str(track.get("id") or ""),
                }
    return {}


def _recording_enrichment(
    payload: dict[str, Any], recording_id: str, acoustid_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    recording = _entity(payload, "recording")
    artist, artist_id = artist_credit(recording)
    title = str(recording.get("title") or "").strip()
    if not title or not artist:
        raise ValueError("MusicBrainz recording lacks a title or artist credit")
    genres = _list_field(recording, "genres", "genre-list")
    genre_names = select_genres(genres)
    enrichment = {
        "recording_id": str(recording.get("id") or recording_id),
        "musicbrainz_trackid": str(recording.get("id") or recording_id),
        "acoustid_id": acoustid_id,
        "title": title,
        "artist": artist,
        "musicbrainz_artistid": artist_id,
        "date": str(recording.get("first-release-date") or ""),
        "genres": genre_names,
        "release": None,
    }
    return enrichment, _list_field(recording, "release-list", "releases")


def _candidate_rows(acoustid: Any, response: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = list(acoustid.parse_lookup_result(response))
    # The parser provides stable (score, recording MBID, title, artist) candidates.
    rows = [_candidate_fields(item) for item in parsed]
    result_by_recording: dict[str, list[str]] = {}
    for result in response.get("results", []):
        result_id = str(result.get("id") or "")
        for recording in result.get("recordings", []):
            if recording.get("id"):
                result_by_recording.setdefault(recording["id"], []).append(result_id)
    for row in rows:
        ids = result_by_recording.get(row["recording_id"], [])
        row["acoustid_id"] = ids[0] if ids else ""
    return rows


def default_runtime_directory() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/phoenix-media-{os.getuid()}"
    return Path(runtime) / "phoenix-media-rate-limit"


def shared_rate_limited_call(
    service: str, interval: float, state_directory: Path, call: Callable[[], Any]
) -> Any:
    """Serialize requests across worker processes and leave no persistent rate database."""
    state_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        state_directory.chmod(0o700)
    except OSError:
        pass
    lock_path = state_directory / f"{service}.lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        deadline = time.monotonic() + RATE_LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"{service} rate limiter busy")
                time.sleep(0.05)
        time.sleep(interval)
        return call()


def _musicbrainz_get(entity: str, mbid: str, state_directory: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", mbid):
        raise ValueError("invalid MusicBrainz identifier")
    includes = "artist-credits+releases+genres" if entity == "recording" else "artist-credits+media+genres"
    url = f"https://musicbrainz.org/ws/2/{entity}/{quote(mbid)}?fmt=json&inc={quote(includes, safe='+')}"
    request = Request(url, headers={"User-Agent": "PhoenixMedia/1.0 (https://musicbrainz.org/doc/MusicBrainz_API)", "Accept": "application/json"})
    try:
        response = shared_rate_limited_call(
            "musicbrainz", MUSICBRAINZ_INTERVAL, state_directory,
            lambda: urlopen(request, timeout=MUSICBRAINZ_TIMEOUT),
        )
        with response:
            data = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise StageFailure("musicbrainz_request_failure", error) from error
    if not isinstance(data, dict):
        raise StageFailure("musicbrainz_invalid_response")
    return data


def default_adapters() -> ServiceAdapters:
    import acoustid
    import mutagen

    return ServiceAdapters(
        acoustid=acoustid,
        musicbrainz_recording=lambda mbid, state: _musicbrainz_get("recording", mbid, state),
        musicbrainz_release=lambda mbid, state: _musicbrainz_get("release", mbid, state),
        tag_reader=lambda path: read_fallback_tags(path, mutagen),
        tag_writer=lambda path, values: write_mutagen_tags(path, values, mutagen),
        rate_limiter=shared_rate_limited_call,
    )


def identify_file(
    source: Path,
    fallback: dict[str, str],
    release_hints: dict[str, str],
    client_key: str,
    state_directory: Path,
    *,
    adapters: ServiceAdapters,
) -> dict[str, Any]:
    try:
        duration, fingerprint = adapters.acoustid.fingerprint_file(
            str(source), maxlength=120, force_fpcalc=True
        )
    except Exception as error:
        raise StageFailure("fingerprint_failure", error) from error
    if not fingerprint or duration <= 0:
        raise StageFailure("fingerprint_failure")
    try:
        response = adapters.rate_limiter(
            "acoustid", ACOUSTID_INTERVAL, state_directory,
            lambda: adapters.acoustid.lookup(
                client_key,
                fingerprint,
                duration,
                meta=["recordings", "releases"],
                timeout=ACOUSTID_TIMEOUT,
            ),
        )
        if not isinstance(response, dict):
            raise ValueError(f"AcoustID returned a non-object response ({type(response).__name__})")
        if response.get("status") != "ok":
            api_error = response.get("error")
            if isinstance(api_error, dict):
                error_code = safe_error_message(ValueError(str(api_error.get("code", "unknown"))))
                error_text = safe_error_message(
                    ValueError(str(api_error.get("message", "unspecified"))),
                    (client_key,),
                )
                raise ValueError(
                    f"AcoustID status={response.get('status')!r} code={error_code}: {error_text}"
                )
            status = safe_error_message(ValueError(str(response.get("status", "missing"))))
            raise ValueError(f"AcoustID returned status={status}")
        candidates = _candidate_rows(adapters.acoustid, response)
    except Exception as error:
        raise StageFailure(
            "acoustid_request_failure", error, sensitive_values=(client_key,)
        ) from error

    selected, decision = select_candidate(candidates, fallback)
    emit(
        "acoustid_result",
        file=str(source),
        fingerprint_duration=round(float(duration), 2),
        candidate_count=len(candidates),
        candidate_scores=decision.get("candidate_scores", []),
        metadata_scores=decision.get("metadata_scores", []),
        decision=decision["reason"],
    )
    if selected is None:
        return {"accepted": False, "reason": decision["reason"], "decision": decision}

    try:
        recording_payload = adapters.musicbrainz_recording(selected["recording_id"], state_directory)
        enrichment, releases = _recording_enrichment(
            recording_payload, selected["recording_id"], selected.get("acoustid_id", "")
        )
    except StageFailure:
        raise
    except Exception as error:
        raise StageFailure("musicbrainz_request_failure", error) from error

    chosen_release, release_reason = select_release(
        releases,
        album_hint=release_hints.get("album"),
        date_hint=release_hints.get("date"),
    )
    if chosen_release:
        release_id = str(chosen_release.get("id") or "")
        try:
            release_payload = adapters.musicbrainz_release(release_id, state_directory)
            release_entity = _entity(release_payload, "release")
            release_artist, release_artist_id = artist_credit(release_entity)
            release_metadata = {
                "id": release_id,
                "musicbrainz_albumid": release_id,
                "album": str(release_entity.get("title") or chosen_release.get("title") or ""),
                "albumartist": release_artist or enrichment["artist"],
                "musicbrainz_albumartistid": release_artist_id,
                "date": str(release_entity.get("date") or chosen_release.get("date") or ""),
                **_release_position(release_payload, selected["recording_id"]),
            }
            enrichment["release"] = release_metadata
        except StageFailure:
            raise
        except Exception as error:
            raise StageFailure("musicbrainz_release_request_failure", error) from error
    emit(
        "musicbrainz_result",
        file=str(source),
        recording_id=enrichment["recording_id"],
        title=enrichment["title"],
        artist=enrichment["artist"],
        release_id=(enrichment.get("release") or {}).get("id"),
        release_decision=release_reason,
        genre_count=len(enrichment["genres"]),
    )
    return {
        "accepted": True,
        "reason": "accepted",
        "acceptance_reason": decision["reason"],
        "decision": decision,
        "enrichment": enrichment,
    }


def read_fallback_tags(path: Path, mutagen_module: Any | None = None) -> dict[str, str]:
    if mutagen_module is None:
        import mutagen as mutagen_module
    # EasyID3/EasyMP4 provide portable common tags; Ogg/FLAC use native Vorbis
    # comments so MusicBrainz identifiers work on Opus and Vorbis files too.
    try:
        if path.suffix.lower() == ".mp3" or path.suffix.lower() in {".m4a", ".m4b", ".mp4"}:
            audio = mutagen_module.File(str(path), easy=True)
        else:
            audio = mutagen_module.File(str(path))
    except Exception as error:
        raise UnusableAudioError("audio container could not be read") from error
    if audio is None or getattr(audio, "info", None) is None:
        raise UnusableAudioError("unsupported or unreadable audio container")
    result: dict[str, str] = {}
    for key in ("title", "artist", "date", "purl"):
        values = (audio.tags or {}).get(key)
        if values:
            result[key] = str(values[0] if isinstance(values, (tuple, list)) else values)
    return result


def _register_mutagen_id_keys(mutagen_module: Any) -> None:
    from mutagen.easyid3 import EasyID3
    from mutagen.easymp4 import EasyMP4Tags

    id_keys = {
        "musicbrainz_trackid": "MusicBrainz Track Id",
        "musicbrainz_artistid": "MusicBrainz Artist Id",
        "musicbrainz_albumid": "MusicBrainz Album Id",
        "musicbrainz_albumartistid": "MusicBrainz Album Artist Id",
        "musicbrainz_releasetrackid": "MusicBrainz Release Track Id",
        "acoustid_id": "Acoustid Id",
    }
    for key, description in id_keys.items():
        EasyID3.RegisterTXXXKey(key, description)
        EasyMP4Tags.RegisterFreeformKey(key, description)


def write_mutagen_tags(
    path: Path, values: dict[str, list[str]], mutagen_module: Any | None = None
) -> list[str]:
    if mutagen_module is None:
        import mutagen as mutagen_module
    _register_mutagen_id_keys(mutagen_module)
    audio = mutagen_module.File(str(path), easy=True)
    if audio is None:
        raise ValueError("Mutagen does not support this audio container")
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    remove_fields = {
        "description", "comment", "synopsis", "genre", "album", "albumartist",
        "tracknumber", "discnumber", "musicbrainz_albumid", "musicbrainz_albumartistid",
        "musicbrainz_releasetrackid",
    }
    for field in remove_fields:
        try:
            if field in tags:
                del tags[field]
        except (KeyError, TypeError):
            pass
    for field, field_values in values.items():
        tags[field] = list(field_values)
    audio.save()
    return sorted(set(remove_fields) | set(values))


def read_client_key(secret_tool: str = "secret-tool") -> str | None:
    """Retrieve the Phoenix AcoustID key through Secret Service; never print it."""
    try:
        result = subprocess.run(
            [secret_tool, "lookup", "service", "phoenix-media", "key", "acoustid-client"],
            capture_output=True,
            text=True,
            timeout=SECRET_SERVICE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    key = result.stdout.strip()
    return key or None


def _review_destination(inbox: Path, source: Path) -> Path:
    relative = source.relative_to(inbox)
    destination = available_destination(inbox / "_review" / relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination


def _install_without_overwrite(temporary: Path, destination: Path) -> tuple[Path, bool]:
    collision = False
    while True:
        try:
            os.link(temporary, destination)
            temporary.unlink()
            return destination, collision
        except FileExistsError:
            collision = True
            destination = available_destination(destination)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            try:
                with temporary.open("rb") as source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
                temporary.unlink()
                return destination, collision
            except FileExistsError:
                collision = True
                destination = available_destination(destination)
            except OSError:
                try:
                    destination.unlink()
                except OSError:
                    pass
                raise


def _write_temp_copy(source: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{source.stem}.phoenix-", suffix=source.suffix, dir=source.parent)
    os.close(fd)
    temporary = Path(name)
    shutil.copy2(source, temporary)
    return temporary


def process_file(
    inbox: Path,
    source: Path,
    *,
    music_root: Path,
    state_directory: Path,
    secret_tool: str = "secret-tool",
    client_key: str | None = None,
    fallback_metadata: dict[str, str] | None = None,
    release_hints: dict[str, str] | None = None,
    adapters: ServiceAdapters | None = None,
) -> int:
    inbox = inbox.resolve()
    source = source.resolve()
    music_root = music_root.resolve()
    started = time.monotonic()
    try:
        relative = source.relative_to(inbox)
    except ValueError:
        emit("file_ignored", file=str(source), reason="outside_inbox")
        return 0
    if (
        source.suffix.lower() not in AUDIO_SUFFIXES
        or any(part in EXCLUDED_DIRS for part in relative.parts)
        or not source.is_file()
    ):
        emit("file_ignored", file=str(relative), reason="unsupported_or_excluded")
        return 0
    if source.name.startswith(".") and ".phoenix-" in source.name:
        emit("file_ignored", file=str(relative), reason="automation_output")
        return 0

    emit("file_started", file=str(relative), stage="metadata_read")
    temporary: Path | None = None
    reason = ""
    error_type: str | None = None
    error_message: str | None = None
    key: str | None = None
    try:
        services = adapters or default_adapters()
        if fallback_metadata is not None:
            fallback = fallback_metadata
        else:
            try:
                fallback = services.tag_reader(source)
            except Exception as error:
                raise StageFailure("unusable_audio", error) from error
        key = client_key if client_key is not None else read_client_key(secret_tool)
        if not key:
            raise StageFailure("missing_acoustid_client_key")
        result = identify_file(
            source,
            fallback,
            release_hints or {},
            key,
            state_directory,
            adapters=services,
        )
        if not result["accepted"]:
            reason = result["reason"]
        else:
            enrichment = result["enrichment"]
            values = canonical_tag_values(enrichment)
            try:
                temporary = _write_temp_copy(source)
            except OSError as error:
                raise StageFailure("filesystem_failure", error) from error
            try:
                tags_changed = services.tag_writer(temporary, values)
            except Exception as error:
                raise StageFailure("tag_write_failure", error) from error
            try:
                destination = library_destination(music_root, source, enrichment)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination, collided = _install_without_overwrite(temporary, destination)
                temporary = None
                if collided:
                    emit("duplicate_destination", file=str(relative), destination=str(destination))
                source.unlink()
            except OSError as error:
                raise StageFailure("filesystem_failure", error) from error
            emit(
                "file_result",
                file=str(relative),
                stage="complete",
                route="library",
                reason="accepted",
                acceptance_reason=result["acceptance_reason"],
                recording_id=enrichment["recording_id"],
                release_id=(enrichment.get("release") or {}).get("id"),
                tags_changed=tags_changed,
                old_filename=source.name,
                new_filename=destination.name,
                destination=str(destination),
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
            return 0
    except StageFailure as error:
        reason = error.reason
        error_type = error.error_type
        error_message = error.error_message
    except Exception as error:
        reason = "operational_failure"
        error_type = type(error).__name__
        error_message = safe_error_message(error, (key,) if key else ())
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    route = "review"
    destination_text = None
    try:
        if source.exists():
            destination_text = str(_review_destination(inbox, source))
        else:
            route = "library"
    except OSError as error:
        route = "inbox"
        reason = "filesystem_failure"
        error_type = type(error).__name__
        error_message = safe_error_message(error, (key,) if key else ())
    operational = reason in {
        "missing_acoustid_client_key", "fingerprint_failure", "acoustid_request_failure",
        "musicbrainz_request_failure", "musicbrainz_release_request_failure",
        "tag_write_failure", "filesystem_failure", "metadata_read_failure", "operational_failure",
    }
    error_fields = {"error_message": error_message} if error_message else {}
    emit(
        "file_result",
        file=str(relative),
        stage="complete",
        route=route,
        reason=reason,
        error_type=error_type,
        **error_fields,
        destination=destination_text,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    unusable_audio = reason == "unusable_audio"
    failed_route = operational and route not in {"review", "library"}
    return 1 if unusable_audio or failed_route else 0


def audio_files(inbox: Path) -> list[Path]:
    found: list[Path] = []
    for current, directories, filenames in os.walk(inbox, followlinks=False):
        directories[:] = sorted(
            name for name in directories
            if name not in EXCLUDED_DIRS and not (Path(current) / name).is_symlink()
        )
        for filename in filenames:
            source = Path(current) / filename
            if (
                source.suffix.lower() in AUDIO_SUFFIXES
                and not (filename.startswith(".") and ".phoenix-" in filename)
                and source.is_file()
                and not source.is_symlink()
            ):
                found.append(source)
    return sorted(found)


def decode_exec_hint(value: str) -> str | None:
    """Decode the nonempty sentinel yt-dlp uses when an optional hint is absent."""
    return None if value == "__phoenix_none__" else value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox", required=True, type=Path)
    parser.add_argument("--music-root", required=True, type=Path)
    parser.add_argument("--state-directory", type=Path, default=default_runtime_directory())
    parser.add_argument("--album-hint", default="")
    parser.add_argument("--release-date-hint", default="")
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()
    selected = args.file
    sources = [selected] if selected else audio_files(args.inbox)
    status = 0
    for source in sources:
        status = max(status, process_file(
            args.inbox,
            source,
            music_root=args.music_root,
            state_directory=args.state_directory,
            release_hints={
                "album": decode_exec_hint(args.album_hint),
                "date": decode_exec_hint(args.release_date_hint),
            },
        ))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
