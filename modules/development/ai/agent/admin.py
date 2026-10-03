"""Phoenix's closed diagnostic capability set; never executes a shell."""

import json
import os
from pathlib import Path
import re
import select
import socket
import struct
import subprocess
import sys
import syslog
import time

MAX_REQUEST = 4096
MAX_OUTPUT = 512 * 1024
OPERATIONS = frozenset({
    "kernel-journal", "dmesg", "trace-summary", "trace-format", "service-status",
    "wakeup-get", "wakeup-set",
})
ADDRESS = re.compile(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]\Z")
EVENT = re.compile(r"(?:xhci-hcd|usb|kprobes)/[a-zA-Z0-9_]{1,100}\Z")


class Rejected(ValueError):
    pass


class Broker:
    def __init__(self, config):
        self.config = config
        self.sys = Path(config.get("sys_root", "/sys"))
        self.tracing = Path(config.get("tracing_root", "/sys/kernel/tracing"))

    def run(self, argv):
        # Fixed executables and argv only. No inherited pager, loader, PATH,
        # DBUS, journal namespace, locale, or other caller-controlled settings.
        with subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env={"LANG": "C", "SYSTEMD_COLORS": "0"},
        ) as process:
            output = bytearray()
            deadline = time.monotonic() + 10
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                        raise Rejected("diagnostic timed out")
                    chunk = os.read(process.stdout.fileno(), 16384)
                    if not chunk:
                        process.wait(timeout=max(0.01, deadline - time.monotonic()))
                        break
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        raise Rejected("diagnostic exceeded output limit")
            except (Rejected, subprocess.TimeoutExpired):
                process.kill()
                process.wait()
                raise Rejected("diagnostic timed out or exceeded output limit") from None
            if process.returncode:
                raise Rejected("diagnostic failed with exit status " + str(process.returncode))
            return output.decode(errors="replace")

    @staticmethod
    def read(path):
        # All input paths are constructed from fixed roots and validated
        # semantic names. Refuse a symlink on the final file as extra defense.
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            data = stream.read(MAX_OUTPUT + 1)
        if len(data) > MAX_OUTPUT:
            raise Rejected("diagnostic exceeded output limit")
        return data.decode(errors="replace")

    def trace_path(self, relative):
        path = self.tracing / relative
        # Reject aliasing via intermediate symlinks too. The live tracefs tree
        # is kernel-owned; fixture trees exercise malicious path replacements.
        if path.resolve().is_relative_to(self.tracing.resolve()):
            return path
        raise Rejected("trace path escapes tracing root")

    def wake_path(self, address):
        if not ADDRESS.fullmatch(address) or address not in self.config["wakeup_devices"]:
            raise Rejected("PCI device is not allowlisted")
        device = self.sys / "bus/pci/devices" / address
        # PCI bus entries are legitimate kernel symlinks into /sys/devices.
        if not device.resolve().is_relative_to((self.sys / "devices").resolve()):
            raise Rejected("PCI device escapes sysfs devices")
        if self.read(device / "class").strip() != "0x0c0330":
            raise Rejected("PCI device is not an xHCI controller")
        wake = device / "power/wakeup"
        if not wake.resolve().is_relative_to(device.resolve()):
            raise Rejected("wakeup path escapes PCI device")
        return wake.resolve()

    def open_wake(self, path, flags):
        # Pin each canonical /sys/devices component before opening the file;
        # neither a path alias nor a replaced intermediate symlink is followed.
        root = (self.sys / "devices").resolve()
        components = path.relative_to(root).parts
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            for component in components[:-1]:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            return os.open(components[-1], flags | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
        finally:
            os.close(fd)

    def dispatch(self, args):
        if not isinstance(args, list) or not 1 <= len(args) <= 3:
            raise Rejected("expected one semantic operation and at most two arguments")
        if not all(isinstance(arg, str) and len(arg) <= 128 for arg in args):
            raise Rejected("arguments must be short strings")
        operation, *values = args
        if operation == "kernel-journal" and len(values) <= 1:
            lines = values[0] if values else "500"
            if not re.fullmatch(r"[1-9][0-9]{0,3}", lines) or int(lines) > 2000:
                raise Rejected("lines must be 1..2000")
            return self.run([self.config["journalctl"], "--dmesg", "--boot=0",
                             "--no-pager", "--output=short-monotonic", "--lines=" + lines])
        if operation == "dmesg" and not values:
            return self.run([self.config["dmesg"], "--color=never"])
        if operation == "trace-summary" and not values:
            result = {}
            for name in ("current_tracer", "tracing_on", "kprobe_events"):
                result[name] = self.read(self.trace_path(name))
            events = self.read(self.trace_path("available_events"))
            result["available_events"] = "\n".join(
                line for line in events.splitlines() if line.startswith(("xhci-hcd:", "usb:", "kprobes:"))
            )
            return json.dumps(result, indent=2) + "\n"
        if operation == "trace-format" and len(values) == 1:
            if not EVENT.fullmatch(values[0]):
                raise Rejected("expected xhci-hcd|usb|kprobes/event_name")
            return self.read(self.trace_path("events/" + values[0] + "/format"))
        if operation == "service-status" and len(values) == 1:
            if values[0] not in self.config["status_services"]:
                raise Rejected("service is not allowlisted")
            return self.run([self.config["systemctl"], "show", "--no-pager",
                             "--property=Id,LoadState,ActiveState,SubState,Result,MainPID",
                             "--", values[0]])
        if operation == "wakeup-get" and len(values) == 1:
            return self.read(self.wake_path(values[0]))
        if operation == "wakeup-set" and len(values) == 2:
            address, state = values
            if state not in ("enabled", "disabled"):
                raise Rejected("wakeup state must be enabled or disabled")
            path = self.wake_path(address)
            before = self.read(path).strip()
            fd = self.open_wake(path, os.O_WRONLY)
            with os.fdopen(fd, "w") as stream:
                stream.write(state + "\n")
            after = self.read(path).strip()
            if after != state:
                raise Rejected("wakeup write did not take effect")
            return json.dumps({"device": address, "before": before, "after": after}) + "\n"
        raise Rejected("unknown operation or invalid argument count")


def handle(connection, broker, config):
    """One bounded request; audit only declared metadata, never arbitrary text."""
    connection.settimeout(5)
    pid, uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    started = time.monotonic()
    operation = "invalid"
    outcome = "denied"
    try:
        # SO_PEERCRED proves a kernel UID, not executable or agent identity.
        # The same-user host has this capability too; its fixed scope is the
        # boundary. Store hashes cannot distinguish malware launching Codex.
        if uid != config["client_uid"]:
            raise Rejected("caller UID is not authorized")
        with connection.makefile("rb") as stream:
            data = stream.readline(MAX_REQUEST + 1)
        if len(data) > MAX_REQUEST or not data.endswith(b"\n"):
            raise Rejected("oversized or incomplete request")
        args = json.loads(data)
        if isinstance(args, list) and args and isinstance(args[0], str) and args[0] in OPERATIONS:
            operation = args[0]
        output = broker.dispatch(args)
        if len(output.encode()) > MAX_OUTPUT:
            raise Rejected("diagnostic exceeded aggregate output limit")
        response = {"ok": True, "output": output}
        outcome = "allowed"
    except (ValueError, OSError, socket.timeout) as error:
        response = {"ok": False, "error": str(error)}
        # Avoid reflective decoder/path errors in persistent logs. Client
        # receives the useful failure, while the journal gets a fixed class.
        outcome = "timeout" if isinstance(error, (socket.timeout, TimeoutError)) else "denied"
    audit = {"uid": uid, "pid": pid, "operation": operation, "outcome": outcome,
             "elapsed_ms": int((time.monotonic() - started) * 1000)}
    if operation == "wakeup-set" and response["ok"]:
        audit["change"] = json.loads(response["output"])
    syslog.syslog(syslog.LOG_INFO, json.dumps(audit))
    try:
        connection.sendall(json.dumps(response).encode() + b"\n")
    except OSError:
        pass


def serve(config):
    broker = Broker(config)
    # systemd owns the socket; no user-selected listener or configuration.
    if os.environ.get("LISTEN_PID") != str(os.getpid()) or os.environ.get("LISTEN_FDS") != "1":
        raise SystemExit("requires exactly one systemd socket")
    listener = socket.socket(fileno=3)
    syslog.openlog("phoenix-admin")
    while True:
        connection, _ = listener.accept()
        with connection:
            handle(connection, broker, config)


def client(args, socket_path="/run/phoenix-admin/socket"):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(socket_path)
        request = json.dumps(args).encode() + b"\n"
        if len(request) > MAX_REQUEST:
            raise SystemExit("request too large")
        connection.sendall(request)
        with connection.makefile("rb") as stream:
            # JSON can expand one control/non-ASCII byte to six ASCII bytes.
            response = json.loads(stream.readline(MAX_OUTPUT * 6 + 4096))
    if not response["ok"]:
        raise SystemExit("phoenix-admin: " + response["error"])
    print(response["output"], end="")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--serve"]:
        with open(sys.argv[2]) as stream:
            serve(json.load(stream))
    elif not sys.argv[1:] or sys.argv[1] in ("-h", "--help"):
        print("phoenix-admin kernel-journal [1..2000] | dmesg | trace-summary | "
              "trace-format xhci-hcd|usb|kprobes/event | service-status UNIT | "
              "wakeup-get PCI | wakeup-set PCI enabled|disabled")
    else:
        client(sys.argv[1:])
