"""Socket-activated HTTP bridge to one fixed OpenShell worker adapter."""
import base64
import http.server
import json
import os
import select
import socket
import subprocess
import sys
import time

LIMIT = 16 * 1024 * 1024


def serve(config):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def dispatch(self):
            process = None
            started = False
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > LIMIT or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Invalid body length")
                # Socket timeout also bounds malicious partial headers/body.
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("Truncated body")
                request = {"url": self.path, "method": self.command,
                           "headers": dict(self.headers), "body": base64.b64encode(body).decode()}
                process = subprocess.Popen(
                    [config["python"], "-I", config["launcher"], config["launcher_config"], "--phoenix-gui-http"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
                    cwd=config["workdir"], env={"HOME": config["home"],
                        "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}", "PATH": config["path"]})
                process.stdin.write(json.dumps(request).encode() + b"\n")
                process.stdin.close()
                # Read nonblocking so disconnect/cancellation terminates SSH
                # even while the backend is waiting for its next SSE frame.
                os.set_blocking(process.stdout.fileno(), False)
                pending = b""
                deadline = time.monotonic() + 180
                total = 0
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([process.stdout, self.connection], [], [], 1)
                    if self.connection in ready:
                        if not self.connection.recv(1, socket.MSG_PEEK):
                            return
                        raise ValueError("Unexpected pipelined request")
                    if process.stdout not in ready:
                        continue
                    chunk = os.read(process.stdout.fileno(), 131072)
                    if not chunk:
                        raise ValueError("Worker ended without complete response")
                    pending += chunk
                    if len(pending) > 262144:
                        raise ValueError("Oversized worker frame")
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        frame = json.loads(line)
                        if not started:
                            status = frame["status"]
                            if not isinstance(status, int) or not 100 <= status <= 599:
                                raise ValueError("Invalid worker HTTP status")
                            self.send_response(status)
                            for key, value in frame["headers"].items():
                                if key in {"content-type", "cache-control", "retry-after"} and not any(c in value for c in "\r\n"):
                                    self.send_header(key, value)
                            self.send_header("Connection", "close")
                            self.end_headers()
                            started = True
                        elif frame.get("done") is True:
                            return
                        else:
                            data = base64.b64decode(frame["chunk"], validate=True)
                            total += len(data)
                            if total > LIMIT:
                                raise ValueError("Oversized worker response")
                            self.wfile.write(data)
                            self.wfile.flush()
                raise TimeoutError("Desktop backend response deadline")
            except (OSError, ValueError, KeyError, TypeError):
                if not started:
                    try:
                        self.send_error(502, "Sandbox desktop backend unavailable")
                    except OSError:
                        pass
            finally:
                self.close_connection = True
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

        do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = dispatch

    connection = socket.socket(fileno=os.dup(0))
    connection.settimeout(30)
    try:
        Handler(connection, ("local", 0), None)
    finally:
        connection.close()


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        serve(json.load(stream))
