#!/usr/bin/env python3
"""Render concise media-download results and retain structured ingest events."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import subprocess
import threading
import queue
import time
import shutil
import uuid


COMPONENT = "phoenix-media-ingest"
OPERATIONAL_FAILURES = {
    "missing_acoustid_client_key",
    "fingerprint_failure",
    "acoustid_request_failure",
    "musicbrainz_request_failure",
    "musicbrainz_release_request_failure",
    "tag_write_failure",
    "filesystem_failure",
    "metadata_read_failure",
    "operational_failure",
}
REVIEW_LABELS = {
    "no_match": "No AcoustID match, manual review required.",
    "low_fingerprint_score": "No confident AcoustID match; manual review required",
    "ambiguous_candidates": "AcoustID match was ambiguous; manual review required",
}
FAILURE_LABELS = {
    "acoustid_request_failure": "AcoustID lookup failed",
    "missing_acoustid_client_key": "AcoustID key is unavailable",
    "fingerprint_failure": "audio fingerprinting failed",
    "musicbrainz_request_failure": "MusicBrainz lookup failed",
    "musicbrainz_release_request_failure": "MusicBrainz release lookup failed",
    "tag_write_failure": "MusicBrainz tags could not be written",
    "filesystem_failure": "the file could not be routed safely",
    "metadata_read_failure": "audio metadata could not be read",
    "operational_failure": "metadata processing failed",
}


def load_events(output: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    try:
        lines = output.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return events
    for line in lines:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(event, dict) and event.get("component") == COMPONENT:
            events.append(event)
    return events


def save_events(events: list[dict[str, object]]) -> None:
    if not events:
        return
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    log_directory = state_home / "phoenix-media"
    log_path = log_directory / "ingest.jsonl"
    try:
        log_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            for event in events:
                line = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                os.write(descriptor, (line + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
    except OSError:
        print("⚠ Could not save structured media diagnostics locally.", file=sys.stderr)


def display_path(value: object) -> str:
    path = str(value or "")
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home) :]
    return path


def basename(value: object) -> str:
    return Path(str(value or "downloaded audio")).name


def operational_message(result: dict[str, object]) -> str:
    reason = str(result.get("reason") or "operational_failure")
    message = FAILURE_LABELS.get(reason, "metadata processing failed")
    detail = str(result.get("error_message") or "").strip()
    if detail:
        # Never expose the key or internal temporary paths through the summary.
        detail = re.sub(r"(?i)(?:/tmp/)?phoenix-download\.[A-Za-z0-9._-]+(?:/[^\s]*)?", "[temporary file]", detail)
        detail = detail[:180]
        message += f": {detail}"
    return message


def download_error(output: Path, exit_code: int) -> str:
    try:
        lines = output.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    matches = [line.strip() for line in lines if line.strip().startswith("ERROR:")]
    if matches:
        message = matches[-1].removeprefix("ERROR:").strip()
        message = re.sub(r"(?i)(?:/tmp/)?phoenix-download\.[A-Za-z0-9._-]+(?:/[^\s]*)?", "[temporary file]", message)
        return message[:240]
    return f"yt-dlp exited with status {exit_code}"


def summarize(output: Path, exit_code: int) -> int:
    events = load_events(output)
    save_events(events)
    results = [event for event in events if event.get("event") == "file_result"]
    result = results[-1] if results else None

    if result and result.get("route") in {"library", "review"} and result.get("destination"):
        destination = str(result["destination"])
        filename = basename(destination)
        if result.get("route") == "library":
            print(f"✓ Downloaded: {filename}")
            print("✓ Metadata: confidently matched")
            print(f"→ Library: {display_path(str(Path(destination).parent)).rstrip(os.sep)}/")
            return exit_code

        reason = str(result.get("reason") or "")
        if reason == "unusable_audio":
            print(f"✗ Downloaded audio is unusable: {filename}", file=sys.stderr)
            print(f"→ Moved to {display_path(str(Path(destination).parent)).rstrip(os.sep)}/")
            return exit_code or 1
        print(f"✓ Downloaded: {filename}")
        if reason in OPERATIONAL_FAILURES:
            print(f"⚠ Metadata: {operational_message(result)}")
        else:
            print(f"ℹ {REVIEW_LABELS.get(reason, 'No confident match; manual review required')}")
        review_directory = str(Path(destination).parent)
        print(f"→ Review: {display_path(review_directory).rstrip(os.sep)}/")
        if exit_code != 0:
            print("✗ The downloaded file could not be processed safely.", file=sys.stderr)
        return exit_code

    if result and result.get("route") == "inbox":
        print(f"✗ Could not route the downloaded audio safely: {operational_message(result)}", file=sys.stderr)
        return exit_code or 1

    if exit_code:
        error = download_error(output, exit_code)
        stage = "Processing" if error.startswith("Postprocessing:") else "Download"
        print(f"✗ {stage} failed: {error.removeprefix('Postprocessing:').strip()}", file=sys.stderr)
        return exit_code

    if result:
        print("✗ The downloaded audio was not moved to the library or review folder.", file=sys.stderr)
        return 1
    ignored = [e for e in events if e.get("event") == "file_ignored"]
    if ignored:
        print("✗ Audio was downloaded but ingestion rejected its path or format.", file=sys.stderr)
        return 1
    print("✓ Download completed.")
    return 0


def summarize_video(result_file: Path, exit_code: int) -> int:
    try:
        reported_paths = [line.strip() for line in result_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        reported_paths = []
    if exit_code:
        error = download_error(result_file.with_name("yt-dlp.log"), exit_code)
        stage = "Processing" if error.startswith("Postprocessing:") else "Video download"
        print(f"✗ {stage} failed: {error.removeprefix('Postprocessing:').strip()}", file=sys.stderr)
        return exit_code
    if not reported_paths:
        print("ℹ No new video file was reported; any existing file was left untouched.")
        return 0
    destination = Path(reported_paths[-1])
    print(f"✓ Downloaded: {destination.name}")
    print(f"→ {display_path(str(destination.parent)).rstrip(os.sep)}/")
    return 0



class CombinedProgress:
    """Aggregate selected streams; fall back to video/audio weights of 90/10."""

    def __init__(self, *, audio_only: bool = False) -> None:
        self.audio_only = audio_only
        self.sizes: dict[str, float] = {}
        self.byte_sizes: dict[str, float] = {}
        self.fractions: dict[str, float] = {}
        self.finished: set[str] = set()

    def plan(self, formats: list[dict[str, object]] | None) -> None:
        self.__init__(audio_only=self.audio_only)
        if formats:
            sizes = {str(f["format_id"]): float(f.get("filesize") or f.get("filesize_approx") or 0)
                     for f in formats}
            self.byte_sizes = {key: size for key, size in sizes.items() if size > 0}
            self.sizes = sizes if all(size > 0 for size in sizes.values()) else {
                str(f["format_id"]): 10 if f.get("vcodec") == "none" else 90 for f in formats}


    def update(self, event: dict[str, object]) -> tuple[int, bool]:
        key = str(event.get("format_id") or ("audio" if event.get("vcodec") == "none" else "video"))
        total = event.get("total_bytes") or event.get("total_bytes_estimate") or self.byte_sizes.get(key)
        fraction = float(event.get("downloaded_bytes") or 0) / float(total) if total else 0
        if event.get("status") == "finished":
            fraction = 1
            self.finished.add(key)
        self.fractions[key] = min(1, max(0, fraction))
        if self.audio_only:
            # A single audio source may have no requested_formats plan.
            complete = event.get("status") == "finished"
        elif self.sizes:
            fraction = sum(size * self.fractions.get(k, 0) for k, size in self.sizes.items()) / sum(self.sizes.values())
            complete = self.finished.issuperset(self.sizes)
        else:
            # The single combined-stream fallback does not have a separate audio phase.
            if ((event.get("vcodec") is None and event.get("acodec") is None)
                    or (event.get("vcodec") != "none" and event.get("acodec") not in {None, "none"})):
                complete = event.get("status") == "finished"
            else:
                kind = "audio" if event.get("vcodec") == "none" else "video"
                self.fractions[kind] = self.fractions[key]
                if event.get("status") == "finished":
                    self.finished.add(kind)
                fraction = .9 * self.fractions.get("video", 0) + .1 * self.fractions.get("audio", 0)
                complete = {"audio", "video"}.issubset(self.finished)
        return (100 if complete else min(99, int(fraction * 100))), complete


def stream_attempt(command: list[str], output, *, video: bool, verbose: bool) -> tuple[int, list[str]]:
    """Render yt-dlp records and defer errors until retry policy has decided."""
    tty = sys.stdout.isatty() and os.environ.get("TERM") != "dumb"
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
    except OSError as error:
        message = f"ERROR: Could not start yt-dlp: {error}"
        output.write(message + "\n")
        return 127, [message]
    records: queue.Queue[str | None] = queue.Queue()

    def read_output() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                records.put(line)
        finally:
            records.put(None)

    threading.Thread(target=read_output, daemon=True).start()
    active = False
    merge_start = None
    analysis_start = None
    analysis_label = ""
    merge_finished = False
    progress = CombinedProgress(audio_only=not video)
    errors: list[str] = []

    def render(text: str, final: bool = False) -> None:
        nonlocal active
        if tty:
            print("\r\033[2K" + text, end="\n" if final else "", flush=True)
            active = not final
        elif final:
            print(text, flush=True)

    if not verbose:
        render("Downloading [░░░░░░░░░░] 0%")
    while True:
        try:
            line = records.get(timeout=1)
        except queue.Empty:
            if analysis_start is not None and not verbose:
                render(f"{analysis_label}… {time.monotonic() - analysis_start:.0f}s elapsed")
            elif merge_start is not None and not verbose:
                render(f"Merging video and audio… {time.monotonic() - merge_start:.0f}s elapsed")
            continue
        if line is None:
            break
        output.write(line)
        output.flush()
        if line.lstrip().startswith("ERROR:"):
            errors.append(line.strip())
        if verbose:
            if line.startswith("PHOENIX_ENCODE "):
                try:
                    event = json.loads(line.split(" ", 1)[1])
                    if event.get("status") == "diagnostic":
                        print(event.get("stdout", "") + event.get("stderr", "") + event.get("detail", ""), end="\n", flush=True)
                        continue
                except json.JSONDecodeError:
                    pass
            print(line, end="", flush=True)
            continue
        prefix, _, payload = line.strip().partition(" ")
        if prefix not in {"PHOENIX_DL", "PHOENIX_PP", "PHOENIX_PLAN", "PHOENIX_ENCODE"}:
            if line.strip().startswith('{'):
                continue
            if not video and not line.lstrip().startswith("WARNING:"):
                continue
            if line.lstrip().startswith("ERROR:"):
                continue
            if active:
                print("\r\033[2K", end="", flush=True)
                active = False
            if line.lstrip().startswith("WARNING:"):
                errors.append(line.strip())
            else:
                print(line, end="", flush=True)
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if prefix == "PHOENIX_ENCODE":
            status = event.get("status")
            encoder = event.get("encoder", "")
            percent = event.get("percent")
            if status == "diagnostic":
                continue
            if status == "original-fallback":
                analysis_start = None
                render(f"Keeping original ({'/'.join(event.get('codecs', []))}): {event['reason']}.", final=True)
            elif status in {"metadata", "artwork"}:
                analysis_start = time.monotonic()
                analysis_label = "Adding metadata" if status == "metadata" else "Adding artwork"
                render(f"{analysis_label}…")
            elif status in {"searching", "quality-validating"}:
                analysis_start = time.monotonic()
                analysis_label = "Selecting AV1 quality" if status == "searching" else "Checking VMAF"
                render(f"{analysis_label}…")
            elif status in {"search-result", "quality-result"}:
                analysis_start = None
            elif status == "finished":
                analysis_start = None
                render(f"Encoding ({encoder}) complete; finishing media…")
            elif status == "validating":
                analysis_start = time.monotonic()
                analysis_label = "Validating playback"
                render("Validating playback…")
            elif status == "fallback":
                render("NVENC unavailable for this source; using software AV1.", final=True)
            elif percent is not None:
                analysis_start = None
                blocks = percent // 10
                text = f"Encoding ({encoder}) [{'█' * blocks}{'░' * (10 - blocks)}] {percent}%"
                if event.get("eta") is not None:
                    text += f" | ETA {event['eta']:.0f}s"
                render(text)
            else:
                render(f"Encoding ({encoder})…")
        elif prefix == "PHOENIX_PLAN":
            progress.plan(event)
            merge_start = None
            merge_finished = False
        elif prefix == "PHOENIX_DL":
            percent, complete = progress.update(event)
            blocks = percent // 10
            text = f"Downloading [{'█' * blocks}{'░' * (10 - blocks)}] {percent}%"
            speed = str(event.get('_speed_str') or '').strip()
            if not complete and speed and 'Unknown' not in speed:
                text += f" | {speed}"
            render(text, final=complete)
        elif event.get("postprocessor") == "Merger":
            if event.get("status") == "started" and merge_start is None and not merge_finished:
                merge_start = time.monotonic()
                # Delay the display until the first elapsed tick; fast merges stay invisible.
            elif event.get("status") == "finished" and not merge_finished:
                elapsed = time.monotonic() - merge_start if merge_start is not None else 0
                if elapsed >= 1:
                    render(f"Merging video and audio… finished ({elapsed:.1f}s)", final=True)
                merge_start = None
                merge_finished = True
    if active:
        print("\r\033[2K", end="", flush=True)
    status = process.wait()
    assert process.stdout is not None
    process.stdout.close()
    return status, errors


RECOVERABLE_DOWNLOAD_ERROR = re.compile(
    r"HTTP Error (?:403|408|429|5\d\d)|(?:connection|read|operation) timed out|"
    r"connection (?:reset|aborted)|Temporary failure in name resolution|Remote end closed", re.I)


def run_download(command: list[str], output_path: Path, temporary_root: Path, *, video: bool, verbose: bool) -> int:
    """Three fresh extractions at most; only recognizable transport failures retry."""
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "phoenix-media/downloads"
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    diagnostic = state / f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.log"
    output_path.touch(mode=0o600)
    with output_path.open("w", encoding="utf-8") as output:
        for attempt in range(1, 4):
            staging = temporary_root / f"attempt-{attempt}"
            staging.mkdir(mode=0o700)
            attempt_command = [*command, "--paths", f"temp:{staging}"]
            output.write(f"Phoenix download attempt {attempt}/3 at {time.time():.3f}\n")
            output.write("argv: " + json.dumps(attempt_command) + "\n")
            status, errors = stream_attempt(attempt_command, output, video=video, verbose=verbose)
            retry = status != 0 and attempt < 3 and any(RECOVERABLE_DOWNLOAD_ERROR.search(e) for e in errors)
            if not retry:
                if not verbose:
                    for warning in errors:
                        if warning.startswith("WARNING:") and (status != 0 or not any(word in warning.lower() for word in ("retrying", "falling back", "player response", "some formats"))):
                            print(warning, file=sys.stderr)
                if video and status and not verbose:
                    for error in errors:
                        if error.startswith("ERROR:"):
                            print(error, file=sys.stderr)
                break
            if verbose:
                print(f"Retrying with fresh extraction in {(1, 5)[attempt - 1]}s…", flush=True)
            # Failed attempt files are disposable; diagnostic --keep-video retains them.
            if "--keep-video" not in command and "-k" not in command:
                shutil.rmtree(staging)
            time.sleep((1, 5)[attempt - 1])
    descriptor = os.open(diagnostic, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as log:
        log.write(output_path.read_text(encoding="utf-8"))
    return status


def diagnose_merge(output_path: Path, seconds: int) -> int:
    """Host-side evidence collector; only inspect this user's FFmpeg processes."""
    descriptor = os.open(output_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    deadline = time.monotonic() + seconds
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        while time.monotonic() < deadline:
            for proc in Path("/proc").iterdir():
                if not proc.name.isdecimal():
                    continue
                try:
                    if proc.stat().st_uid != os.getuid() or (proc / "comm").read_text().strip() != "ffmpeg":
                        continue
                    argv = (proc / "cmdline").read_bytes().decode(errors="replace").strip("\0").split("\0")
                    files = []
                    for fd in (proc / "fd").iterdir():
                        target = os.readlink(fd)
                        if target.startswith("/"):
                            stat = fd.stat()
                            files.append({"fd": fd.name, "path": target, "size": stat.st_size})
                    record = {"time": time.time(), "pid": int(proc.name), "argv": argv,
                              "exe": os.readlink(proc / "exe"), "stat": (proc / "stat").read_text(),
                              "status": (proc / "status").read_text(), "io": (proc / "io").read_text(),
                              "wchan": (proc / "wchan").read_text(), "files": files}
                    output.write(json.dumps(record) + "\n")
                    output.flush()
                except (OSError, PermissionError):
                    continue
            time.sleep(.5)
    return 0


def codec_policy() -> dict:
    return json.loads(Path(os.environ.get(
        "PHOENIX_MEDIA_CODEC_POLICY", Path(__file__).with_name("codec-policy.json"))).read_text())


def media_tool(name: str) -> str:
    directory = os.environ.get("PHOENIX_MEDIA_FFMPEG_DIRECTORY")
    return str(Path(directory) / name) if directory else name


def probe_media(path: Path) -> dict:
    result = subprocess.run([media_tool("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise MediaIntegrityError("FFprobe could not read media")
    return json.loads(result.stdout)


def positive_number(value: object) -> float | None:
    try:
        number = float(value)
        return number if 0 < number < float("inf") else None
    except (TypeError, ValueError):
        return None


def audio_bitrate(stream: dict, ceiling: float) -> float:
    # Never infer audio rate from aggregate container rate or extractor estimates.
    # FFprobe's per-stream bit_rate is available for e.g. AAC in MP4.
    rate = positive_number(stream.get("bit_rate"))
    return min(ceiling, rate / 1000) if rate else ceiling


def measure_audio_bitrates(path: Path, streams: list[dict]) -> None:
    """Recover average audio payload rate when a merge lost stream bit_rate."""
    missing = {s["index"] for s in streams if s.get("codec_name") != "opus"
               and not positive_number(s.get("bit_rate"))}
    if not missing:
        return
    # Matroska packet durations may be rounded; use the full timestamp span
    # rather than accumulating per-packet rounding error.
    totals = {index: [0, None, None, True] for index in missing}
    process = subprocess.Popen([media_tool("ffprobe"), "-v", "error", "-select_streams", "a",
                                "-show_entries", "packet=stream_index,size,pts_time,duration_time",
                                "-of", "compact=p=0", str(path)], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True)
    try:
        for line in process.stdout:
            fields = dict(part.split("=", 1) for part in line.strip().split("|") if "=" in part)
            index = int(fields.get("stream_index", -1))
            if index not in totals:
                continue
            size = positive_number(fields.get("size"))
            duration = positive_number(fields.get("duration_time"))
            try:
                pts = float(fields.get("pts_time", "nan"))
            except ValueError:
                pts = float("nan")
            if not size or not duration or not math.isfinite(pts):
                totals[index][3] = False
            else:
                totals[index][0] += size
                begin, end = totals[index][1:3]
                totals[index][1] = min(begin, pts) if begin is not None else pts
                totals[index][2] = max(end, pts + duration) if end is not None else pts + duration
        if process.wait() == 0:
            for stream in streams:
                size, begin, end, reliable = totals.get(stream["index"], (0, None, None, False))
                if reliable and begin is not None and end is not None and end > begin:
                    stream["bit_rate"] = size * 8 / (end - begin)
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()


NVENC_OPTIONS = ["-c:v", "av1_nvenc", "-preset", "p7", "-tune", "hq",
                 "-rc", "vbr", "-b:v", "0", "-multipass", "fullres",
                 "-rc-lookahead", "32", "-spatial-aq", "1", "-temporal-aq", "1"]
SOFTWARE_OPTIONS = ["-c:v", "libsvtav1", "-preset", "6",
                    "-svtav1-params", "lp=8"]
_NVENC_AVAILABLE = None


def nvenc_available() -> bool:
    global _NVENC_AVAILABLE
    if _NVENC_AVAILABLE is None:
        # Probe actual driver/device access, not just the compiled encoder list.
        try:
            result = subprocess.run([media_tool("ffmpeg"), "-hide_banner", "-v", "error", "-nostdin",
                                     "-f", "lavfi", "-i", "color=s=640x360:r=30",
                                     "-frames:v", "1", *NVENC_OPTIONS, "-cq", "32", "-f", "null", "-"],
                                    capture_output=True, timeout=30)
            _NVENC_AVAILABLE = result.returncode == 0
        except subprocess.TimeoutExpired:
            _NVENC_AVAILABLE = False
    return _NVENC_AVAILABLE


VIDEO_MIN_VMAF = 95
# A one-point sample margin addresses observed sample/full-score variance.
# Actual output still has to pass the independent full-score floor.
VIDEO_SEARCH_VMAF = 96
VIDEO_MAX_ENCODED_PERCENT = 100


def ab_av1_command(arguments: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if os.environ.get("PHOENIX_MEDIA_FFMPEG_DIRECTORY"):
        env["PATH"] = os.environ["PHOENIX_MEDIA_FFMPEG_DIRECTORY"] + os.pathsep + env.get("PATH", "")
    env["RUST_LOG"] = "ab_av1=debug"
    command = [os.environ.get("PHOENIX_MEDIA_AB_AV1", "ab-av1"), *arguments]
    return subprocess.run(command, env=env, capture_output=True, text=True)


class OptimizationUnavailable(RuntimeError):
    """Optional compression did not produce an acceptable candidate."""


class MediaIntegrityError(RuntimeError):
    """A downloaded or completed media file cannot be published safely."""


class EncodingError(RuntimeError):
    """Required audio conversion failed."""


def optimizer_result(arguments: list[str], emit) -> subprocess.CompletedProcess:
    try:
        result = ab_av1_command(arguments)
    except OSError as error:
        emit('PHOENIX_ENCODE ' + json.dumps({"status": "diagnostic", "detail": str(error)}))
        raise OptimizationUnavailable("optimizer could not start") from error
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "diagnostic", "stdout": result.stdout,
                                        "stderr": result.stderr, "returncode": result.returncode}))
    return result


def select_video_quality(source: Path, video: dict, gpu: bool, emit) -> float:
    options = NVENC_OPTIONS if gpu else SOFTWARE_OPTIONS
    encoder, preset = options[1], options[options.index("-preset") + 1]
    high_depth = "10" in str(video.get("pix_fmt")) or "12" in str(video.get("pix_fmt"))
    arguments = ["crf-search", "-i", str(source), "-e", encoder, "--preset", preset,
                 "--pix-format", "yuv420p10le" if high_depth else "yuv420p", "--keyint", "250",
                 "--min-vmaf", str(VIDEO_SEARCH_VMAF), "--max-encoded-percent", str(VIDEO_MAX_ENCODED_PERCENT),
                 "--min-samples", "3", "--sample-duration", "10s", "--cache", "false",
                 "--temp-dir", str(source.parent), "--vmaf", "n_threads=8", "--vmaf-fps", "0",
                 "--vmaf-scale", "none", "--enc", "fps_mode=passthrough"]
    for option, value in zip(options[::2], options[1::2]):
        if option not in ("-c:v", "-preset"):
            arguments += ["--enc", f"{option[1:]}={value}"]
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "searching", "encoder": encoder, "argv": arguments,
                                        "source_bytes": source.stat().st_size if source.exists() else None}))
    # Samples are disposable even if upstream crashes or leaves partial output.
    import tempfile
    with tempfile.TemporaryDirectory(prefix=".phoenix-search-", dir=source.parent) as temporary:
        arguments[arguments.index("--temp-dir") + 1] = temporary
        result = optimizer_result(arguments, emit)
    if result.returncode:
        reason = "quality/size constraints were not met" if "Failed to find a suitable crf" in result.stderr else "optimizer failed"
        raise OptimizationUnavailable(reason)
    # 0.11.2 has a stable human summary, not main's newer JSON search interface.
    match = re.fullmatch(r"crf ([0-9]+(?:\.[0-9]+)?) VMAF ([0-9]+(?:\.[0-9]+)?) predicted .+", result.stdout.strip())
    if not match or float(match[2]) < VIDEO_SEARCH_VMAF:
        raise OptimizationUnavailable("optimizer returned an invalid or below-target quality result")
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "search-result", "summary": result.stdout.strip()}))
    return float(match[1])


