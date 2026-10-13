"""Phoenix's closed diagnostic capability set; never executes a shell."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import secrets
import socket
import struct
import subprocess
import sys
import syslog
import time

AUTHORIZATION_PATH = "@authorizationLibrary@"
_spec = importlib.util.spec_from_file_location('phoenix_authorization', AUTHORIZATION_PATH if AUTHORIZATION_PATH.startswith('/') else Path(__file__).parent / 'authorization/request.py')
authorization = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(authorization)

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
        self.reservations = None
        if "reservations" in config:
            settings = config["reservations"]
            spec = importlib.util.spec_from_file_location("phoenix_reservation_management", settings["adapter"])
            adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter)
            self.reservations = adapter.Management(settings)
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

    def execute_authorized(self, request, uid, pid, operator=False, reservation=None, preflight_id=None):
        installed = authorization.policy(self.config)
        result = authorization.require(request, installed, uid, pid, operator, preflight_id)
        command = request['operation']
        mapped = self.reservations is not None and command in self.config['reservations']['mapping']
        try:
            if mapped:
                if not isinstance(reservation, dict) or set(reservation) != {'generation', 'capability'} or type(reservation['generation']) is not int or not isinstance(reservation['capability'], str) or not re.fullmatch('[a-f0-9]{64}', reservation['capability']):
                    raise Rejected('mapped operation requires valid reservation')
                with self.reservations.engine.operation(uid, command=command, **reservation) as gate:
                    output = self.dispatch(authorization.diagnostic_argv(request))
                    try:
                        gate.advance_baseline()
                    except self.reservations.module.Rejected:
                        pass
            else:
                if reservation is not None:
                    raise Rejected('unused reservation is not accepted')
                output = self.dispatch(authorization.diagnostic_argv(request))
            authorization.audit('completed', result['id'], uid, pid, request, result['decision'])
            return output
        except Exception:
            authorization.audit('failed', result['id'], uid, pid, request, result['decision'], category='execution-failed')
            raise Rejected('bounded diagnostic failed') from None

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
    reason_hash = None
    try:
        # SO_PEERCRED proves a kernel UID, not executable or agent identity.
        # The same-user host has this capability too; its fixed scope is the
        # boundary. Store hashes cannot distinguish malware launching Codex.
        if uid not in {config["client_uid"], authorization.policy(config)["operatorUid"]} and not (uid == 0 and broker.reservations is not None):
            raise Rejected("caller UID is not authorized")
        with connection.makefile("rb") as stream:
            data = stream.readline(MAX_REQUEST + 1)
        if len(data) > MAX_REQUEST or not data.endswith(b"\n"):
            raise Rejected("oversized or incomplete request")
        request = json.loads(data)
        if isinstance(request, dict) and set(request) == {'authorization'}:
            response = authorization.preflight(request['authorization'], authorization.policy(config), uid, pid)
            outcome = 'preflight'
        elif isinstance(request, dict) and "reservation" in request and "args" not in request and "request" not in request and broker.reservations is not None:
            operator = uid == 0
            expected = {"reservation", "operator_uid"} if operator else {"reservation"}
            if set(request) != expected or (operator and (type(request["operator_uid"]) is not int or request["operator_uid"] != config["reservations"]["operator_uid"])):
                raise Rejected("invalid reservation envelope")
            named = request["reservation"]
            if isinstance(named, dict) and isinstance(named.get("operation"), str) and named["operation"] in {"acquire", "poll", "cancel", "renew", "release", "status", "force-unlock"}:
                operation = "reservation." + named["operation"]
            if operation == "reservation.force-unlock" and isinstance(named.get("reason"), str):
                reason_hash = hashlib.sha256(named["reason"].encode()).hexdigest()
            try:
                result = broker.reservations.dispatch(named, request["operator_uid"] if operator else uid, operator)
            except broker.reservations.module.Rejected as error:
                raise Rejected(str(error)) from None
            response = {"ok": True, "reservation": result}
            outcome = "allowed"
        else:
            if uid != config["client_uid"]:
                raise Rejected("caller UID is not authorized")
            if not isinstance(request, dict) or set(request) not in ({'args', 'reason'}, {'args', 'reason', 'task'}, {'args', 'reason', 'reservation'}, {'args', 'reason', 'task', 'reservation'}, {'request'}, {'request', 'reservation'}, {'request', 'preflightId'}, {'request', 'reservation', 'preflightId'}):
                raise Rejected('unsupported diagnostic envelope')
            named = request.get('request') if 'request' in request else authorization.diagnostic(request['args'], request['reason'], request.get('task', 'phoenix-admin'))
            # Direct legacy socket callers pass through the same installed policy.
            output = broker.execute_authorized(named, uid, pid, reservation=request.get('reservation'), preflight_id=request.get('preflightId'))
            operation = named['operation'].removeprefix('admin.')
            reason_hash = hashlib.sha256(named['reason'].strip().encode()).hexdigest()
            if len(output.encode()) > MAX_OUTPUT:
                raise Rejected("diagnostic exceeded aggregate output limit")
            response = {"ok": True, "output": output}
            outcome = "allowed"
    except (ValueError, TypeError, KeyError, OSError, socket.timeout) as error:
        response = {"ok": False, "error": str(error)}
        authorization.audit('rejected', secrets.token_hex(16), uid, pid, category='invalid-or-denied')
        outcome = "timeout" if isinstance(error, (socket.timeout, TimeoutError)) else "denied"
    audit = {"uid": uid, "pid": pid, "operation": operation, "outcome": outcome,
             "elapsed_ms": int((time.monotonic() - started) * 1000)}
    if reason_hash:
        audit["reason_sha256"] = reason_hash
    if operation == "wakeup-set" and response["ok"]:
        audit["change"] = json.loads(response["output"])
    syslog.openlog("phoenix-admin")
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


def client(args, reason, reservation=None, socket_path="/run/phoenix-admin/socket", task='phoenix-admin'):
    named = authorization.diagnostic(args, reason, task)
    client_config_path = "@authorizationClientConfig@"
    config = json.loads(Path(client_config_path).read_text()) if client_config_path.startswith('/') else None
    if config is not None:
        authorization.validate(named, authorization.policy(config))
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as preflight:
            preflight.settimeout(15)
            preflight.connect(socket_path)
            preflight.sendall(json.dumps({'authorization': named}).encode() + b'\n')
            with preflight.makefile('rb') as stream:
                decision = json.loads(stream.readline(8192))
        if not decision.get('ok'):
            raise SystemExit('phoenix-admin: authorization preflight denied')
        if decision['decision'] == 'denied':
            raise SystemExit('phoenix-admin: operation denied by installed policy')
        if decision['decision'] == 'human':
            import shlex
            host = shlex.join(['phoenix-admin', '--task', task, '--reason', reason, *args])
            if not Path('/run/wrappers/bin/pkexec').exists():
                raise SystemExit('host-authentication-required: Run on the native host: ' + host)
            print('Phoenix needs native operator authentication for ' + named['operation'] + ': ' + reason, file=sys.stderr)
            envelope = {'request': named, 'preflightId': decision['id']}
            if reservation is not None: envelope['reservation'] = reservation
            completed = subprocess.run(config['operatorCommand'], input=json.dumps(envelope).encode(), stdout=subprocess.PIPE, check=False)
            if completed.returncode:
                authorization.audit('client-authentication-failed', decision['id'], os.getuid(), os.getpid(), named, 'human', category='authentication-failed-or-cancelled', trusted=False)
                raise SystemExit('phoenix-admin: authentication failed or cancelled')
            response = json.loads(completed.stdout)
            if not response.get('ok'): raise SystemExit('phoenix-admin: bounded diagnostic denied')
            print(response['output'], end='')
            return
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(socket_path)
        envelope = {'request': named, 'preflightId': decision['id']} if config is not None else {'args': args, 'reason': reason, 'task': task}
        if reservation is not None:
            envelope["reservation"] = reservation
        request = json.dumps(envelope).encode() + b"\n"
        if len(request) > MAX_REQUEST:
            raise SystemExit("request too large")
        connection.sendall(request)
        with connection.makefile("rb") as stream:
            # JSON can expand one control/non-ASCII byte to six ASCII bytes.
            response = json.loads(stream.readline(MAX_OUTPUT * 6 + 4096))
    if not response["ok"]:
        raise SystemExit("phoenix-admin: " + response["error"])
    print(response["output"], end="")


def main():
    if sys.argv[1:2] == ["--serve"]:
        with open(sys.argv[2]) as stream:
            serve(json.load(stream))
    elif sys.argv[1:2] == ['--operator']:
        config = json.loads(Path(sys.argv[2]).read_text())
        try:
            if os.geteuid() != 0: raise Rejected('root helper required')
            uid = int(os.environ.get('PKEXEC_UID', '-1'))
            data = sys.stdin.buffer.read(MAX_REQUEST + 1)
            if len(data) > MAX_REQUEST: raise Rejected('oversized request')
            request = json.loads(data)
            if not isinstance(request, dict) or set(request) not in ({'request'}, {'request', 'reservation'}, {'request', 'preflightId'}, {'request', 'reservation', 'preflightId'}): raise Rejected('unsupported helper envelope')
            output = Broker(config).execute_authorized(request['request'], uid, os.getpid(), operator=True, reservation=request.get('reservation'), preflight_id=request.get('preflightId'))
            response = dict(ok=True, output=output)
        except Exception:
            authorization.audit('rejected', secrets.token_hex(16), locals().get('uid', -1), os.getpid(), category='invalid-or-denied')
            response = dict(ok=False, error='bounded diagnostic denied')
        print(json.dumps(response))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--task", default="phoenix-admin", help="bounded task label")
        parser.add_argument("--reservation-file")
        parser.add_argument("--reason", required=True, help="concrete authorized task purpose; do not include secrets")
        parser.add_argument("args", nargs="+", help="named operation and semantic arguments")
        args = parser.parse_args()
        try:
            authorization.text(args.reason, 300, 'nonsecret reason')
            authorization.text(args.task, 100, 'task')
        except ValueError as error:
            parser.error(str(error))
        reservation = None
        if args.reservation_file:
            adapter_path = "@reservationAdapter@"
            if adapter_path.startswith('@'):
                parser.error('reservation client adapter is unavailable')
            spec = importlib.util.spec_from_file_location('reservation_client', adapter_path)
            adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter)
            reservation = adapter.read_capability(args.reservation_file)
        client(args.args, args.reason.strip(), reservation, task=args.task)


if __name__ == '__main__':
    try:
        main()
    except (Exception, SystemExit) as error:
        if sys.argv[1:2] not in (['--serve'], ['--operator']) and not (isinstance(error, SystemExit) and error.code in (None, 0)):
            authorization.audit('client-failed', secrets.token_hex(16), os.getuid(), os.getpid(), category='local-validation-or-request-failed', trusted=False)
        raise
