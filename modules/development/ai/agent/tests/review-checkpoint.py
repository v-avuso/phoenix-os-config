"""Zero-AI isolated root checkpoint/provenance trial, not deployment acceptance."""
import contextlib
import fcntl
import hashlib
import pwd
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


def verify_records(directory, source, closure, selected=False):
    info = directory.lstat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('checkpoint-directory-invalid')
    records = list(directory.glob('*.approved.json'))
    if not records:
        raise ValueError('checkpoint-missing')
    matched = False
    for record in records:
        if selected and json.loads(record.read_text()).get('source') != source:
            continue
        matched = True
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

    if not matched:
        raise ValueError('checkpoint-missing')


def candidate(review, source):
    files = review.baseline_files(Path(source))
    modes = review.source_modes(Path(source), files)
    if 'README.md' not in files:
        raise ValueError('trial-readme-missing')
    files['README.md'] += '\n<!-- Isolated review integration acceptance; no configuration change. -->\n'
    return files, modes


def activation_recorder(deploy, runtime, profile, recorded):
    def record(config, binding, temporary, loaded_review, state, uid, pid):
        del temporary, state, uid, pid
        with deploy.activation_guard(config):
            deploy.recheck_bound(config, binding)
            if str(Path('/run/current-system').resolve()) != runtime or str(Path('/nix/var/nix/profiles/system').resolve()) != profile:
                raise ValueError('active-binding-changed')
            recorded.append(binding)
            return dict(source=binding['source'], closure=binding['closure'], activation=False)
    return record


def pending_override(deploy, review, security, trial, source, runtime, profile):
    if security.records(trial, 'approved'):
        raise ValueError('override-cache-not-empty')
    nonce = os.urandom(32).hex()
    binding = dict(source=source, closure=runtime, target=trial['target'], action='test',
                   base=source, profile=profile, profileSource=source, nonce=nonce,
                   reason='Synthetic pending override acceptance; activation disabled.', commit='0' * 40)
    security.pending(trial, binding, trial['clientUid'], 'override-trial',
                     'schema-invalid', 'Synthetic fixture failure, not an AI rejection.', review.run)
    pending = Path(trial['securityReviewState']) / (nonce + '.pending.json')
    recorded = []
    deploy.activate_bound = activation_recorder(deploy, runtime, profile, recorded)
    try:
        deploy.override(trial, nonce, trial['operatorUid'] + 1, os.getpid())
    except ValueError as error:
        if str(error) != 'security override requires authenticated root and enabled review':
            raise
    else:
        raise ValueError('override-wrong-uid-accepted')
    if recorded or not pending.exists() or security.records(trial, 'approved'):
        raise ValueError('override-binding-mismatch')
    result = deploy.override(trial, nonce, trial['operatorUid'], os.getpid())
    if len(recorded) != 1 or (result['source'], result['closure']) != (source, runtime):
        raise ValueError('override-binding-mismatch')
    if pending.exists() or list(pending.parent.glob(nonce + '.pending.*')):
        raise ValueError('override-pending-remains')
    verify_records(Path(trial['securityReviewState']), source, runtime)
    if not any(record.get('branch') == security.branch_key('override-trial')
               for _, record in security.records(trial, 'approved')):
        raise ValueError('checkpoint-missing')
    try:
        deploy.override(trial, nonce, trial['operatorUid'], os.getpid())
    except FileNotFoundError:
        pass
    else:
        raise ValueError('override-replay-accepted')
    if len(recorded) != 1:
        raise ValueError('override-replay-accepted')
    return dict(status='passed', modelInvocations=0, activation=False, syntheticPending=True,
                wrongOperatorRejected=True, pendingConsumed=True, replayRejected=True,
                rootCheckpoint=True, controllerUid=os.geteuid(), ownedRootsCleaned=True,
                authentication='generic-pkexec-not-critical-action')


