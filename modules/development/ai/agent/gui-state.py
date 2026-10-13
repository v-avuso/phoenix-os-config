"""One active shared-state GUI; native and contained backends remain independent."""
import fcntl
import importlib.util
import json
import secrets
import re
import socket
import time
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlsplit


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def owner_record(fd):
    try:
        value = json.loads(os.pread(fd, 256, 0))
    except (ValueError, UnicodeError):
        return None
    if (not isinstance(value, dict) or value.keys() != {"variant", "nonce"}
            or value["variant"] not in ("native", "sandbox")
            or not isinstance(value["nonce"], str) or len(value["nonce"]) != 64
            or any(c not in "0123456789abcdef" for c in value["nonce"])):
        return None
    return value


def startup_link(command):
    links = [arg for arg in command if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", arg)]
    if not links:
        return None
    if (len(links) != 1 or not links[0].startswith(("codex://", "codex-browser-sidebar://"))
            or len(links[0].encode()) > 4096 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in links[0])):
        raise ValueError("Unsupported or oversized shared GUI link")
    try:
        parsed = urlsplit(links[0])
        if parsed.username is not None or parsed.password is not None:
            raise ValueError()
    except ValueError:
        raise ValueError("Unsupported shared GUI link") from None
    return links[0]


def request_owner(config, fd, owner, action, target, uri=None):
    # Recheck the fixed lock identity immediately before asking that owner.
    if owner_record(fd) != owner:
        return "changed"
    endpoint = Path(config["controlDir"]) / (owner["nonce"][:16] + ".sock")
    endpoint_info = endpoint.lstat()
    if (not stat.S_ISSOCK(endpoint_info.st_mode) or endpoint_info.st_uid != os.getuid()
            or stat.S_IMODE(endpoint_info.st_mode) != 0o600):
        return "unavailable"
    deadline = time.monotonic() + 45
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(45)
        connection.connect(str(endpoint))
        if owner_record(fd) != owner:
            return "changed"
        message = {"token": owner["nonce"], "action": action, "target": target}
        if uri is not None:
            message["uri"] = uri
        connection.sendall(json.dumps(message, ensure_ascii=False).encode() + b"\n")
        response = b""
        while not response.endswith(b"\n"):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "unavailable"
            connection.settimeout(remaining)
            chunk = connection.recv(128)
            if not chunk:
                return "unavailable"
            response += chunk
            if len(response) > 128:
                return "unavailable"
        result = json.loads(response)
        if not isinstance(result, dict) or result.keys() != {"status"}:
            return "unavailable"
        return result["status"] if result["status"] in {"handled", "kept", "closing", "busy", "denied", "unavailable"} else "unavailable"


def acquire_after_close(fd, owner, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if owner_record(fd) != owner:
            return False
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return owner_record(fd) == owner
        except BlockingIOError:
            time.sleep(0.1)
    return False


def main(config, variant, command):
    if variant not in ("native", "sandbox") or not command:
        raise ValueError("Expected a fixed GUI variant and launcher command")
    uri = startup_link(command)
    history = load("history_runtime", config["historyModule"])
    settings = json.loads(Path(config["historyConfig"]).read_text())
    path = history.regular_path(config["lock"])
    history.regular_path(path.parent, directory=True).mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("Shared GUI lock has unexpected ownership or type")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            owner = owner_record(fd)
            if config.get("controlDir") and owner:
                action = ("open-link" if uri else "new-window" if "--new-instance" in command else "activate") if owner["variant"] == variant else "switch"
                try:
                    result = request_owner(config, fd, owner, action, variant, uri if action == "open-link" else None)
                except (OSError, ValueError):
                    result = "unavailable"
                if result in {"handled", "kept"}:
                    return 0
                if result == "closing" and acquire_after_close(fd, owner):
                    pass
                else:
                    print("Current ChatGPT was kept, is still closing, or its owner changed. No variant was started or forcibly closed.", file=sys.stderr)
                    return 3
            else:
                label = {"native": "Native", "sandbox": "Sandboxed"}.get(owner["variant"] if owner else "", "Existing")
                print(f"{label} ChatGPT is running with shared state. Keep its current window, or close it normally before opening another variant. No application was closed.", file=sys.stderr)
                return 3
        token = secrets.token_hex(32)
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({"variant": variant, "nonce": token}).encode())
        # This SH lock prevents a cold handoff racing GUI startup; the host
        # supervisor holds both locks even if Electron closes inherited FDs.
        history_fd = history.lifecycle_lock(settings, shared=True)
        try:
            if not history.status(settings)["active"]:
                raise ValueError("Shared desktop state requires completed cold history handoff; keep clients stopped and use codex-history-enable first")
            transport = load("gui_transport", config["transportModule"])
            # locked_transport owns/closes this duplicate; retain our own until
            # child cleanup completes, including errors before subprocess start.
            env = dict(os.environ)
            if config.get("controlDir"):
                directory = history.regular_path(config["controlDir"], directory=True)
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                info = directory.stat()
                if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                    raise ValueError("Shared GUI control directory must be owned and private")
                env.update(PHOENIX_GUI_CONTROL_DIR=str(directory), PHOENIX_GUI_OWNER_TOKEN=token,
                           PHOENIX_GUI_VARIANT=variant)
            return transport.locked_transport(command, env, os.dup(history_fd))
        finally:
            os.close(history_fd)
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        args = sys.argv[3:]
        if args[:1] == ["--"]:
            args = args[1:]
        raise SystemExit(main(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], args))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from None
