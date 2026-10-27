"""Local, on-demand controls for an unmodified Huenicorn process."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
import sources

NATIVE = "http://127.0.0.1:8215"
PANEL = "127.0.0.1:8217"


def native(path, data=None, method="GET"):
    body = None if method == "GET" else json.dumps(data).encode()
    request = urllib.request.Request(NATIVE + path, data=body, method=method,
                                    headers={"Content-Type": "application/json"})
    # Local control traffic must never go through an HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=2) as reply:
        return json.load(reply)


class Controller:
    def __init__(self, executable, default_screen=2, hyprctl="hyprctl", systemd_run="systemd-run"):
        self.executable = executable
        self.default_screen = default_screen
        self.hyprctl = hyprctl
        self.systemd_run = systemd_run
        self.source_mode = "screen"
        self.screen = None
        self.process = None
        self.level = None

    def source_state(self):
        displays = []
        selected, error = None, ""
        try:
            displays = sources.monitors(self.hyprctl)
            selected = (self.screen or sources.default_monitor(displays, self.default_screen)) if self.source_mode == "screen" else "manual"
            if selected != "manual" and selected not in {m['name'] for m in displays}:
                selected, error = None, "Selected display disconnected. Select a connected display."
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            error = "Display list unavailable or default display missing"
        return {"screens": [{"name": m["name"], "label": f"Display {i + 1} · {m.get('description', m['name'])}"}
                            for i, m in enumerate(displays)], "selected_screen": selected,
                "source_error": error}

    def set_screen(self, value):
        if not isinstance(value, str) or value not in {m['name'] for m in sources.monitors(self.hyprctl)}:
            raise ValueError("Select a connected display.")
        restart = self.running()
        if restart:
            self.stop()
        self.source_mode, self.screen = "screen", value
        if restart:
            self.start()

    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        if self.running():
            return
        config = json.loads((Path.home() / ".config/huenicorn/config.json").read_text())
        if config.get("boundBackendIP") != "127.0.0.1" or config.get("restServerPort") != 8215:
            raise ValueError("Huenicorn must bind to 127.0.0.1:8215 in its private config.")
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8215)) == 0:
                raise ValueError("Another Huenicorn instance is running. Stop it in its control page first.")
        if self.source_mode == "screen":
            displays = sources.monitors(self.hyprctl)
            output = self.screen or sources.default_monitor(displays, self.default_screen)
            if output not in {m['name'] for m in displays}:
                raise ValueError("Selected display disconnected. Select a connected display.")
            self.clear_restore_token()
            preference = {"mode": "screen", "output": output}
        else:
            preference = {"mode": "manual"}
        sources.write_preference(preference)
        environment = os.environ.copy()
        environment.update(OPENCV_FOR_THREADS_NUM="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        directory = Path.home() / ".local/state/phoenix-hue-control"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (directory / "huenicorn.log").open("ab") as log:
            # A standard desktop app scope gives the portal a Hue-only identity.
            # --scope execs the workload in this child; process ownership stays here.
            command = [self.systemd_run, "--user", "--scope", "--quiet", "--unit",
                       "app-" + sources.APP_ID + "-" + uuid.uuid4().hex, "--", self.executable]
            self.process = subprocess.Popen(command, stdout=log, stderr=log,
                                            env=environment, start_new_session=True)

    def stop(self):
        if not self.running():
            return
        # Never signal an externally managed instance or a name-matched PID.
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def channels(self):
        channels = native("/api/channels")
        active = [c for c in channels if c["active"]]
        if not active:
            raise ValueError("No active channels. Configure an edge profile in Huenicorn first.")
        return active

    def choose_screen(self):
        if not self.running():
            raise ValueError("Enable sync before choosing a screen.")
        # Upstream's documented Wayland reset: stop, remove only restoreToken,
        # restart. Never rewrite a config while its owner can still save it.
        self.stop()
        self.clear_restore_token()
        self.source_mode, self.screen = "manual", None
        self.start()

    def clear_restore_token(self):
        path = Path.home() / ".config/huenicorn/config.json"
        config = json.loads(path.read_text())
        if "restoreToken" not in config:
            return
        config.pop("restoreToken", None)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                json.dump(config, output, indent=2)
                output.write("\n")
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def set_level(self, value):
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError("Glow level must be between -1 and 1.")
        if not self.running():
            raise ValueError("Enable sync and approve screen capture before adjusting glow.")
        # Read the current area each time; channel IDs are not hardcoded to this bridge.
        for channel in self.channels():
            result = native("/api/setChannelGammaFactor/" + str(channel["channelId"]),
                            {"gammaFactor": value}, "PUT")
            if not result.get("succeeded"):
                raise ValueError("Huenicorn rejected a channel update. Retry to apply to all segments.")
        native("/api/saveProfile", None, "POST")
        self.level = value

    def state(self):
        return dict(self.sync_state(), **self.source_state())

    def sync_state(self):
        if not self.running():
            return {"enabled": False, "ready": False, "level": self.level, "message": "Sync off"}
        try:
            channels = self.channels()
            values = {round(c["gammaFactor"], 4) for c in channels}
            self.level = next(iter(values)) if len(values) == 1 else None
            return {"enabled": True, "ready": True, "level": self.level,
                    "message": "Sync on" if self.level is not None else "Sync on — segments have different levels; move slider to link them"}
        except (OSError, ValueError, KeyError):
            return {"enabled": True, "ready": False, "level": self.level,
                    "message": "Starting — choose a screen if prompted; allow a restore token to remember it"}


def handler_for(controller):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, value, content_type="application/json"):
            data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; connect-src 'self'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get("Host") == PANEL

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"error": "Invalid host"})
            if self.path == "/":
                return self.reply(200, Path(__file__).with_name("panel.html").read_text(), "text/html; charset=utf-8")
            if self.path == "/edge-test":
                return self.reply(200, Path(__file__).with_name("edge-test.html").read_text(), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self.reply(200, controller.state())
            self.reply(404, {"error": "Not found"})

        def do_POST(self):
            # JSON + an exact Origin prevents cross-site forms, fetches and DNS rebinding.
            if not self.valid_host() or self.headers.get("Origin") != "http://" + PANEL:
                return self.reply(403, {"error": "Only the local panel may change sync"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1024 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a small JSON request")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                if self.path == "/api/sync" and type(data.get("enabled")) is bool:
                    controller.start() if data["enabled"] else controller.stop()
                elif self.path == "/api/level":
                    controller.set_level(data.get("level"))
                elif self.path == "/api/screen" and data == {}:
                    controller.choose_screen()
                elif self.path == "/api/source" and set(data) == {"screen"}:
                    controller.set_screen(data["screen"])
                else:
                    raise ValueError("Unknown control")
                self.reply(200, controller.state())
            except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
                # Do not expose native responses/config contents or credentials.
                message = str(error) if isinstance(error, ValueError) else "Huenicorn is unavailable; check its local setup or try again."
                self.reply(400, {"error": message})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--huenicorn", required=True)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--default-screen", type=int, default=2)
    parser.add_argument("--hyprctl", default="hyprctl")
    parser.add_argument("--systemd-run", default="systemd-run")
    args = parser.parse_args()
    os.umask(0o077)
    if args.default_screen < 1:
        parser.error("default screen must be a positive position from the left")
    controller = Controller(args.huenicorn, args.default_screen, args.hyprctl, args.systemd_run)
    server = HTTPServer(("127.0.0.1", 8217), handler_for(controller))
    # Signal handlers unwind the server rather than calling shutdown from its own thread.
    def shutdown(*_args):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print("Hue controls: http://127.0.0.1:8217 (sync starts off)", flush=True)
    if args.open_browser:
        subprocess.Popen(["xdg-open", "http://127.0.0.1:8217/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        server.server_close()


if __name__ == "__main__":
    main()
