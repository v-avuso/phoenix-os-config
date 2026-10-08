#!/usr/bin/env python3
"""Render concise media-download results and retain structured ingest events."""

from __future__ import annotations

import argparse
import json
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
        print(f"✗ Download failed: {download_error(output, exit_code)}", file=sys.stderr)
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
        print(f"✗ Video download failed (yt-dlp exit {exit_code}).", file=sys.stderr)
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
            if event.get("vcodec") != "none" and event.get("acodec") not in {None, "none"}:
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
            if merge_start is not None and not verbose:
                render(f"Merging video and audio… {time.monotonic() - merge_start:.0f}s elapsed")
            continue
        if line is None:
            break
        output.write(line)
        output.flush()
        if line.lstrip().startswith("ERROR:"):
            errors.append(line.strip())
        if verbose:
            print(line, end="", flush=True)
            continue
        prefix, _, payload = line.strip().partition(" ")
        if prefix not in {"PHOENIX_DL", "PHOENIX_PP", "PHOENIX_PLAN"}:
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
        if prefix == "PHOENIX_PLAN":
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


def policy_args(mode: str) -> int:
    policy = json.loads(Path(os.environ.get("PHOENIX_MEDIA_CODEC_POLICY", Path(__file__).with_name("codec-policy.json"))).read_text())
    options = policy[mode]
    args = ["--format", options["format"]]
    if mode == "audio":
        args += ["--extract-audio", "--audio-format", options["codec"], "--audio-quality", options["quality"]]
    else:
        args += ["--merge-output-format", options["container"]]
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
    arguments = parser.parse_args()
    if arguments.command == "policy-args":
        return policy_args(arguments.mode)
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