def integration(deploy, review, trial, public, root, source, runtime, profile, plan=False):
    files, modes = candidate(review, source)
    if plan:
        with tempfile.TemporaryDirectory(prefix='phoenix-review-plan-') as directory:
            snapshot = Path(directory)
            for name, content in files.items():
                path = snapshot / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                path.chmod(0o755 if modes[name] == '100755' else 0o644)
            frozen = review.run([trial['nix'], '--offline', 'store', 'add-path', '--name', 'source', str(snapshot)]).decode().strip()
        return dict(status='prebuild-plan', source=frozen, modelInvocations=0, activation=False,
                    buildArgv=[trial['nix'], '--offline', 'build', '--no-link', '--print-out-paths',
                               '--no-write-lock-file', '--option', 'accept-flake-config', 'false', 'path:' + frozen + '#nixosConfigurations.' + trial['target'] + '.config.system.build.toplevel'])
    reviewer = pwd.getpwnam(trial['reviewerUser'])
    budget = root / 'budget'; budget.mkdir(mode=0o755)
    token = budget / 'used'; token.write_text('0'); token.chmod(0o600)
    os.chown(token, reviewer.pw_uid, reviewer.pw_gid)
    trial = dict(trial, bwrap=public['gateBwrap'], codex=public['gateCodex'], nix=public['offlineNix'])
    config_path = root / 'integration.json'
    trial['configPath'] = str(config_path)
    config_path.write_text(json.dumps(trial)); config_path.chmod(0o444)
    # Gate identities change the policy fingerprint: seed only this private policy.
    deploy.trust_active(trial, trial['operatorUid'], os.getpid())
    recorded = []
    deploy.activate_bound = activation_recorder(deploy, runtime, profile, recorded)
    request = dict(files=files, modes=modes, commit=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
                   target=trial['target'], action='test', reason='Isolated root review integration; activation disabled.',
                   task='review-integration-trial', branch='review-integration-a')
    # Avoid raw model summaries or controller output in the public receipt.
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        # Authenticated fixture supplies the configured daemon caller identity;
        # this is not proof of socket peer admission.
        first = deploy.process(trial, request, trial['clientUid'], os.getpid())
        if token.read_text() != '1' or len(recorded) != 1:
            raise ValueError('trial-review-count-invalid')
        verify_records(Path(trial['securityReviewState']), first['source'], first['closure'], selected=True)
        request['branch'] = 'review-integration-b'
        second = deploy.process(trial, request, trial['clientUid'], os.getpid())
    if first != second or token.read_text() != '1' or len(recorded) != 2:
        raise ValueError('exact-reuse-or-state-changed')
    return dict(status='passed', modelInvocations=1, activation=False, rootCheckpoint=True,
                exactReuse=True, builderUid=pwd.getpwnam(trial['builderUser']).pw_uid,
                reviewerUid=reviewer.pw_uid, controllerUid=os.geteuid(), ownedRootsCleaned=True)


def interrupt(*_):
    raise InterruptedError("trial-interrupted")


def main(descriptor, dry_run=False, integration_mode=False, plan=False, override_mode=False):
    stage = 'configuration'
    try:
        public = json.loads(immutable(descriptor).read_text())
        config = json.loads(immutable(public['config']).read_text())
        controller = immutable(public['controller'])
        if dry_run:
            print(json.dumps(dict(status='dry-run', modelInvocations=0, activation=False,
                                  proof='synthetic-pending-override-activation-stub' if override_mode else ('root-process-review-activation-stub' if integration_mode else 'trust-active-root-checkpoint-only'))))
            return 0
        if plan:
            spec = importlib.util.spec_from_file_location('checkpoint_controller', controller)
            deploy = importlib.util.module_from_spec(spec); spec.loader.exec_module(deploy)
            result = integration(deploy, deploy.load_review(config), config, public, None, str(Path(config['baseline']).resolve(strict=True)), None, None, plan=True)
            print(json.dumps(result)); return 0
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
        receipt = None
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
                if override_mode:
                    stage = 'pending-override'
                    receipt = pending_override(deploy, review, security, trial, source, runtime, profile)
                else:
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
                    if integration_mode:
                        stage = 'root-process-integration'
                        receipt = integration(deploy, review, trial, public, root, source, runtime, profile)
        if receipt is not None:
            print(json.dumps(receipt)); return 0
        print(json.dumps(dict(status='passed', modelInvocations=0, activation=False,
                              rootCheckpoint=True, exactReuse=True, ownedRootsCleaned=True, trialPid=os.getpid())))
        return 0
    except Exception as error:
        codes = {'trial-interrupted', 'operator-authentication-required', 'trial-config-invalid', 'immutable-input-required',
                 'lock-identities-overlap', 'checkpoint-directory-invalid', 'checkpoint-missing',
                 'checkpoint-owner-invalid', 'checkpoint-binding-mismatch', 'checkpoint-root-invalid',
                 'runtime-profile-mismatch', 'activation-guard-unavailable', 'global-lock-invalid',
                 'active-binding-changed', 'exact-reuse-or-state-changed', 'trial-readme-missing', 'trial-review-count-invalid', 'rejected-or-failed', 'baseline-provenance-missing',
                 'baseline-provenance-invalid', 'baseline-verification-failed', 'baseline-target-mismatch'}
        if hasattr(error, 'stage'):
            stage = error.stage
        codes.update({'override-cache-not-empty', 'override-wrong-uid-accepted', 'override-binding-mismatch', 'override-pending-remains', 'override-replay-accepted', 'review-authentication-missing', 'review-authentication-failed', 'review-timeout',
                      'review-invocation-failed', 'reviewer-invocation-failed', 'schema-invalid', 'binding-mismatch',
                      'model-denied', 'review-context-oversized', 'baseline-changed', 'profile-changed'})
        candidate = getattr(error, 'code', str(error))
        code = candidate if candidate in codes else ('global-lock-busy' if isinstance(error, BlockingIOError) else 'trial-failed')
        print(json.dumps(dict(status='blocked-or-failed', stage=stage, code=code, modelInvocations='at-most-one' if integration_mode else 0,
                              activation=False, retry=False)))
        return 1


if __name__ == '__main__':
    allowed = {'--dry-run', '--integration', '--integration-dry-run', '--prebuild-plan', '--pending-override', '--pending-override-dry-run'}
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in allowed):
        raise SystemExit(2)
    mode = sys.argv[2] if len(sys.argv) == 3 else ''
    raise SystemExit(main(sys.argv[1], mode in {'--dry-run', '--integration-dry-run', '--pending-override-dry-run'},
                          mode.startswith('--integration'), mode == '--prebuild-plan', mode.startswith('--pending-override')))
