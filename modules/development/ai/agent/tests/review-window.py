"""Fixed temporary review window; no model invocation and no boot-profile update."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import stat
import subprocess
import sys
import time

UNIT = 'phoenix-controlled-review-off'
DEPLOYMENT = Path('/var/lib/phoenix-deploy/deployment.lock')
ACTIVATION = Path('/var/lib/phoenix-deploy/activation.lock')
PROFILE = Path('/nix/var/nix/profiles/system')
RUNTIME = Path('/run/current-system')


def event(stage):
    print(json.dumps(dict(trial='controlled-review-window', stage=stage)), flush=True)


def run(argv, timeout=60, **kwargs):
    with subprocess.Popen(argv, start_new_session=True, **kwargs) as child:
        try:
            return child.communicate(timeout=timeout), child.returncode
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL); child.wait()


def checked(argv, timeout=60, pass_fds=()):
    _, status = run(argv, timeout, pass_fds=pass_fds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if status: raise ValueError('command-failed')


def query(d, *args):
    (output, _), status = run([d['systemctl'], *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if status: raise ValueError('status-unavailable')
    return output.decode().strip()


def immutable(path):
    path = Path(path).resolve(strict=True)
    info = path.stat()
    if not str(path).startswith('/nix/store/') or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('immutable-input-required')
    return path


def configuration(closure):
    if str(immutable(closure)) != closure: raise ValueError('closure-alias-denied')
    lines = (Path(closure) / 'etc/systemd/system/phoenix-deploy.service').read_text().splitlines()
    commands = [shlex.split(line.removeprefix('ExecStart=')) for line in lines if line.startswith('ExecStart=')]
    if len(commands) != 1 or len(commands[0]) != 5 or commands[0][1] != '-I' or commands[0][-1] != 'serve':
        raise ValueError('controller-shape-invalid')
    command = commands[0]
    for path in (command[0], command[2], command[3]): immutable(path)
    return command, json.loads(Path(command[3]).read_text())


def validate(d):
    if set(d) != {'off', 'on', 'busctl', 'systemctl', 'systemdRun', 'python', 'script'} or d['off'] == d['on']:
        raise ValueError('descriptor-invalid')
    for key in ('busctl', 'systemctl', 'systemdRun', 'python', 'script'): immutable(d[key])
    off_command, off = configuration(d['off'])
    on_command, on = configuration(d['on'])
    for config, enabled in ((off, False), (on, True)):
        if config['modelReviewEnabled'] is not enabled or config['clientUid'] != 1000 or config['operatorUid'] != 1000:
            raise ValueError('configuration-invalid')
        if Path(config['work']).parent / 'deployment.lock' != DEPLOYMENT or Path(config['activationLock']) != ACTIVATION:
            raise ValueError('lock-identity-invalid')
        if config.get('reservations') or config.get('disruptionGuard', {}).get('enable'):
            raise ValueError('optional-controls-enabled')
    if (on['model'], on['effort']) != ('gpt-6-luna', 'high'):
        raise ValueError('reviewer-settings-invalid')
    return off_command, on_command


@contextlib.contextmanager
def locks(deadline):
    with contextlib.ExitStack() as stack:
        descriptors = []
        for path in (DEPLOYMENT, ACTIVATION):
            parent = path.parent.lstat()
            if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022 or path.parent.resolve() != path.parent:
                raise ValueError('unsafe-lock-directory')
            # Existing production lock only: never create/chmod another authority file.
            fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
            stack.callback(os.close, fd)
            descriptors.append(fd)
            info = os.fstat(fd)
            mode_ok = (stat.S_IMODE(info.st_mode) == 0o600 if path == ACTIVATION else not info.st_mode & 0o022)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or not mode_ok or info.st_nlink != 1:
                raise ValueError('unsafe-lock')
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
                except BlockingIOError:
                    if time.monotonic() >= deadline: raise ValueError('recovery-lock-busy')
                    time.sleep(0.1)
        yield tuple(descriptors)


def verify_off(d):
    if str(RUNTIME.resolve(strict=True)) != d['off'] or str(PROFILE.resolve(strict=True)) != d['off']:
        raise ValueError('off-binding-mismatch')


def switch(d, closure, descriptors):
    # Parent owns locks until this foreground child is reaped; ordinary termination
    # must not release a guard ahead of the mutation.
    def defer(signum, _frame):
        event('termination-deferred')
    previous = {s: signal.signal(s, defer) for s in (signal.SIGTERM, signal.SIGINT)}
    try: checked([closure + '/bin/switch-to-configuration', 'test'], timeout=600, pass_fds=descriptors)
    finally:
        for s, handler in previous.items(): signal.signal(s, handler)


def reload_on(d, command):
    pid = int(query(d, 'show', 'phoenix-deploy.service', '-p', 'MainPID', '--value'))
    if not pid: return
    try:
        fd = os.pidfd_open(pid)
        try:
            proc = Path('/proc') / str(pid)
            if proc.stat().st_uid == 0 and (proc / 'cmdline').read_bytes().split(b'\0')[:-1] == [x.encode() for x in command]:
                signal.pidfd_send_signal(fd, signal.SIGUSR1)
        finally: os.close(fd)
    except ProcessLookupError: pass


def recover(d, command):
    event('recovery-queued')
    reload_on(d, command)
    with locks(time.monotonic() + 8100) as descriptors:
        if str(PROFILE.resolve(strict=True)) != d['off']: raise ValueError('boot-profile-changed')
        switch(d, d['off'], descriptors); verify_off(d)
    event('off-restored')
    if query(d, 'show', UNIT + '.timer', '-p', 'LoadState', '--value') != 'not-found':
        checked([d['systemctl'], 'stop', UNIT + '.timer'])
    event('owned-timer-stopped-service-exits')


def timer_ready(d):
    if query(d, 'show', UNIT + '.timer', '-p', 'SubState', '--value') != 'waiting':
        raise ValueError('timer-not-waiting')
    path = '/org/freedesktop/systemd1/unit/phoenix_2dcontrolled_2dreview_2doff_2etimer'
    (output, _), status = run([d['busctl'], '--system', 'get-property', 'org.freedesktop.systemd1',
                              path, 'org.freedesktop.systemd1.Timer', 'NextElapseUSecMonotonic'],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fields = output.decode().strip().split()
    if status or len(fields) != 2 or fields[0] != 't' or not fields[1].isdigit():
        raise ValueError('timer-clock-unavailable')
    remaining = int(fields[1]) * 1000 - time.monotonic_ns()
    if remaining < 150_000_000_000 or remaining > 300_000_000_000:
        raise ValueError('timer-window-too-short')


def setup(d, command):
    event('setup-binding-check')
    verify_off(d)
    installed, _ = configuration(str(RUNTIME.resolve(strict=True)))
    expected, _ = configuration(d['off'])
    if installed != expected: raise ValueError('installed-controller-mismatch')
    if os.environ.get('PKEXEC_UID') != '1000': raise ValueError('operator-authentication-required')
    for suffix in ('.timer', '.service'):
        if query(d, 'show', UNIT + suffix, '-p', 'LoadState', '--value') != 'not-found':
            raise ValueError('owned-unit-already-exists')
    armed = False
    try:
        event('setup-idle-lock-check')
        with locks(time.monotonic()) as descriptors:
            verify_off(d)
            checked([d['systemdRun'], '--collect', '--unit=' + UNIT, '--on-active=5m', '--timer-property=AccuracySec=1s', '--timer-property=RemainAfterElapse=no',
                     '--property=Type=oneshot', '--property=TimeoutStartSec=infinity',
                     d['python'], '-I', d['script'], d['descriptor'], 'recover'])
            armed = True
            if query(d, 'is-active', UNIT + '.timer') != 'active': raise ValueError('timer-not-armed')
            event('timer-armed'); switch(d, d['on'], descriptors)
            if str(RUNTIME.resolve(strict=True)) != d['on'] or str(PROFILE.resolve(strict=True)) != d['off']:
                raise ValueError('on-binding-mismatch')
            timer_ready(d)
        event('on-ready')
    except Exception:
        if armed: recover(d, command)
        raise


def main(descriptor, mode):
    d = json.loads(immutable(descriptor).read_text())
    _, command = validate(d)
    if mode == 'dry-run': event('package-valid-no-state-change'); return
    if os.geteuid() != 0: raise ValueError('root-required')
    d['descriptor'] = str(immutable(descriptor))
    if mode == 'setup': setup(d, command)
    elif mode == 'recover': recover(d, command)
    else: raise ValueError('mode-invalid')


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3: raise ValueError('arguments-invalid')
        main(*sys.argv[1:])
    except Exception as error:
        codes = {'command-failed', 'status-unavailable', 'immutable-input-required', 'controller-shape-invalid',
                 'descriptor-invalid', 'closure-alias-denied', 'configuration-invalid', 'lock-identity-invalid', 'optional-controls-enabled',
                 'reviewer-settings-invalid', 'unsafe-lock-directory', 'unsafe-lock', 'recovery-lock-busy',
                 'off-binding-mismatch', 'boot-profile-changed', 'installed-controller-mismatch',
                 'operator-authentication-required', 'owned-unit-already-exists', 'timer-not-armed',
                 'on-binding-mismatch', 'timer-not-waiting', 'timer-clock-unavailable', 'timer-window-too-short', 'root-required', 'mode-invalid', 'arguments-invalid'}
        code = ('command-timeout' if isinstance(error, subprocess.TimeoutExpired) else
                'io-failed' if isinstance(error, OSError) else
                str(error) if type(error) is ValueError and str(error) in codes else 'unexpected-failure')
        event('failed-' + code); sys.exit(1)
