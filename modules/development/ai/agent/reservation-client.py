"""Fixed reservation transport and strict private capability-file client."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time

OPERATIONS = {'acquire', 'poll', 'cancel', 'renew', 'release', 'status', 'force-unlock'}
MAX_REQUEST = 4096


class Failure(ValueError):
    """Non-reflective diagnostic selected by this fixed client."""
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage


def load(path):
    spec = importlib.util.spec_from_file_location('phoenix_reservation_engine', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline():
    # Same activated-source/profile observation as deployment; include current
    # runtime too, so temporary activation cannot leave a matching boot profile.
    paths = {'source': '/etc/phoenix-agent/activated-source',
             'runtime': '/run/current-system', 'profile': '/nix/var/nix/profiles/system'}
    result = {key: str(Path(path).resolve(strict=True)) for key, path in paths.items()}
    result['profileSource'] = str((Path(result['profile']) / 'etc/phoenix-agent/activated-source').resolve(strict=True))
    if any(not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+', value) for value in result.values()):
        raise ValueError('reservation baseline unavailable')
    return json.dumps(result, sort_keys=True, separators=(',', ':'))


class Management:
    def __init__(self, config):
        self.config = config
        self.module = load(config['engine'])
        self.engine = self.module.Engine(config['state'], baseline=baseline,
                                        mapping=config['mapping'], **config['bounds'])

    def dispatch(self, request, uid, operator=False):
        if not isinstance(request, dict) or not isinstance(request.get('operation'), str) or request['operation'] not in OPERATIONS:
            raise ValueError('invalid reservation operation')
        operation = request['operation']
        fields = {'status': set(), 'acquire': {'task', 'command', 'baseline'},
                  'renew': {'generation', 'capability', 'seconds'},
                  'force-unlock': {'generation', 'reason'}}.get(operation, {'generation', 'capability'})
        if set(request) != fields | {'operation'}:
            raise ValueError('invalid reservation fields')
        if 'generation' in fields and (type(request['generation']) is not int or request['generation'] < 1):
            raise ValueError('invalid generation')
        if 'capability' in fields and (not isinstance(request['capability'], str) or
                                      not re.fullmatch('[a-f0-9]{64}', request['capability'])):
            raise ValueError('invalid capability')
        if operation == 'status':
            result = self.engine.status()
            result['baseline'] = baseline()
            result['mapping'] = self.config['mapping']
            result['bounds'] = self.config['bounds']
            return result
        if operation == 'acquire':
            if not isinstance(request['baseline'], str) or len(request['baseline']) > 2048:
                raise ValueError('invalid baseline')
            return self.engine.acquire(uid, request['task'], request['command'], request['baseline'])
        if operation == 'force-unlock':
            if not operator:
                raise ValueError('force unlock requires authenticated operator')
            self.engine.force_unlock(request['generation'], request['reason'])
            return {'generation': request['generation'], 'revoked': True}
        args = (uid, request['generation'], request['capability'])
        if operation == 'renew':
            if type(request['seconds']) is not int:
                raise ValueError('invalid renewal seconds')
            return self.engine.renew(*args, seconds=request['seconds'])
        return getattr(self.engine, operation)(*args) or {'generation': request['generation']}


def exchange(config, request, operator_uid=None):
    envelope = {'reservation': request}
    if operator_uid is not None:
        envelope['operator_uid'] = operator_uid
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(config['socket'])
        data = json.dumps(envelope).encode() + b'\n'
        if len(data) > MAX_REQUEST:
            raise ValueError('reservation request too large')
        connection.sendall(data)
        with connection.makefile('rb') as stream:
            response = json.loads(stream.readline(1024 * 1024))
    if not isinstance(response, dict):
        raise Failure('server', 'invalid broker response')
    if not response.get('ok'):
        errors = {
            'baseline changed; resubmit acquisition': 'baseline changed; reacquire using current server status',
            'owner or baseline changed': 'ownership or baseline changed; inspect status and reacquire',
            'invalid or stale reservation': 'capability is invalid or expired; inspect status and reacquire',
            'reservation queue full': 'reservation queue full; retry after existing tickets complete',
            'owner generation changed': 'recovery generation changed; inspect status before retry',
            'renewal bound exceeded': 'renewal exceeds configured limit',
        }
        error = response.get('error')
        raise Failure('server', errors.get(error, 'reservation request denied; inspect status and request fields') if isinstance(error, str) else 'invalid broker response')
    return response['reservation']


def private_file(path, uid, write=False):
    # O_EXCL avoids clobbering a previously acquired capability, even on errors.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        os.close(fd)
        raise Failure('capability-file', 'requires caller-owned regular 0600 file with one link')
    return fd


def read_capability(path):
    with os.fdopen(private_file(path, os.getuid()), 'r') as stream:
        data = stream.read(4097)
    if len(data) > 4096:
        raise ValueError('capability file too large')
    value = json.loads(data)
    if not isinstance(value, dict) or set(value) != {'generation', 'capability'} or type(value['generation']) is not int or value['generation'] < 1 or not isinstance(value['capability'], str) or not re.fullmatch('[a-f0-9]{64}', value['capability']):
        raise ValueError('invalid capability file')
    return value


def authenticated(config, recovery=False):
    if os.geteuid() != 0 or os.environ.get('PKEXEC_UID') != str(config['operator_uid']):
        raise Failure('authentication', 'fixed helper requires root and authenticated configured operator')
    # No filepath, argv, execution, config or environment override in the wire API.
    data = sys.stdin.buffer.readline(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST or not data.endswith(b'\n') or sys.stdin.buffer.read(1):
        raise ValueError('invalid operator request')
    request = json.loads(data)
    if not isinstance(request, dict) or (request.get('operation') == 'force-unlock') != recovery:
        raise ValueError('wrong fixed operator entry point')
    if isinstance(request, dict) and request.get('operation') == 'acquire':
        if set(request) != {'operation', 'task', 'command', 'wait'} or type(request['wait']) is not int or not 0 <= request['wait'] <= config['bounds']['wait_seconds']:
            raise ValueError('invalid operator acquisition')
        wait = request.pop('wait')
        request['baseline'] = exchange(config, {'operation': 'status'}, config['operator_uid'])['baseline']
        result = exchange(config, request, config['operator_uid'])
        capability = {key: result[key] for key in ('generation', 'capability')}
        deadline = time.monotonic() + wait
        try:
            while wait and result['state'] == 'queued':
                if time.monotonic() >= deadline:
                    exchange(config, {'operation': 'cancel', **capability}, config['operator_uid'])
                    raise Failure('wait', 'deadline reached; queue cancelled')
                time.sleep(min(2, max(0, deadline-time.monotonic())))
                result = exchange(config, {'operation': 'poll', **capability}, config['operator_uid'])
                result['capability'] = capability['capability']
        except (KeyboardInterrupt, BrokenPipeError):
            exchange(config, {'operation': 'cancel', **capability}, config['operator_uid'])
            raise
    else:
        result = exchange(config, request, config['operator_uid'])
    print(json.dumps(result))


def main(config):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator', action='store_true', help='native host fresh Polkit authentication')
    parser.add_argument('--capability-file', help='explicit private 0600 file; capability never in argv')
    parser.add_argument('--task')
    parser.add_argument('--command')
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--generation', type=int)
    parser.add_argument('--reason')
    parser.add_argument('--wait', type=int, default=0, help='bounded client wait, at most 3600 seconds')
    parser.add_argument('operation', choices=sorted(OPERATIONS))
    args = parser.parse_args()
    def send(request):
        if not args.operator:
            return exchange(config, request)
        helper = config['recovery_helper'] if request['operation'] == 'force-unlock' else config['helper']
        if request['operation'] == 'force-unlock':
            print('Forced recovery: generation %s; reason SHA-256 %s' % (request['generation'], hashlib.sha256(request['reason'].encode()).hexdigest()), file=sys.stderr)
        process = subprocess.run([config['pkexec'], '--disable-internal-agent', helper],
                                 input=json.dumps(request)+'\n', text=True, capture_output=True,
                                 env={'LANG': 'C'}, timeout=150 + args.wait)
        if process.returncode:
            raise Failure('operator', 'authentication or fixed helper request failed; inspect server status')
        return json.loads(process.stdout)
    if not 0 <= args.wait <= 3600 or args.wait and args.operation != 'acquire':
        parser.error('wait is supported only for acquisition and must be 0..3600')
    request = {'operation': args.operation}
    fd = None
    try:
        if args.operation == 'acquire':
            if not args.task or not args.command or not args.capability_file:
                parser.error('acquire requires task, command and capability-file')
            # Secure destination before acquiring so an unsafe file never loses
            # a newly issued capability. Persist immediately before any polling.
            fd = private_file(args.capability_file, os.getuid(), write=True)
            request.update(task=args.task, command=args.command)
            if args.operator:
                request['wait'] = args.wait
            else:
                request['baseline'] = send({'operation': 'status'})['baseline']
        elif args.operation == 'force-unlock':
            if not args.operator or args.generation is None or not args.reason:
                parser.error('force-unlock requires operator, generation and reason')
            request.update(generation=args.generation, reason=args.reason)
        elif args.operation != 'status':
            if not args.capability_file:
                parser.error('operation requires capability-file')
            request.update(read_capability(args.capability_file))
            if args.operation == 'renew':
                request['seconds'] = args.seconds
        result = send(request)
        if args.operation == 'acquire':
            capability = {'generation': result['generation'], 'capability': result.pop('capability')}
            info = os.fstat(fd)
            current = os.lstat(args.capability_file)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise Failure('capability-file', 'destination changed while acquiring; ticket will expire')
            with os.fdopen(fd, 'w') as stream:
                fd = None
                json.dump(capability, stream)
                stream.flush()
                os.fsync(stream.fileno())
            deadline = time.monotonic() + args.wait
            try:
                while result['state'] == 'queued' and args.wait and not args.operator:
                    if time.monotonic() >= deadline:
                        send({'operation': 'cancel', **capability})
                        raise Failure('wait', 'deadline reached; queue cancelled')
                    # Poll immediately after each short sleep; the 10-second
                    # diagnostic occupancy leaves margin within 30s liveness.
                    time.sleep(min(2, max(0, deadline-time.monotonic())))
                    result = send({'operation': 'poll', **capability})
            except KeyboardInterrupt:
                send({'operation': 'cancel', **capability})
                raise
        print(json.dumps(result, sort_keys=True))
    finally:
        if fd is not None:
            info = os.fstat(fd)
            os.close(fd)
            # Remove only our still-pinned destination; preserve concurrent
            # caller replacements, including a failed final write validation.
            try:
                current = os.lstat(args.capability_file)
                if (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino):
                    os.unlink(args.capability_file)
            except FileNotFoundError:
                pass


if __name__ == '__main__':
    try:
        with open(sys.argv[1]) as stream:
            config = json.load(stream)
        del sys.argv[1]
        if sys.argv[1:] in (['--authenticated-helper'], ['--authenticated-recovery']):
            authenticated(config, sys.argv[1:] == ['--authenticated-recovery'])
        else:
            main(config)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Never reflect a decoder, path or response (which may carry capability).
        message = ('%s: %s' % (error.stage, error)) if isinstance(error, Failure) else ('transport/helper timeout' if isinstance(error, subprocess.SubprocessError) else 'validation or transport failure; check capability file, socket and request fields')
        raise SystemExit('phoenix-reservation: ' + message) from None
