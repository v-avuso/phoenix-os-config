"""Zero-AI isolated root checkpoint/provenance trial, not deployment acceptance."""
import contextlib
import fcntl
import importlib.util
import json
import os
import signal
from pathlib import Path
import stat
import sys
import tempfile


def require_operator(config, effective_uid, authenticated_uid):
    if effective_uid != 0 or authenticated_uid != str(config['operatorUid']):
        raise ValueError('operator-authentication-required')
    if not config.get('modelReviewEnabled') or (config['model'], config['effort']) != ('gpt-6-luna', 'high'):
        raise ValueError('trial-config-invalid')


def immutable(path):
    path = Path(path).resolve(strict=True)
    info = path.stat()
    if not str(path).startswith('/nix/store/') or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('immutable-input-required')
    return path


def private_config(config, root):
    work = root / 'requests'
    work.mkdir(mode=0o711)
    state = root / 'checkpoints'
    state.mkdir(mode=0o700)
    original_lock = Path(config['work']).parent / 'deployment.lock'
    if original_lock == work.parent / 'deployment.lock':
        raise ValueError('lock-identities-overlap')
    return dict(config, work=str(work), securityReviewState=str(state)), original_lock


def verify_records(directory, source, closure):
    info = directory.lstat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('checkpoint-directory-invalid')
    records = list(directory.glob('*.approved.json'))
    if not records:
        raise ValueError('checkpoint-missing')
    for record in records:
        info = record.lstat()
        if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('checkpoint-owner-invalid')
        value = json.loads(record.read_text())
        if (value['source'], value['closure']) != (source, closure):
            raise ValueError('checkpoint-binding-mismatch')
        for field, expected in (('source', source), ('closure', closure)):
            root = record.with_suffix('.' + field)
            if not root.is_symlink() or root.lstat().st_uid != 0 or str(root.resolve(strict=True)) != expected:
                raise ValueError('checkpoint-root-invalid')


def interrupt(*_):
    raise InterruptedError("trial-interrupted")


def main(descriptor, dry_run=False):
    stage = 'configuration'
    try:
        public = json.loads(immutable(descriptor).read_text())
        config = json.loads(immutable(public['config']).read_text())
        controller = immutable(public['controller'])
        if dry_run:
            print(json.dumps(dict(status='dry-run', modelInvocations=0, activation=False,
                                  proof='trust-active-root-checkpoint-only')))
            return 0
        stage = 'authentication'
        require_operator(config, os.geteuid(), os.environ.get('PKEXEC_UID'))
        signal.signal(signal.SIGTERM, interrupt)
        signal.signal(signal.SIGINT, interrupt)
        stage = 'load-controller'
        spec = importlib.util.spec_from_file_location('checkpoint_controller', controller)
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        review, security = deploy.load_review(config), deploy.load_security(config)
        stage = 'active-binding'
        runtime = str(Path('/run/current-system').resolve(strict=True))
        source = str(Path(config['baseline']).resolve(strict=True))
        profile = str(Path('/nix/var/nix/profiles/system').resolve(strict=True))
        if runtime != profile:
            raise ValueError('runtime-profile-mismatch')
        for path in (runtime, source):
            review.run([config['nixStore'], '--check-validity', path])
        # Refuse a missing guard rather than provision any production state.
        immutable_guard = Path(config['activationLock']).lstat()
        if not stat.S_ISREG(immutable_guard.st_mode) or immutable_guard.st_uid != 0 or stat.S_IMODE(immutable_guard.st_mode) != 0o600 or immutable_guard.st_nlink != 1:
            raise ValueError('activation-guard-unavailable')
        with tempfile.TemporaryDirectory(prefix='phoenix-checkpoint-trial-', dir='/var/tmp') as directory:
            root = Path(directory)
            root.chmod(0o711)
            trial, global_lock = private_config(config, root)
            global_lock = global_lock.resolve(strict=True)
            if global_lock == (root / 'deployment.lock').resolve():
                raise ValueError('lock-identities-overlap')
            fd = os.open(global_lock, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, 'a') as lock:
                info = os.fstat(lock.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                    raise ValueError('global-lock-invalid')
                stage = 'global-lock'
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                stage = 'trust-active'
                # Production function validates provenance and takes its real
                # activation guard; no worker/process/activation callback exists.
                result = deploy.trust_active(trial, config['operatorUid'], os.getpid())
                if (result['source'], result['closure']) != (source, runtime):
                    raise ValueError('active-binding-changed')
                stage = 'root-checkpoint'
                verify_records(Path(trial['securityReviewState']), source, runtime)
                stage = 'exact-reuse'
                reused, _, _ = security.choose_checkpoint(trial, config['target'], source, runtime,
                    'another-trial-branch', source, review.baseline_files(Path(source)), review, deploy.store_path)
                if not reused or str(Path('/run/current-system').resolve(strict=True)) != runtime or str(Path('/nix/var/nix/profiles/system').resolve(strict=True)) != profile:
                    raise ValueError('exact-reuse-or-state-changed')
        print(json.dumps(dict(status='passed', modelInvocations=0, activation=False,
                              rootCheckpoint=True, exactReuse=True, ownedRootsCleaned=True, trialPid=os.getpid())))
        return 0
    except Exception as error:
        codes = {'trial-interrupted', 'operator-authentication-required', 'trial-config-invalid', 'immutable-input-required',
                 'lock-identities-overlap', 'checkpoint-directory-invalid', 'checkpoint-missing',
                 'checkpoint-owner-invalid', 'checkpoint-binding-mismatch', 'checkpoint-root-invalid',
                 'runtime-profile-mismatch', 'activation-guard-unavailable', 'global-lock-invalid',
                 'active-binding-changed', 'exact-reuse-or-state-changed', 'baseline-provenance-missing',
                 'baseline-provenance-invalid', 'baseline-verification-failed', 'baseline-target-mismatch'}
        candidate = getattr(error, 'code', str(error))
        code = candidate if candidate in codes else ('global-lock-busy' if isinstance(error, BlockingIOError) else 'trial-failed')
        print(json.dumps(dict(status='blocked-or-failed', stage=stage, code=code, modelInvocations=0,
                              activation=False, retry=False)))
        return 1


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != '--dry-run'):
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], len(sys.argv) == 3))
