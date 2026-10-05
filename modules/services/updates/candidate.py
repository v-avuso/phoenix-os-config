#!/usr/bin/env python3
"""Prepare stable update candidates in isolated Git worktrees."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import uuid

INPUTS = {
    "nixpkgs": ("NixOS", "nixpkgs", "nixos-26.05"),
    "nixpkgs-updates-fast": ("NixOS", "nixpkgs", "nixos-26.05"),
    "codex-desktop-linux": ("ilysenko", "codex-desktop-linux", "main"),
    "codex-desktop-sandbox": ("ilysenko", "codex-desktop-linux", "main"),
}
APPLICATION_INPUTS = {
    "firefox": ("nixpkgs-updates-fast",),
    # Native follows the accepted source; Sandboxed remains independently pinned.
    "codex-desktop": ("codex-desktop-linux",),
    "codex-cli": (),
}
COMMUNITY_CHECKS = {"source-and-node", "rust", "nix", "official-linux-gate"}
REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
CLI_TAG = re.compile(r"rust-v([0-9]+\.[0-9]+\.[0-9]+)\Z")
COMMUNITY_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
SOURCE_LIMIT = 768 * 1024
WIRE_LIMIT = 1024 * 1024
REASON = "Prepare a stable update candidate for protected boot review"


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


def git(exe, repo, home, *args):
    env = {"HOME": str(home), "PATH": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
    return _run([exe, "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                 "-c", "commit.gpgSign=false", "-C", str(repo), *args], env=env)


def _revision(value, field):
    if not isinstance(value, str) or not REVISION.fullmatch(value):
        raise CandidateError(field + " must be a full lowercase revision")
    return value


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


def verify_source(exe, repo, home, commit, approved_source, *, require_store=True):
    commit = _revision(commit, "approved commit")
    store_source = Path(approved_source).resolve(strict=True)
    if require_store and not str(store_source).startswith("/nix/store/"):
        raise CandidateError("approved source must be immutable in the Nix store")
    if _commit_inventory(exe, repo, home, commit) != _inventory(store_source):
        raise CandidateError("commit content does not match the protected approved source")
    return commit


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


def validate_lock_change(before, after, pins):
    if before.get("root") != after.get("root") or before.get("version") != after.get("version"):
        raise CandidateError("Nix changed lock root or schema")
    old_root = before["nodes"][before["root"]]["inputs"]
    new_root = after["nodes"][after["root"]]["inputs"]
    if old_root != new_root:
        raise CandidateError("Nix changed root input declarations")
    allowed = _closure(before, set(pins)) | _closure(after, set(pins))
    changed = {name for name in set(before["nodes"]) | set(after["nodes"])
        if before["nodes"].get(name) != after["nodes"].get(name)}
    if changed - allowed:
        raise CandidateError("unexpected lock graph changes: " + ", ".join(sorted(changed - allowed)))
    for alias, pin in pins.items():
        name = new_root[alias]
        node = after["nodes"].get(name, {})
        owner, repo, ref = INPUTS[alias]
        if node.get("locked", {}).get("rev") != pin["revision"]:
            raise CandidateError("Nix did not persist exact selected revision for " + alias)
        if node.get("locked", {}).get("owner") != owner or node.get("locked", {}).get("repo") != repo:
            raise CandidateError("Nix changed source identity for " + alias)
        if node.get("original", {}).get("ref") != ref:
            raise CandidateError("Nix changed declared branch for " + alias)


def validate_request(request):
    fields = {"version", "mainHead", "pins", "applications", "observationOk"}
    if not isinstance(request, dict) or set(request) != fields or request["version"] != 1:
        raise CandidateError("candidate request schema is invalid")
    if request["observationOk"] is not True:
        raise CandidateError("source observation failed")
    _revision(request["mainHead"], "main head")
    apps = request["applications"]
    if (not isinstance(apps, list) or not apps or len(set(apps)) != len(apps)
        or any(app not in APPLICATION_INPUTS for app in apps)):
        raise CandidateError("unknown or duplicate application identifier")
    pins = request["pins"]
    if not isinstance(pins, dict) or not pins:
        raise CandidateError("candidate request has no selected pins")
    for alias, pin in pins.items():
        if alias not in INPUTS or not isinstance(pin, dict) or set(pin) != {"revision", "days", "source"}:
            raise CandidateError("invalid pin record: " + str(alias))
        _revision(pin["revision"], alias + " revision")
        if pin["source"] != INPUTS[alias][2] or type(pin["days"]) is not int or not 0 <= pin["days"] <= 365:
            raise CandidateError("pin source or age is invalid: " + alias)
    for app in apps:
        if not set(APPLICATION_INPUTS[app]) <= pins.keys():
            raise CandidateError("missing selected input for " + app)
    return request


def _changed_paths(exe, repo, home, base, commit):
    output = git(exe, repo, home, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", base, commit)
    return {p.decode() for p in output.split(b"\0") if p}


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


def _controller(socket_path, target, commit, files, modes, timeout):
    request = {"files": files, "modes": modes, "commit": commit, "target": target,
        "action": "boot", "reason": REASON}
    body = json.dumps(request, separators=(",", ":")).encode() + b"\n"
    if len(body) > WIRE_LIMIT:
        raise CandidateError("controller request exceeds wire limit")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(timeout)
        conn.connect(socket_path)
        conn.sendall(body)
        response = bytearray()
        while not response.endswith(b"\n"):
            block = conn.recv(65536)
            if not block or len(response) + len(block) > 65536:
                raise CandidateError("controller response lost or oversized")
            response.extend(block)
    result = json.loads(response)
    if not isinstance(result, dict):
        raise CandidateError("controller response is invalid")
    return result


def prepare(config, request):
    request = validate_request(request)
    repo = Path(config["repo"]).resolve(strict=True)
    state = Path(config["state"]).resolve()
    if state == repo or repo in state.parents:
        raise CandidateError("candidate state must be outside checkout")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    nix_home = Path(config["nixHome"]).resolve()
    if nix_home == state or state not in nix_home.parents:
        raise CandidateError("Nix home must be a private subdirectory of candidate state")
    nix_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    home = state / "command-home"
    home.mkdir(mode=0o700, exist_ok=True)
    with (state / "candidate.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        exe = config["git"]
        head = git(exe, repo, home, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        if head != request["mainHead"]:
            raise CandidateError("main HEAD changed since observation")
        baseline = verify_source(exe, repo, home, config["approvedCommit"], config["approvedSource"],
                                 require_store=config.get("requireStore", True))
        if baseline != head:
            raise CandidateError("main contains commits beyond approved source")
        ident = uuid.uuid4().hex
        branch = "codex/updates/" + ident
        worktree = state / "worktrees" / ident
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git(exe, repo, home, "worktree", "add", "-b", branch, str(worktree), baseline)
        commit = None
        try:
            before = _read_lock(worktree / "flake.lock")
            for alias, pin in sorted(request["pins"].items()):
                if alias not in before["nodes"][before["root"]]["inputs"]:
                    raise CandidateError("flake input is not declared: " + alias)
                owner, source_repo, _ = INPUTS[alias]
                source = "github:%s/%s/%s" % (owner, source_repo, pin["revision"])
                _run([config["nix"], "flake", "lock", "--override-input", alias, source,
                      "--output-lock-file", "flake.lock"], cwd=worktree,
                     env={"HOME": str(nix_home), "PATH": "/nonexistent",
                          "NIX_CONFIG": "accept-flake-config = false\n"}, timeout=config.get("nixTimeout", 1800))
            after = _read_lock(worktree / "flake.lock")
            validate_lock_change(before, after, request["pins"])
            paths = _working_paths(exe, worktree, home, baseline)
            allowed_paths = {"flake.lock", *config.get("packageFiles", [])}
            if not paths or not paths <= allowed_paths:
                raise CandidateError("candidate changed files outside updater allowlist")
            git(exe, worktree, home, "add", "--", *sorted(paths))
            staged = {p.decode() for p in git(exe, worktree, home, "diff", "--cached", "--name-only", "-z").split(b"\0") if p}
            if staged != paths:
                raise CandidateError("candidate index contains unexpected paths")
            git(exe, worktree, home, "-c", "user.name=Phoenix Update Service", "-c",
                "user.email=phoenix-updates@localhost", "commit", "-m",
                "feat(updates): prepare stable package pins", "-m",
                "Prepare caller-verified eligible pins in allowlisted sources.\n\n"
                "Start from the protected activated source.\n"
                "Validation: exact selected revisions and lock graph allowlist.")
            commit = git(exe, worktree, home, "rev-parse", "HEAD").decode().strip()
            if _changed_paths(exe, worktree, home, baseline, commit) != paths:
                raise CandidateError("candidate commit contains unexpected changes")
            if git(exe, repo, home, "rev-parse", "HEAD").decode().strip() != head:
                return {"status": "pending-integration", "reason": "main-head-changed", "candidate": commit, "branch": branch}
            if _status_paths(exe, repo, home) & paths:
                return {"status": "pending-integration", "reason": "user-edits-overlap-candidate", "candidate": commit, "branch": branch}
            files, modes = _manifest(exe, worktree, home, commit)
            try:
                response = _controller(config["controllerSocket"], config["target"], commit, files, modes,
                                       config.get("controllerTimeout", 7200))
            except Exception:
                return {"status": "controller-rejected", "reason": "controller-transport-failed", "candidate": commit}
            if response.get("ok") is True and response.get("action") == "boot":
                return {"status": "staged", "candidate": commit, "branch": branch,
                        "source": response.get("source"), "action": "boot",
                        "mergeBackRequired": True}
            return {"status": "controller-rejected", "reason": "controller-denied-or-unsupported",
                    "candidate": commit, "branch": branch, "mergeBackRequired": True}
        except Exception:
            if commit is None:
                try:
                    git(exe, repo, home, "worktree", "remove", "--force", str(worktree))
                    git(exe, repo, home, "branch", "-D", branch)
                except Exception:
                    pass
            raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    state = Path(config["state"])
    try:
        request = json.loads(Path(config["requestFile"]).read_text(encoding="utf-8"))
        result = prepare(config, request)
    except Exception as exc:
        result = {"status": "failed", "reason": "candidate-preparation-failed", "detail": str(exc)[:500]}
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    dest = state / "last-result.json"
    fd, temporary = tempfile.mkstemp(prefix=".last-result.", dir=state)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(result, output, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"staged", "controller-rejected", "pending-integration"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