def validate_video_budget(output: Path, source: Path, emit) -> None:
    if output.stat().st_size > source.stat().st_size * VIDEO_MAX_ENCODED_PERCENT / 100:
        raise OptimizationUnavailable(f"completed output exceeds the {VIDEO_MAX_ENCODED_PERCENT}% source-size limit")
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "quality-validating", "output_bytes": output.stat().st_size}))
    result = optimizer_result(["vmaf", "--reference", str(source), "--distorted", str(output),
                               "--vmaf", "n_threads=8", "--vmaf-fps", "0", "--vmaf-scale", "none"], emit)
    score = positive_number(result.stdout.strip()) if result.returncode == 0 else None
    if score is None or score < VIDEO_MIN_VMAF:
        raise OptimizationUnavailable(f"Completed output VMAF {score if score is not None else 'unavailable'} "
                           f"is below {VIDEO_MIN_VMAF}; not published")
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "quality-result", "vmaf": score}))


def validate_media(path: Path, mode: str, source: dict, *, original: bool = False) -> None:
    media = probe_media(path)
    streams = media.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    video = [s for s in streams if s.get("codec_type") == "video"
             and not s.get("disposition", {}).get("attached_pic")]
    source_audio = [s for s in source.get("streams", []) if s.get("codec_type") == "audio"]
    source_video = [s for s in source.get("streams", []) if s.get("codec_type") == "video"
                    and not s.get("disposition", {}).get("attached_pic")]
    if (mode == "audio" and not audio) or (mode == "video" and not video):
        raise MediaIntegrityError("Output is missing its primary media stream")
    if not original:
        if any(s.get("codec_name") != "opus" for s in audio):
            raise MediaIntegrityError("Output audio is not Opus")
        if mode == "video":
            if any(s.get("codec_name") != "av1" for s in video) or len(video) != len(source_video):
                raise MediaIntegrityError("Output video is not AV1 or has missing streams")
            if len(audio) != len(source_audio):
                raise MediaIntegrityError("Output has missing audio streams")
            if "webm" not in media.get("format", {}).get("format_name", ""):
                raise MediaIntegrityError("Output container is not WebM")
            for before, after in zip(source_video, video):
                if (before.get("width"), before.get("height")) != (after.get("width"), after.get("height")):
                    raise MediaIntegrityError("Output resolution changed")
                # Preserve timestamps rather than imposing a constant output frame rate.
                from fractions import Fraction
                rates = [s.get("avg_frame_rate", "0/0") for s in (before, after)]
                if all(r not in ("0/0", "0/1") for r in rates):
                    a, b = map(lambda r: float(Fraction(r)), rates)
                    if abs(a - b) > max(.01, a * .001):
                        raise MediaIntegrityError("Output frame rate changed")
    duration = positive_number(source.get("format", {}).get("duration"))
    output_duration = positive_number(media.get("format", {}).get("duration"))
    if duration and (not output_duration or abs(duration - output_duration) > max(.25, duration * .001)):
        raise MediaIntegrityError("Output duration changed or is unavailable")
    # Decode all media before publishing, including copied streams.
    result = subprocess.run([media_tool("ffmpeg"), "-hide_banner", "-v", "error", "-xerror", "-nostdin",
                             "-i", str(path), "-map", "0:a?", "-map", "0:V?",
                             "-f", "null", "-"], capture_output=True)
    if result.returncode:
        raise MediaIntegrityError("Completed output failed playback validation")


