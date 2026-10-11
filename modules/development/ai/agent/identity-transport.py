"""Fixed socket-activated launch admission; Unix rights carry the three stdio FDs."""
import array
import json
import os
from pathlib import Path
import select
import signal
import socket
import struct
import subprocess
import sys
import termios

STAGE = "configuration"
LIMIT = 32768
SIGNALS = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGWINCH}


def admit(config, request):
    if not isinstance(request, dict) or set(request) != {"args", "cwd"}:
        raise ValueError("invalid launch request")
    args, cwd = request["args"], request["cwd"]
    if not isinstance(args, list) or not all(isinstance(v, str) and len(v) <= 16384 and "\0" not in v for v in args):
        raise ValueError("invalid launch arguments")
    # No executable, provider, policy, environment or Codex configuration overrides.
    if args not in (["app-server"], ["app-server", "--analytics-default-enabled"], ["--phoenix-gui-http"], ["--phoenix-account-id"]):
        if not (not args or len(args) == 1 and not args[0].startswith("-") or
                len(args) == 2 and args[0] == "resume" and all(c in "0123456789abcdef-" for c in args[1]) and len(args[1]) == 36):
            raise ValueError("protected launch accepts a prompt, resume UUID, or fixed app-server")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or str(Path(cwd).resolve()) != cwd:
        raise ValueError("launch directory is missing or aliased")
    if not Path(cwd).is_dir() or not any(Path(cwd).is_relative_to(Path(root)) for root in config["workspaces"]):
        raise ValueError("launch directory is outside configured workspaces")
    if len(args) == 1 and args[0] != "app-server" and not args[0].startswith("-"):
        args = ["--", args[0]]
    return args, cwd


def serve(config, connection):
    global STAGE
    STAGE = "peer-authentication"
    uid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
    if uid != config["operatorUid"]:
        raise ValueError("launch peer is not the configured operator")
    STAGE = "request-admission"
    connection.settimeout(5)
    data, ancillary, flags, _ = connection.recvmsg(LIMIT, socket.CMSG_SPACE(3 * array.array("i").itemsize), socket.MSG_CMSG_CLOEXEC)
    fds = []
    try:
        for level, kind, value in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                received = array.array("i")
                received.frombytes(value[:len(value) - len(value) % received.itemsize])
                fds.extend(received)
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or len(fds) != 3:
            raise ValueError("expected exactly three stdio descriptors")
        # A bounded newline frame can span multiple stream reads.
        while b"\n" not in data and len(data) < LIMIT:
            part = connection.recv(LIMIT - len(data))
            if not part:
                raise ValueError("incomplete launch request")
            data += part
        frame, separator, controls = data.partition(b"\n")
        if not separator or len(controls) > 32 or any(number not in SIGNALS for number in controls):
            raise ValueError("invalid launch frame/control")
        args, cwd = admit(config, json.loads(frame))
        STAGE = "worker-launch"
        process = subprocess.Popen(config["command"] + args, cwd=cwd, env=config["environment"],
                                   stdin=fds[0], stdout=fds[1], stderr=fds[2], start_new_session=True)
    finally:
        for fd in fds:
            os.close(fd)
    STAGE = "worker-control"
    connection.settimeout(None)
    try:
        while process.poll() is None:
            if controls or select.select([connection], [], [], .1)[0]:
                if controls:
                    control, controls = controls[:1], controls[1:]
                else:
                    control = connection.recv(1)
                if not control:
                    break
                number = control[0]
                if number not in SIGNALS:
                    break
                os.killpg(process.pid, number)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        code = process.wait()
        connection.sendall(json.dumps({"exit": code if code >= 0 else 128 - code}).encode() + b"\n")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def client(config, args):
    global STAGE
    STAGE = "connect"
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    previous = {}
    terminal = termios.tcgetattr(0) if os.isatty(0) else None
    try:
        connection.connect(config["socket"])
        STAGE = "request-send"
        request = json.dumps({"args": args, "cwd": str(Path.cwd().resolve())}).encode() + b"\n"
        if len(request) >= LIMIT:
            raise ValueError("launch request is too large")
        frame_sent = False
        pending = set()
        def forward(number, _frame):
            if not frame_sent:
                pending.add(number)
                return
            try:
                connection.sendall(bytes([number]))
            except OSError:
                pass
        for number in SIGNALS:
            previous[number] = signal.signal(number, forward)
        sent = connection.sendmsg([request], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [0, 1, 2]))])
        connection.sendall(request[sent:])
        frame_sent = True
        for number in pending:
            forward(number, None)
        STAGE = "result"
        with connection.makefile("rb") as reply:
            result = json.loads(reply.readline(1024))
        if set(result) != {"exit"} or type(result["exit"]) is not int or not 0 <= result["exit"] <= 255:
            raise ValueError("invalid protected launch result")
        return result["exit"]
    finally:
        connection.close()
        for number, handler in previous.items():
            signal.signal(number, handler)
        if terminal is not None:
            termios.tcsetattr(0, termios.TCSANOW, terminal)


if __name__ == "__main__":
    try:
        config = json.loads(Path(sys.argv[2]).read_text())
        if sys.argv[1] == "--serve":
            with socket.socket(fileno=os.dup(0)) as connection:
                serve(config, connection)
        elif sys.argv[1] == "--client":
            raise SystemExit(client(config, sys.argv[3:]))
        else:
            raise ValueError("invalid mode")
    except (ValueError, OSError, subprocess.SubprocessError):
        category = {"peer-authentication": "peer-denied", "request-admission": "request-rejected", "worker-launch": "worker-launch-failed", "worker-control": "control-failed", "connect": "socket-unavailable", "request-send": "request-send-failed", "result": "invalid-or-lost-result"}.get(STAGE, "invalid-configuration")
        print(f"Protected agent launch failed: stage={STAGE} category={category}. Inspect the identity launch journal; Native Codex remains available.", file=sys.stderr)
        raise SystemExit(1)
