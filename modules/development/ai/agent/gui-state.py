"""One active shared-state GUI; native and contained backends remain independent."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(config, variant, command):
    if variant not in ("native", "sandbox") or not command:
        raise ValueError("Expected a fixed GUI variant and launcher command")
    history = load("history_runtime", config["historyModule"])
    settings = json.loads(Path(config["historyConfig"]).read_text())
    path = history.regular_path(config["lock"])
    history.regular_path(path.parent, directory=True).mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Shared GUI lock has unexpected ownership or type")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            owner = os.pread(fd, 16, 0).decode("ascii", errors="ignore").strip()
            label = {"native": "Native", "sandbox": "Sandboxed"}.get(owner, "Existing")
            print(f"{label} ChatGPT is running with shared state. Keep its current window, or close it normally before opening another variant. No application was closed.", file=sys.stderr)
            return 3
        os.ftruncate(fd, 0)
        os.write(fd, variant.encode())
        # This SH lock prevents a cold handoff racing GUI startup; the host
        # supervisor holds both locks even if Electron closes inherited FDs.
        history_fd = history.lifecycle_lock(settings, shared=True)
        try:
            if not history.status(settings)["active"]:
                raise ValueError("Shared desktop state requires completed cold history handoff; keep clients stopped and use codex-history-enable first")
            transport = load("gui_transport", config["transportModule"])
            # locked_transport owns/closes this duplicate; retain our own until
            # child cleanup completes, including errors before subprocess start.
            return transport.locked_transport(command, dict(os.environ), os.dup(history_fd))
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
