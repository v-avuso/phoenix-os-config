"""Exact registered ELF commands; imported only by the installed root controller.

The request supplies an identifier and audit context, never executable authority.
Program-byte binding is not an audit of the executable's dependency closure.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

REQUEST = {'version', 'operation', 'task', 'reason', 'authority'}
MODES = {'automatic', 'review', 'human'}
FORBIDDEN = {'sh','bash','dash','zsh','fish','busybox','env','sudo','pkexec','doas','su',
             'python','python3','perl','ruby','node','lua','awk','gawk','nix','nix-shell','nix-run'}
FLAGS = {'-c','--command','-e','--eval','--exec','-exec','-execdir','--shell'}
MAX_OUTPUT = 65536
TTL = 120

class Rejected(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def read_request(fd):
    import select
    result = bytearray(); deadline = time.monotonic()+5
    while not result.endswith(b'\n'):
        remaining = deadline-time.monotonic()
        if remaining <= 0 or not select.select([fd],[],[],remaining)[0]:
            raise Rejected('command-input-timeout')
        block = os.read(fd,4097-len(result))
        if not block: break
        result.extend(block)
        if len(result)>4096: raise Rejected('command-input-limit')
    return bytes(result)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def text(value, limit):
    import unicodedata
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(unicodedata.category(c).startswith('C') for c in value):
        raise Rejected('command-invalid-context')
    return value

def immutable(path):
    """Check both declared and resolved target ownership in the real Nix store."""
    p = Path(path)
    if not p.is_absolute() or not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+(?:/.+)?', str(p)):
        raise Rejected('command-program-not-immutable')
    resolved = p.resolve(strict=True)
    if not str(resolved).startswith('/nix/store/'):
        raise Rejected('command-program-not-immutable')
    for target in (p, resolved):
        for ancestor in (target, *target.parents):
            info = ancestor.lstat()
            if str(ancestor) == '/nix/store':
                if info.st_uid != 0 or not stat.S_ISDIR(info.st_mode) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                    raise Rejected('command-program-not-immutable')
                break
            if info.st_uid != 0 or (not stat.S_ISLNK(info.st_mode) and info.st_mode & 0o022):
                raise Rejected('command-program-not-immutable')
            if str(ancestor) == '/nix/store':
                break
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode):
        raise Rejected('command-program-not-immutable')
    return resolved

def program(entry):
    p = immutable(entry['executable'])
    # Initial surface deliberately excludes scripts and generic trampolines.
    for name in (Path(entry['executable']).name, p.name):
        if name in FORBIDDEN or re.match(r'^(python|perl|ruby|node|lua|bash|sh)([0-9.-]|$)', name):
            raise Rejected('command-program-unsupported')
    with p.open('rb') as stream:
        if stream.read(4) != b'\x7fELF' or not p.stat().st_mode & 0o111:
            raise Rejected('command-program-unsupported')
        stream.seek(0)
        fingerprint = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(p), 'sha256': fingerprint}

def current_authority(config, request):
    expected = immutable(config['commandAuthority'])
    current = Path(config['commandCurrentAuthority']).resolve(strict=True)
    if current != expected or hashlib.sha256(expected.read_bytes()).hexdigest() != request.get('authority'):
        raise Rejected('command-authority-changed')
    return hashlib.sha256(expected.read_bytes()).hexdigest()

def selected(config, request, uid, *, operator=False, critical=False, inspect=program):
    if not config.get('commands', {}).get('enable', False):
        raise Rejected('command-disabled')
    if not isinstance(request, dict) or set(request) != REQUEST or type(request['version']) is not int or request['version'] != 1:
        raise Rejected('command-invalid-request')
    if uid != config['operatorUid' if operator else 'clientUid']:
        raise Rejected('command-caller-denied')
    authority = current_authority(config, request)
    name = request['operation']
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name):
        raise Rejected('command-unknown-operation')
    text(request['task'], 100); text(request['reason'], 300)
    entry = config['commands']['entries'].get(name)
    if not isinstance(entry, dict) or set(entry) != {'executable','arguments','rationale','mode','timeout'}:
        raise Rejected('command-unknown-operation')
    if operator and ((entry['mode']=='review') != critical):
        raise Rejected('command-critical-authentication-required')
    text(entry['rationale'], 2000)
    args = entry['arguments']
    if (entry['mode'] not in MODES or type(entry['timeout']) is not int or not 1 <= entry['timeout'] <= 60
            or not isinstance(args, list) or len(args) > 16 or any(not isinstance(a, str) or len(a) > 4096 or '\x00' in a or a in FLAGS for a in args)
            or sum(len(a.encode()) for a in args) > 16384):
        raise Rejected('command-invalid-definition')
    if entry['mode'] == 'review' and not config.get('modelReviewEnabled', False):
        raise Rejected('command-review-provider-unavailable')
    identity = inspect(entry)
    binding = {'authority': authority, 'policy': digest({'commands': config['commands'], 'reviewPolicy': config.get('commandReviewPolicyDigest'),
                               'model': config.get('model'), 'effort': config.get('effort')}),
               'operation': name, 'program': entry['executable'], 'programTarget': identity['path'], 'programSha256': identity['sha256'],
               'arguments': digest(args), 'caller': str(uid), 'task': request['task'], 'reason': request['reason']}
    return entry, binding

def validate_verdict(verdict, binding):
    # Root validates independently of the unprivileged review worker/schema.
    if (not isinstance(verdict, dict) or set(verdict) != {*binding, 'approved', 'summary'}
            or any(verdict.get(k) != v for k,v in binding.items())
            or type(verdict.get('approved')) is not bool or not isinstance(verdict.get('summary'), str)
            or len(verdict['summary']) > 4000):
        raise Rejected('command-review-binding-invalid')
    if not verdict['approved']:
        error = Rejected('command-review-denied')
        import unicodedata
        error.summary = ''.join(c for c in verdict['summary'] if not unicodedata.category(c).startswith('C'))[:1000]
        raise error

def state_directory(config):
    p = Path(config['commandState'])
    p.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = p.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise Rejected('command-state-invalid')
    return p

def execute(config, entry, binding):
    """Drain bounded pipes; kill the entire process group on any deadline/overflow."""
    import secrets
    unit = 'phoenix-command-' + secrets.token_hex(16) + '.service'
    # A fixed transient cgroup retains setsid/double-fork descendants. The root
    # program is still trusted published code, not adversarial-code containment.
    argv = [config['systemdRun'], '--quiet', '--wait', '--pipe', '--description=Phoenix registered command',
        '--service-type=exec', '--unit='+unit, '--property=KillMode=control-group',
        '--property=RuntimeMaxSec='+str(entry['timeout']), '--property=TimeoutStopSec=2',
        '--property=NoNewPrivileges=yes', '--property=ProtectControlGroups=yes',
        '--expand-environment=no', '--', config['python'], '-I', config['commandExec'],
        binding['programTarget'], binding['program'], *entry['arguments']]
    child = subprocess.Popen(argv, cwd='/',
        env={'PATH':'/nonexistent','HOME':'/var/empty','LANG':'C'}, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, close_fds=True)
    selector = selectors.DefaultSelector(); output = {child.stdout:bytearray(),child.stderr:bytearray()}
    for stream in output:
        os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + entry['timeout'] + 5
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Rejected('command-timeout')
            for key,_ in selector.select(min(remaining, 0.1)):
                block = os.read(key.fileobj.fileno(), 8192)
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    output[key.fileobj].extend(block)
                    if sum(map(len, output.values())) > MAX_OUTPUT:
                        raise Rejected('command-output-limit')
        try:
            status = child.wait(timeout=max(0.001, deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            raise Rejected('command-timeout') from None
        if status:
            result = subprocess.run([config['systemctl'],'show','--property=Result','--value',unit],
                stdin=subprocess.DEVNULL,capture_output=True,timeout=5,check=False)
            if result.stdout.strip() == b'timeout': raise Rejected('command-timeout')
        return dict(ok=True, code='command-completed', exitCode=status,
                    stdout=bytes(output[child.stdout]).decode('utf-8', 'replace'),
                    stderr=bytes(output[child.stderr]).decode('utf-8', 'replace'))
    finally:
        cleanup_error = None
        try:
            # Try both service cleanup operations; failure must not skip local cleanup.
            for operation in ('stop','reset-failed'):
                try:
                    subprocess.run([config['systemctl'],operation,unit], stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,check=False)
                except subprocess.TimeoutExpired:
                    cleanup_error = 'command-cleanup-timeout'
                except OSError:
                    cleanup_error = cleanup_error or 'command-cleanup-failed'
        finally:
            try:
                try: os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                except OSError: cleanup_error = cleanup_error or 'command-cleanup-failed'
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: cleanup_error = 'command-cleanup-timeout'
                except OSError: cleanup_error = cleanup_error or 'command-cleanup-failed'
            finally:
                try: selector.close()
                finally:
                    for stream in output: stream.close()
        if cleanup_error is not None:
            raise Rejected(cleanup_error) from None

def process(config, request, uid, *, operator=False, critical=False, reviewer=None, inspect=program, executor=None, now=time.time, audit=None):
    if os.geteuid() != 0:
        raise Rejected('command-root-required')
    entry, binding = selected(config, request, uid, operator=operator, critical=critical, inspect=inspect)
    def emit(event, decision, category):
        if audit is not None: audit(event,decision,category)
    emit('requested',entry['mode'],'authenticated-operator-helper' if operator else 'kernel-peer')
    state = state_directory(config)
    fd = os.open(state/'lock', os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise Rejected('command-state-invalid')
        fcntl.flock(fd, fcntl.LOCK_EX)
        if entry['mode'] == 'human' and not operator:
            raise Rejected('command-human-authentication-required')
        if operator:
            emit('decision','critical-override' if critical else 'human','fresh-authenticated-operator')
        elif entry['mode']=='automatic':
            emit('decision','automatic','installed-exact-grant')
        if entry['mode'] == 'review' and not operator:
            key = digest(binding); cache = state/(key+'.json'); valid = False
            if cache.exists():
                info = cache.lstat()
                if stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o077 and info.st_size <= 16384:
                    try:
                        saved = json.loads(cache.read_text())
                        valid = (set(saved) == {'binding','created','expires'} and saved['binding'] == binding
                                 and type(saved['created']) in {int,float} and type(saved['expires']) in {int,float}
                                 and saved['created'] <= now() < saved['expires'] <= saved['created']+TTL)
                    except (ValueError, TypeError): pass
            if valid: emit('decision','review-cache','exact-unexpired-approval')
            if not valid:
                if reviewer is None: raise Rejected('command-review-error')
                try: verdict = reviewer(entry, binding)
                except Rejected: raise
                except Exception: raise Rejected('command-review-error') from None
                validate_verdict(verdict, binding)
                emit('decision','review-new','exact-bound-verdict')
                # Never cache a replaced definition/program after slow review.
                if selected(config, request, uid, inspect=inspect)[1] != binding:
                    raise Rejected('command-binding-changed')
                for old in sorted(state.glob('*.json'), key=lambda p:p.lstat().st_mtime)[:-31]: old.unlink()
                import tempfile
                for stale in state.glob('approval-*.tmp'):
                    if stale.lstat().st_mtime < now()-TTL: stale.unlink()
                out, temporary = tempfile.mkstemp(prefix='approval-', suffix='.tmp', dir=state)
                try:
                    stamp = now()
                    os.write(out, canonical({'binding':binding,'created':stamp,'expires':stamp+TTL}))
                    os.close(out); out = None
                    os.replace(temporary, cache)
                finally:
                    if out is not None: os.close(out)
                    Path(temporary).unlink(missing_ok=True)
        if selected(config, request, uid, operator=operator, critical=critical, inspect=inspect)[1] != binding:
            raise Rejected('command-binding-changed')
        return (executor(entry, binding) if executor is not None else execute(config, entry, binding))
    finally:
        os.close(fd)