def retain_original(source: Path, media: dict, reason: Exception, emit) -> Path:
    # A combined source keeps its real container. Matroska carrying H.264/AAC
    # must not be labelled WebM even if an extractor supplied that extension.
    streams = media.get("streams", [])
    webm_compatible = all(s.get("codec_name") in {"av1", "vp8", "vp9", "opus", "vorbis"}
                          for s in streams if s.get("codec_type") in {"audio", "video"})
    if source.suffix.lower() == ".webm" and not webm_compatible:
        destination = source.with_suffix(".mkv")
        if destination.exists():
            raise RuntimeError("Original fallback destination already exists")
        os.replace(source, destination)
        source = destination
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "original-fallback", "reason": str(reason),
                                        "codecs": [s.get("codec_name") for s in streams],
                                        "extension": source.suffix}))
    return source


def enforce_codecs(source: Path, mode: str, *, original: bool = False, emit=print,
                   prefer_gpu: bool = True) -> Path:
    media = probe_media(source)
    if original:
        validate_media(source, mode, media, original=True)
        return source
    streams = media.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if (mode == "video" and not videos) or (mode == "audio" and not audios):
        raise RuntimeError("Source is missing its primary media stream")
    destination = source.with_suffix(".webm" if mode == "video" else ".opus")
    convert_video = mode == "video" and any(s.get("codec_name") != "av1" for s in videos)
    convert_audio = any(s.get("codec_name") != "opus" for s in audios)
    if destination == source and not convert_video and not convert_audio and (mode == "video" or not videos):
        emit('PHOENIX_ENCODE ' + json.dumps({"status": "validating"}))
        validate_media(source, mode, media)
        return source
    import tempfile
    duration = positive_number(media.get("format", {}).get("duration"))
    ceiling = float(codec_policy()["audio"]["quality"].removesuffix("K"))
    measure_audio_bitrates(source, audios)
    gpu = convert_video and prefer_gpu and nvenc_available()
    if convert_video:
        # Do not let optional compression hide a genuinely corrupt download.
        emit('PHOENIX_ENCODE ' + json.dumps({"status": "validating"}))
        validate_media(source, mode, media, original=True)
        try:
            if len(videos) != 1:
                raise OptimizationUnavailable("quality search requires one moving video stream")
            quality = select_video_quality(source, videos[0], gpu, emit)
        except OptimizationUnavailable as error:
            return retain_original(source, media, error, emit)
    else:
        quality = None
    args = [media_tool("ffmpeg"), "-hide_banner", "-v", "error", "-nostdin", "-y", "-i", str(source),
            "-map_metadata", "0", "-map_chapters", "0"]
    selected = (videos if mode == "video" else []) + audios
    for stream in selected:
        args += ["-map", f"0:{stream['index']}"]
    args += ["-c", "copy"]
    for index, stream in enumerate(videos if mode == "video" else []):
        if stream.get("codec_name") != "av1":
            options = [*(NVENC_OPTIONS if gpu else SOFTWARE_OPTIONS),
                       "-cq" if gpu else "-crf", f"{quality:g}", "-g", "250"]
            # Scope every encoder option so mixed AV1/non-AV1 tracks still copy AV1.
            for option, value in zip(options[::2], options[1::2]):
                args += [option if option.endswith(":v") else option + ":v", value]
                args[-2] += f":{index}"
            high_depth = "10" in str(stream.get("pix_fmt")) or "12" in str(stream.get("pix_fmt"))
            pixel_format = ("p010le" if gpu else "yuv420p10le") if high_depth else "yuv420p"
            args += [f"-pix_fmt:v:{index}", pixel_format, f"-fps_mode:v:{index}", "passthrough"]
    for index, stream in enumerate(audios):
        if stream.get("codec_name") != "opus":
            args += [f"-c:a:{index}", "libopus", f"-b:a:{index}", f"{audio_bitrate(stream, ceiling):g}k",
                     f"-vbr:a:{index}", "on"]
    descriptor, temporary = tempfile.mkstemp(prefix=".phoenix-codecs-", suffix=destination.suffix,
                                            dir=source.parent)
    os.close(descriptor)
    staged = Path(temporary)
    args += ["-progress", "pipe:1", "-stats_period", "1", str(staged)]
    start = time.monotonic()
    encoder = "NVENC" if gpu else "SVT-AV1" if convert_video else "Opus" if convert_audio else "stream copy"
    emit('PHOENIX_ENCODE ' + json.dumps({"status": "started", "encoder": encoder, "argv": args}))
    try:
        with tempfile.TemporaryFile(mode="w+") as diagnostics:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=diagnostics, text=True)
            try:
                for line in process.stdout:
                    key, _, value = line.strip().partition("=")
                    if key == "out_time_us":
                        completed = max(0, float(value) / 1000000)
                        elapsed = time.monotonic() - start
                        event = {"status": "encoding", "encoder": encoder, "elapsed": elapsed}
                        if duration:
                            event["percent"] = min(99, int(completed / duration * 100))
                            if completed > 0 and elapsed >= 1:
                                event["eta"] = max(0, (duration - completed) * elapsed / completed)
                        emit('PHOENIX_ENCODE ' + json.dumps(event))
                if process.wait():
                    diagnostics.seek(0)
                    detail = diagnostics.read()[-800:].strip()
                    if convert_video:
                        emit('PHOENIX_ENCODE ' + json.dumps({"status": "diagnostic", "detail": detail}))
                        raise OptimizationUnavailable("AV1 encoding failed")
                    raise EncodingError("FFmpeg audio conversion failed: " + detail)
            finally:
                process.stdout.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait()
        encoding_seconds = time.monotonic() - start
        emit('PHOENIX_ENCODE ' + json.dumps({"status": "validating"}))
        validate_media(staged, mode, media)
        if convert_video:
            validate_video_budget(staged, source, emit)
        if destination != source and destination.exists():
            raise RuntimeError("Staged destination already exists")
        os.replace(staged, destination)
        emit('PHOENIX_ENCODE ' + json.dumps({"status": "finished", "encoder": encoder,
                                            "encoding_seconds": encoding_seconds,
                                            "elapsed": time.monotonic() - start}))
        return destination
    except OptimizationUnavailable as error:
        return retain_original(source, media, error, emit)
    finally:
        staged.unlink(missing_ok=True)


