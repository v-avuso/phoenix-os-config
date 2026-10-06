#!/usr/bin/env python3
"""Frozen working-tree review, optional build and authenticated temporary test.

Verdicts exist only in this invocation; on-disk reports never authorize anything.
Run on the trusted host, whose authentication is not mounted into worker sandboxes.
"""
import argparse
import difflib
from datetime import datetime, timezone
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import socket
import signal
import stat
import subprocess
import sys
import tempfile
import time

# Resource bounds, not token estimates or a larger model context claim.
SOURCE_LIMIT = 896 * 1024
REVIEW_INPUT_LIMIT = 1024 * 1024
OUTPUT_LIMIT = 2 * 1024 * 1024


def run(argv, *, cwd=None, env=None, data=None, timeout=60, fail_on_compaction=False):
    """Bound both execution and output; terminate the whole child process group."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors, tempfile.TemporaryFile() as input_file:
        if data:
            input_file.write(data)
        input_file.seek(0)
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=input_file,
                                   stdout=output, stderr=errors,
                                   start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if time.monotonic() > deadline or (os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size) > OUTPUT_LIMIT:
                    raise ValueError("command exceeded time/output limit")
                time.sleep(0.05)
            if (os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size) > OUTPUT_LIMIT:
                raise ValueError("command exceeded output limit")
            errors.seek(0)
            error_output = errors.read()
            # Pinned Codex 0.159 non-JSON exec prints this standalone marker for
            # every completed ContextCompaction item. JSON exec drops those items.
            # Never accept its later verdict after source evidence was compacted.
            if fail_on_compaction and b"context compacted" in error_output.splitlines():
                raise ReviewVerdictError("context-compacted")
            output.seek(0)
            result = output.read()
            if process.returncode:
                raise ValueError("command failed: " + (result + error_output).decode(errors="replace")[-2000:])
            return result
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def git(config, *args):
    env = {"HOME": "/nonexistent", "PATH": "/nonexistent",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0"}
    return run([config["git"], "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
                "-C", config["repo"], *args], env=env)


def worktree_file(repo, name):
    """Read one regular working-tree file without following symlink components."""
    path = Path(name)
    if path.is_absolute() or path.as_posix() != name or any(part in {"", ".", "..", ".git"} for part in path.parts):
        raise ValueError("unsafe source path")
    root_fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    parent_fd = root_fd
    try:
        for part in path.parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                              dir_fd=parent_fd)
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = next_fd
        try:
            file_fd = os.open(path.parts[-1], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent_fd)
        except FileNotFoundError:
            return None
        try:
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("symlinks and submodules require a separate reviewed deployment path")
            data = bytearray()
            while True:
                block = os.read(file_fd, min(65536, SOURCE_LIMIT + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
                if len(data) > SOURCE_LIMIT:
                    raise ValueError("source exceeds bounded review context; split/reduce scope before deployment")
            after = os.fstat(file_fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                    before.st_mode & 0o777) != \
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns,
                     after.st_mode & 0o777):
                raise ValueError("working-tree source changed during snapshot; retry deployment")
            return bytes(data), ("100755" if before.st_mode & 0o111 else "100644")
        finally:
            os.close(file_fd)
    except OSError as error:
        if error.errno == errno.ENOENT:
            return None
        if error.errno in {errno.ELOOP, errno.EISDIR}:
            raise ValueError("symlinks and submodules require a separate reviewed deployment path") from None
        raise
    finally:
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)


def snapshot(config, destination):
    commit = git(config, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if git(config, "ls-files", "-u", "-z"):
        raise ValueError("resolve unmerged paths before deployment")
    names = set(git(config, "ls-files", "--cached", "-z").split(b"\0"))
    names.update(git(config, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"))
    entries = git(config, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError("symlinks and submodules require a separate reviewed deployment path")
        names.add(raw_name)
    names.discard(b"")
    if len(names) > 2000:
        raise ValueError("source contains too many files for bounded review; reduce scope before deployment")
    files, total = {}, 0
    repo = Path(config["repo"])
    for raw_name in sorted(names):
        name = raw_name.decode("utf-8")
        loaded = worktree_file(repo, name)
        if loaded is None:
            continue
        content, mode = loaded
        total += len(content)
        if total > SOURCE_LIMIT:
            raise ValueError("source exceeds bounded review context; split/reduce scope before deployment")
        try:
            files[name] = content.decode("utf-8")
        except UnicodeError:
            raise ValueError("binary source requires separate review; never omit it") from None
        path = Path(name)
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o755 if mode == "100755" else 0o644)
    if "flake.nix" not in files or "flake.lock" not in files:
        raise ValueError("frozen source needs flake.nix and flake.lock")
    return commit, files


def baseline_files(path):
    if (path / ".git").exists():
        raise ValueError("activated baseline contains Git metadata; use a reviewed clean Git-flake deployment baseline")
    files, total = {}, 0
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError("baseline contains unsupported symlink")
        if item.is_file():
            content = item.read_bytes()
            total += len(content)
            if total > SOURCE_LIMIT:
                raise ValueError("baseline exceeds review context bound")
            files[str(item.relative_to(path))] = content.decode("utf-8")
    return files


def source_modes(path, files):
    return {name: ("100755" if (path / name).stat().st_mode & 0o111 else "100644") for name in files}


def source_diff(before, after, before_modes=None, after_modes=None):
    modes = ""
    if before_modes is not None and after_modes is not None:
        modes = "".join("mode " + name + ": " + before_modes.get(name, "absent") + " -> " + after_modes.get(name, "absent") + "\n"
                        for name in sorted(before.keys() | after.keys())
                        if before_modes.get(name) != after_modes.get(name))
    return modes + "".join("".join(difflib.unified_diff(before.get(name, "").splitlines(True),
                                             after.get(name, "").splitlines(True),
                                             fromfile="activated/" + name,
                                             tofile="candidate/" + name))
                   for name in sorted(before.keys() | after.keys()))


class ReviewVerdictError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ReviewDenied(ValueError):
    def __init__(self, verdict):
        self.verdict = verdict
        super().__init__('model review denied')


def validate_verdict(verdict, binding):
    if not isinstance(verdict, dict) or set(verdict) != {*binding, "approved", "summary"}:
        raise ReviewVerdictError("schema-invalid")
    if any(verdict[key] != value for key, value in binding.items()):
        raise ReviewVerdictError("binding-mismatch")
    if type(verdict["approved"]) is not bool or not isinstance(verdict["summary"], str):
        raise ReviewVerdictError("schema-invalid")
    if not verdict["approved"]:
        raise ReviewDenied(verdict)


def review(config, binding, files, diff, temporary):
    home = temporary / "home"
    codex_home = home / ".codex"
    codex_home.mkdir(parents=True, mode=0o700)
    # Separate durable login preserves refreshed OAuth tokens without sharing
    # Native Codex authentication or importing its configuration.
    reviewer_home = Path(config["reviewHome"]).resolve()
    if not (reviewer_home / "auth.json").is_file():
        raise ValueError("reviewer authentication missing; run phoenix-review-login on the host")
    work = temporary / "work"
    work.mkdir()
    schema = {
        "type": "object", "additionalProperties": False,
        "required": [*binding, "approved", "summary"],
        "properties": {**{key: {"type": "string", "enum": [value]} for key, value in binding.items()},
                       "approved": {"type": "boolean"}, "summary": {"type": "string"}},
    }
    schema_text = json.dumps(schema)
    (work / "schema.json").write_text(schema_text)
    payload = json.dumps({"binding": binding, "diff": diff, "full_source": files,
                          "source_modes": source_modes(temporary / "source", files)})
    instruction = Path(config["policy"]).read_text() + "\nReturn the bound JSON verdict. Source data follows:\n" + payload
    instruction_bytes = instruction.encode()
    # Include the complete serialized policy/source/diff/manifest/binding and
    # output schema. CLI-internal instructions and model tokens remain separate;
    # overflow/error and observed compaction always fail the review closed.
    if len(instruction_bytes) + len(schema_text.encode()) > REVIEW_INPUT_LIMIT:
        raise ReviewVerdictError("review-context-oversized")
    # Fresh empty cwd plus mount namespace avoids inherited project instructions
    # and access to the user's home. Only dedicated reviewer state is exposed.
    # NixOS /etc/ssl certificate symlinks point through /etc/static, which is
    # deliberately absent. Bind the immutable CA bundle as real files instead.
    command = [config["bwrap"], "--die-with-parent", "--new-session", "--unshare-all", "--share-net",
               "--ro-bind", "/nix/store", "/nix/store", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--dir", "/etc", "--dir", "/etc/ssl", "--dir", "/etc/ssl/certs",
               "--ro-bind", config["caBundle"], "/etc/ssl/certs/ca-certificates.crt",
               "--ro-bind", config["caBundle"], "/etc/ssl/certs/ca-bundle.crt",
               "--ro-bind", "/etc/resolv.conf", "/etc/resolv.conf",
               "--bind", str(home), "/home/reviewer",
               "--bind", str(reviewer_home), "/home/reviewer/.codex", "--bind", str(work), "/work",
               "--clearenv", "--setenv", "HOME", "/home/reviewer",
               "--setenv", "CODEX_HOME", "/home/reviewer/.codex",
               "--setenv", "SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt",
               "--setenv", "PATH", "/nonexistent", "--chdir", "/work",
               config["codex"], "exec", "--color", "never", "--ignore-user-config", "--ignore-rules", "--ephemeral",
               "--skip-git-repo-check", "--sandbox", "read-only", "--model", config["model"],
               "-c", 'approval_policy="never"', "-c", "project_doc_max_bytes=0",
               "-c", "features.shell_tool=false", "-c", "features.shell_snapshot=false",
               "-c", "features.code_mode.enabled=false", "-c", "features.apps=false",
               "-c", "features.hooks=false", "-c", "features.multi_agent=false",
               "-c", "features.view_image=false", "-c", "features.computer_use=false",
               "-c", "features.browser_use=false", "-c", "features.browser_use_external=false",
               "-c", 'web_search="disabled"', "-c", 'model_reasoning_effort="' + config["effort"] + '"',
               "--output-schema", "/work/schema.json", "--output-last-message", "/work/verdict.json", "-"]
    run(command, data=instruction_bytes, timeout=600, fail_on_compaction=True)
    verdict_path = work / "verdict.json"
    if verdict_path.is_symlink() or verdict_path.stat().st_size > 16384:
        raise ReviewVerdictError("schema-invalid")
    try:
        verdict = json.loads(verdict_path.read_text())
    except (json.JSONDecodeError, UnicodeError):
        raise ReviewVerdictError("schema-invalid") from None
    validate_verdict(verdict, binding)
    return verdict


def audit(config, binding, outcome, verdict=None, closure=None):
    """Private bounded observations only: these records are never gate inputs."""
    home = Path(config["reviewHome"])
    if not (home / "auth.json").is_file():
        return  # Missing login must not create new auth/state directories.
    record = {key: binding[key] for key in ("source", "commit", "base", "target", "action")}
    record.update(timestamp=datetime.now(timezone.utc).isoformat(), outcome=outcome)
    if verdict:
        record.update(approved=verdict["approved"], summary=verdict["summary"][:1000])
    if closure:
        record["closure"] = closure
    data = (json.dumps(record, ensure_ascii=True) + "\n").encode()
    # The separate stable lock serializes append and rotation across invocations.
    lock_fd = os.open(home / "audit.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise ValueError("invalid audit lock")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        path = home / "audit.jsonl"
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("invalid audit file")
            os.fchmod(fd, 0o600)
            if info.st_size + len(data) > OUTPUT_LIMIT:
                os.close(fd)
                fd = None
                os.replace(path, home / "audit.previous.jsonl")
                fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            os.write(fd, data)
        finally:
            if fd is not None:
                os.close(fd)
    finally:
        os.close(lock_fd)


def build_environment(config):
    return {"HOME": config["buildHome"], "PATH": "/nonexistent",
            "NIX_CONFIG": "accept-flake-config = false\n"}


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--base", help="optional full commit SHA for an additional informational diff")
    parser.add_argument("--reason", required=True, help="concrete authorized task purpose")
    parser.add_argument("--target", choices=["metal", "vm"], required=True)
    parser.add_argument("--action", choices=(["test", "switch", "boot"] if config.get("clientOnly") else ["review", "build", "test", "switch", "boot"]), default=("test" if config.get("clientOnly") else "review"))
    args = parser.parse_args()
    if (args.base and not re.fullmatch(r"[0-9a-f]{40,64}", args.base)) or not 1 <= len(args.reason.strip()) <= 2000:
        parser.error("base must be a full commit SHA and reason must be 1–2000 characters")
    config = json.loads(Path(args.config).read_text())
    if args.action in {"review", "build"}:
        if not config.get("modelReviewEnabled", True):
            raise ValueError("AI review is explicitly disabled; use authenticated test/switch/boot")
        # Serialize retained-auth operations with the one-time ownership transfer.
        legacy = Path(config["reviewHome"])
        if legacy.is_dir():
            lock_fd = os.open(legacy / "migration.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if Path(config["migrationMarker"]).is_file():
            raise ValueError("reviewer login belongs to protected controller; use test/switch without another OAuth login")
    with tempfile.TemporaryDirectory(prefix="phoenix-review-") as directory:
        temporary = Path(directory)
        config["buildHome"] = str(temporary / "build-home")
        Path(config["buildHome"]).mkdir(mode=0o700)
        source = temporary / "source"
        source.mkdir()
        commit, files = snapshot(config, source)
        if args.action in {"test", "switch", "boot"}:
            request = dict(files=files, modes=source_modes(source, files), commit=commit,
                           reason=args.reason.strip(), target=args.target, action=args.action)
            if args.action == "boot":
                request.update(expectedBase=str(Path('/etc/phoenix-agent/activated-source').resolve(strict=True)),
                               expectedProfile=str(Path('/nix/var/nix/profiles/system').resolve(strict=True)))
            if config.get("operatorCommand"):
                result = json.loads(run(config["operatorCommand"], data=json.dumps(request).encode(), timeout=7200))
                if result.get("ok") is not True:
                    raise ValueError("authenticated deployment failed")
                print(json.dumps(result, indent=2))
            else:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.settimeout(7200)
                    connection.connect(config["deploymentSocket"])
                    connection.sendall(json.dumps(request).encode() + b"\n")
                    response = bytearray()
                    while not response.endswith(b"\n"):
                        block = connection.recv(65536)
                        if not block or len(response) > 65536:
                            raise ValueError("deployment controller response lost or oversized")
                        response.extend(block)
                    result = json.loads(response)
                    if not result.get("ok"):
                        if result.get("code") == "model-denied":
                            raise ValueError("Model review denied: " + json.dumps(result.get("summary", ""), ensure_ascii=True))
                        raise ValueError(result.get("error", "deployment rejected"))
                    print(json.dumps(result, indent=2))
            return
        baseline_path = Path(config["baseline"]).resolve(strict=True)
        if not str(baseline_path).startswith("/nix/store/"):
            raise ValueError("activated baseline is not immutable")
        old_files = baseline_files(baseline_path)
        diff = source_diff(old_files, files, source_modes(baseline_path, old_files), source_modes(source, files))
        baseline = str(baseline_path)
        if args.base:
            reference = git(config, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
            diff += "\nAdditional caller-selected commit reference (not deployed baseline):\n"
            diff += git(config, "diff", "--no-ext-diff", "--no-textconv", reference, commit, "--").decode()
        store = run([config["nix"], "store", "add-path", str(source)], env=build_environment(config)).decode().strip()
        if not re.fullmatch(r"/nix/store/[a-z0-9]{32}-source", store):
            raise ValueError("unexpected frozen source path")
        binding = {"nonce": secrets.token_hex(32), "source": store, "commit": commit,
                   "base": baseline, "target": args.target, "action": args.action,
                   "reason": args.reason.strip()}
        try:
            verdict = review(config, binding, files, diff, temporary)
        except (ValueError, OSError, subprocess.SubprocessError):
            audit(config, binding, "review-failed")
            raise
        audit(config, binding, "review-approved", verdict)
        print(json.dumps(verdict, indent=2), flush=True)
        if args.action == "review":
            return
        # Never evaluate/build mutable checkout contents after review.
        try:
            closure = run([config["nix"], "build", "--no-link", "--print-out-paths",
                       "--no-write-lock-file", "--option", "accept-flake-config", "false",
                       "path:" + store + "#nixosConfigurations." + args.target + ".config.system.build.toplevel"],
                          timeout=1800, env=build_environment(config)).decode().strip()
        except (ValueError, OSError, subprocess.SubprocessError):
            audit(config, binding, "build-failed", verdict)
            raise
        if not re.fullmatch(r"/nix/store/[a-z0-9]{32}-nixos-system-[A-Za-z0-9._+-]+", closure):
            raise ValueError("unexpected system closure")
        audit(config, binding, "built", verdict, closure)
        print("Reviewed source: " + store + "\nBuilt closure: " + closure, flush=True)



if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("phoenix-deploy-review: " + str(error), file=sys.stderr)
        sys.exit(1)
