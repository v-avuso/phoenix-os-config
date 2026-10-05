#!/usr/bin/env python3
"""Bounded Nix/Git utilities shared by the source-group updater.

The delayed policy prototype is preserved in Git commit ed38a0b; unused
cooldown selection and incomplete request/controller orchestration are retired.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
COMMUNITY_CHECKS = {"source-and-node", "rust", "nix", "official-linux-gate"}
CLI_TAG = re.compile(r"rust-v([0-9]+\.[0-9]+\.[0-9]+)\Z")
COMMUNITY_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SOURCE_LIMIT = 896 * 1024
WIRE_LIMIT = 1024 * 1024

def _revision(value, field):
    if not isinstance(value, str) or not REVISION.fullmatch(value):
        raise CandidateError(field + " must be a full lowercase revision")
    return value

class CandidateError(ValueError):
    pass

def _run(argv, cwd=None, env=None, timeout=60):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, start_new_session=True)
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() > deadline or os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > 2 * 1024 * 1024:
                    raise CandidateError("command timed out or exceeded output bound: " + Path(argv[0]).name)
                time.sleep(.03)
            if process.returncode:
                raise CandidateError("command failed: %s exit %s" % (Path(argv[0]).name, process.returncode))
            if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > 2 * 1024 * 1024:
                raise CandidateError("command output exceeded bound: " + Path(argv[0]).name)
            out.seek(0)
            return out.read()
        finally:
            if process.poll() is None:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()

def git_metadata(repo, home):
    """Separate command-bearing config/attributes from shared objects and refs.

    GIT_COMMON_DIR redirects config and info/attributes to our private view.
    The real per-worktree HEAD/index remain in place for normal Git coordination.
    Never copy caller config, attributes, hooks, worktree config or templates.
    """
    directory = Path(repo) / '.git'
    if directory.is_file():
        text = directory.read_text().strip()
        if not text.startswith('gitdir: '):
            raise CandidateError('unsupported Git directory marker')
        directory = (Path(repo) / text[8:]).resolve(strict=True)
    else:
        directory = directory.resolve(strict=True)
    marker = directory / 'commondir'
    common = (directory / marker.read_text().strip()).resolve(strict=True) if marker.exists() else directory
    safe_root = Path(home).resolve() / 'git-metadata'
    safe_root.mkdir(mode=0o700, exist_ok=True)
    if common.is_relative_to(safe_root):
        safe = common
    else:
        safe = safe_root / hashlib.sha256(str(common).encode()).hexdigest()
        if not safe.exists():
            safe.mkdir(mode=0o700)
            (safe / 'config').write_text('[core]\n repositoryformatversion = 0\n bare = false\n')
            (safe / 'info').mkdir()
            for name in ('objects', 'refs', 'packed-refs', 'logs'):
                (safe / name).symlink_to(common / name)
    return directory, safe


def git_env(repo, home):
    _directory, common = git_metadata(repo, home)
    return {"HOME": str(home), "PATH": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
            "GIT_COMMON_DIR": str(common), "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}


def git_command(exe, repo, home):
    directory, _common = git_metadata(repo, home)
    return [exe, '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
            '-c', 'core.attributesFile=/dev/null', '-c', 'commit.gpgSign=false',
            '--git-dir', str(directory), '--work-tree', str(repo), '-C', str(repo)]


def git(exe, repo, home, *args):
    return _run([*git_command(exe, repo, home), *args], env=git_env(repo, home))

def _inventory(path):
    files = {}
    for root, dirs, names in os.walk(path, followlinks=False):
        if any((Path(root) / name).is_symlink() for name in dirs):
            raise CandidateError("approved source contains symlinks")
        for name in names:
            item = Path(root) / name
            if item.is_symlink() or not item.is_file():
                raise CandidateError("approved source contains unsupported files")
            relative = item.relative_to(path).as_posix()
            mode = "100755" if item.stat().st_mode & 0o111 else "100644"
            files[relative] = (mode, hashlib.sha256(item.read_bytes()).hexdigest())
    return files

def _commit_inventory(exe, repo, home, commit):
    result = {}
    for entry in filter(None, git(exe, repo, home, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0")):
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise CandidateError("approved source contains symlinks or submodules")
        content = git(exe, repo, home, "cat-file", "blob", oid)
        result[name.decode()] = (mode, hashlib.sha256(content).hexdigest())
    return result

def validate_community_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {"version", "amd64", "arm64"}:
        raise CandidateError("Community payload schema changed")
    version = payload["version"]
    if not isinstance(version, str) or not COMMUNITY_VERSION.fullmatch(version):
        raise CandidateError("Community payload version is not stable")
    import base64
    for arch in ("amd64", "arm64"):
        record = payload[arch]
        if not isinstance(record, dict) or set(record) != {"repositoryPath", "sha256", "sri"}:
            raise CandidateError("Community package metadata is invalid")
        expected = "pool/main/c/chatgpt/chatgpt_%s_%s.deb" % (version, arch)
        if record["repositoryPath"] != expected or not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
            raise CandidateError("Community stable payload path or SHA-256 is invalid")
        sri = "sha256-" + base64.b64encode(bytes.fromhex(record["sha256"])).decode()
        if record["sri"] != sri:
            raise CandidateError("Community SRI does not match its SHA-256")
    return payload

def validate_community_checks(revision, result):
    revision = _revision(revision, "Community revision")
    if not isinstance(result, dict) or not isinstance(result.get("check_runs"), list):
        raise CandidateError("Community check response is malformed")
    for name in COMMUNITY_CHECKS:
        matches = [x for x in result["check_runs"] if isinstance(x, dict) and x.get("name") == name]
        if not matches:
            raise CandidateError("required Community check missing: " + name)
        for check in matches:
            if (check.get("head_sha") != revision or not isinstance(check.get("app"), dict)
                or check["app"].get("slug") != "github-actions" or check.get("status") != "completed"
                or check.get("conclusion") != "success"):
                raise CandidateError("required Community check failed or changed: " + name)

def stable_cli_release(releases):
    if not isinstance(releases, list):
        raise CandidateError("Codex CLI release list is malformed")
    from datetime import datetime
    eligible = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False:
            continue
        tag = release.get("tag_name")
        match = CLI_TAG.fullmatch(tag) if isinstance(tag, str) else None
        published = release.get("published_at")
        if not match or not isinstance(published, str):
            continue
        try:
            parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            eligible.append((parsed.timestamp(), match.group(1), release))
    return max(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None

def _read_lock(path):
    lock = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict) or not isinstance(lock.get("nodes"), dict):
        raise CandidateError("flake.lock graph is invalid")
    root = lock["nodes"].get(lock.get("root"))
    if not isinstance(root, dict) or not isinstance(root.get("inputs"), dict):
        raise CandidateError("flake.lock root is invalid")
    return lock

def _closure(lock, aliases):
    root_inputs = lock["nodes"][lock["root"]]["inputs"]
    pending = [root_inputs.get(name) for name in aliases]
    if any(not isinstance(name, str) or name not in lock["nodes"] for name in pending):
        raise CandidateError("selected input has no locked node")
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for value in lock["nodes"].get(name, {}).get("inputs", {}).values():
            if isinstance(value, str) and value in lock["nodes"]:
                pending.append(value)
    return seen

def _working_paths(exe, repo, home, base):
    output = git(exe, repo, home, "diff", "--name-only", "-z", base, "--")
    return {p.decode() for p in output.split(b"\0") if p}

def _status_paths(exe, repo, home):
    output = git(exe, repo, home, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {entry[3:].decode() for entry in output.split(b"\0") if entry}

def _manifest(exe, repo, home, commit):
    files, modes, total = {}, {}, 0
    entries = git(exe, repo, home, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0")
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode()
        if kind != "blob" or mode not in {"100644", "100755"} or name.startswith("/") or ".git" in name.split("/"):
            raise CandidateError("candidate source contains unsupported paths")
        raw = git(exe, repo, home, "cat-file", "blob", oid)
        total += len(raw)
        if total > SOURCE_LIMIT:
            raise CandidateError("candidate source exceeds controller source bound")
        try:
            files[name] = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise CandidateError("candidate source contains binary files") from None
        modes[name] = mode
    if not {"flake.nix", "flake.lock"} <= files.keys():
        raise CandidateError("candidate source misses flake files")
    return files, modes
