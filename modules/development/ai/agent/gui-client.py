"""GUI CLI bridge: version probe or app-server stdio; no native fallback."""
import os
import socket
import sys
import threading


def supported(args):
    # The pinned desktop passes feature/config flags around app-server. These
    # are deliberately ignored: host relay configuration remains declarative.
    filtered = []
    index = 0
    while index < len(args):
        if args[index] == "-c" and index + 1 < len(args):
            index += 2
            continue
        filtered.append(args[index])
        index += 1
    return filtered in (["app-server"], ["app-server", "--analytics-default-enabled"])


def main(path, version, args):
    if args == ["--version"]:
        print("codex-cli " + version)
        return 0
    if not supported(args):
        print("Sandbox GUI bridge supports app-server only; use the sandbox CLI for other commands.", file=sys.stderr)
        return 2
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.connect(path)
    except OSError:
        print("Sandbox app-server relay unavailable; no Native fallback. Inspect phoenix-agent-gui socket/service.", file=sys.stderr)
        return 1

    def input_stream():
        try:
            while chunk := os.read(0, 65536):
                connection.sendall(chunk)
            connection.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    threading.Thread(target=input_stream, daemon=True).start()
    try:
        while chunk := connection.recv(65536):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