def policy_args(mode: str, *, original: bool = False) -> int:
    policy = codec_policy()
    args = ["--format", "bestvideo+bestaudio/best" if original and mode == "video"
            else "bestaudio/best" if original else policy[mode]["format"]]
    if mode == "video" and not original:
        args += ["--merge-output-format", policy[mode]["container"]]
    if os.environ.get("PHOENIX_MEDIA_FFMPEG_DIRECTORY"):
        args += ["--ffmpeg-location", os.environ["PHOENIX_MEDIA_FFMPEG_DIRECTORY"]]
    plugins = os.environ.get("PHOENIX_MEDIA_PLUGIN_DIRECTORY", str(Path(__file__).with_name("plugins")))
    if mode == "audio":
        # FFmpeg exposes existing Ogg pictures as video. Metadata remuxes audio
        # only; the plugin preserves/reapplies pictures after the remux.
        args += ["--postprocessor-args", "Metadata+ffmpeg_o:-map -0:v?"]
    args += ["--no-embed-metadata", "--no-embed-chapters", "--no-embed-thumbnail",
             "--plugin-dirs", plugins, "--use-postprocessor",
             f"PhoenixCodecs:mode={mode};original={str(original).lower()}", "--no-ignore-errors"]
    sys.stdout.buffer.write(b"\0".join(a.encode() for a in args) + b"\0")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    summarize_parser = commands.add_parser("summarize")
    summarize_parser.add_argument("--output", required=True, type=Path)
    summarize_parser.add_argument("--exit-code", required=True, type=int)
    video_parser = commands.add_parser("summarize-video")
    video_parser.add_argument("--result-file", required=True, type=Path)
    video_parser.add_argument("--exit-code", required=True, type=int)
    progress_parser = commands.add_parser("run-download")
    progress_parser.add_argument("--output", type=Path, required=True)
    progress_parser.add_argument("--temporary-root", type=Path, required=True)
    progress_parser.add_argument("--video", action="store_true")
    progress_parser.add_argument("--verbose", action="store_true")
    progress_parser.add_argument("argv", nargs=argparse.REMAINDER)
    diagnose_parser = commands.add_parser("diagnose-merge")
    diagnose_parser.add_argument("--output", type=Path, required=True)
    diagnose_parser.add_argument("--seconds", type=int, default=240)
    policy_parser = commands.add_parser("policy-args")
    policy_parser.add_argument("mode", choices=["audio", "video"])
    policy_parser.add_argument("--original", action="store_true")
    arguments = parser.parse_args()
    if arguments.command == "policy-args":
        return policy_args(arguments.mode, original=arguments.original)
    if arguments.command == "diagnose-merge":
        return diagnose_merge(arguments.output, arguments.seconds)
    if arguments.command == "run-download":
        argv = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        return run_download(argv, arguments.output, arguments.temporary_root,
                            video=arguments.video, verbose=arguments.verbose)
    if arguments.command == "summarize-video":
        return summarize_video(arguments.result_file, arguments.exit_code)
    return summarize(arguments.output, arguments.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
