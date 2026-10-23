"""On-demand exact-source recovery; native authentication, protected review, no overrides.

The packaged descriptor fixes all inputs. This is never installed as an automatic
grant. Only an operator-approved immutable executable may enter this root path.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pwd
import secrets
import shlex
import stat
import sys
import tempfile


def immutable(path):
    resolved = Path(path).resolve(strict=True)
    info = resolved.stat()
    if (not str(resolved).startswith('/nix/store/') or not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0 or info.st_mode & 0o022):
        raise ValueError('immutable-input-required')
    return resolved


def load(path):
    spec = importlib.util.spec_from_file_location('source_bootstrap_controller', immutable(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def service_binding(closure, config_path, config):
    unit = immutable(Path(closure) / 'etc/systemd/system/phoenix-deploy.service')
    argv = shlex.split(next(line.split('=', 1)[1] for line in unit.read_text().splitlines() if line.startswith('ExecStart=')))
    if argv != [config['python'], '-I', config['controller'], config_path, 'serve']:
        raise ValueError('recovery-controller-config-binding-mismatch')


def inspect(descriptor):
    old = json.loads(immutable(descriptor['installedConfig']).read_text())
    new = json.loads(immutable(descriptor['candidateConfig']).read_text())
    new['configPath'] = descriptor['candidateConfig']
    for key in ('modelReviewEnabled', 'target', 'operatorUid', 'clientUid', 'reviewerUser', 'builderUser',
                'reviewHome', 'work', 'securityReviewState', 'activationLock', 'codex', 'model', 'effort',
                'reservations', 'disruptionGuard', 'commands'):
        if old.get(key) != new.get(key):
            raise ValueError('recovery-cannot-change-authority-or-review-identity')
    if not old['modelReviewEnabled']:
        raise ValueError('enabled-security-review-required')
    if old.get('reservations'):
        raise ValueError('recovery-reservation-support-required')
    if json.loads(immutable(old['authorizationPolicy']).read_text()) != json.loads(immutable(new['authorizationPolicy']).read_text()):
        raise ValueError('recovery-cannot-change-authorization-policy')
    for prefix in ('approved', 'candidate'):
        if str((Path(descriptor[prefix + 'Closure']) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != descriptor[prefix + 'Source']:
            raise ValueError('closure-source-binding-mismatch')
    service_binding(descriptor['candidateClosure'], descriptor['candidateConfig'], new)
    deploy = load(new['controller'])
    security = deploy.load_security(new)
    if (security.policy_digest(old) != descriptor['installedPolicy'] or
            security.policy_digest(new) != descriptor['candidatePolicy']):
        raise ValueError('recovery-policy-binding-mismatch')
    return old, new, deploy, security


def recheck(descriptor, old, new, deploy, security):
    for path, key in [('/run/current-system', 'runtime'), ('/nix/var/nix/profiles/system', 'profile'),
                      (old['baseline'], 'baseline')]:
        if str(Path(path).resolve(strict=True)) != descriptor[key]:
            raise ValueError('recovery-active-state-changed')
    service_binding(descriptor['runtime'], descriptor['installedConfig'], old)
    if (security.policy_digest(old) != descriptor['installedPolicy'] or
            security.policy_digest(new) != descriptor['candidatePolicy']):
        raise ValueError('recovery-policy-binding-mismatch')
    deploy.activation_executable(descriptor['candidateClosure'])


def approved_baseline(descriptor, old, security):
    match = any(record.get('policy') == descriptor['installedPolicy'] and
                record.get('target') == old['target'] and
                record.get('source') == descriptor['approvedSource'] and
                record.get('closure') == descriptor['approvedClosure']
                for _, record in security.records(old, 'approved'))
    if not match:
        raise ValueError('previous-protected-approval-required')
    # This helper is not an override for a retained denial of the exact candidate.
    if any(record.get('source') == descriptor['candidateSource'] and record.get('code') == 'model-denied'
           for _, record in security.records(old, 'pending')):
        raise ValueError('retained-denial-requires-separate-resolution')


def verify_completion(descriptor, new, deploy, security, review):
    for path, expected in [('/run/current-system', descriptor['candidateClosure']),
                           ('/nix/var/nix/profiles/system', descriptor['candidateClosure']),
                           (new['baseline'], descriptor['candidateSource'])]:
        if str(Path(path).resolve(strict=True)) != expected:
            raise ValueError('recovery-installed-binding-mismatch')
    if not any(record.get('policy') == descriptor['candidatePolicy'] and
               record.get('target') == new['target'] and
               record.get('source') == descriptor['candidateSource'] and
               record.get('closure') == descriptor['candidateClosure']
               for _, record in security.records(new, 'approved')):
        raise ValueError('recovery-checkpoint-publication-missing')
    # An old-policy source is not silently approved under the new policy.
    exact, _, _ = security.choose_checkpoint(new, new['target'], descriptor['approvedSource'],
        descriptor['approvedClosure'], 'recovery-enforcement-check', descriptor['candidateSource'],
        review.baseline_files(Path(descriptor['approvedSource'])), review, deploy.store_path)
    if exact:
        raise ValueError('recovery-unreviewed-source-reused')


def recover(descriptor, old, new, deploy, security, uid):
    if os.geteuid() != 0 or uid != old['operatorUid']:
        raise ValueError('native-operator-authentication-required')
    review = deploy.load_review(new)
    lock = Path(old['work']).parent / 'deployment.lock'
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with deploy.activation_guard(new):
            recheck(descriptor, old, new, deploy, security)
            approved_baseline(descriptor, old, security)
        files = review.baseline_files(Path(descriptor['candidateSource']))
        baseline = review.baseline_files(Path(descriptor['approvedSource']))
        binding = dict(source=descriptor['candidateSource'], closure=descriptor['candidateClosure'],
                       base=descriptor['baseline'], profile=descriptor['profile'],
                       profileSource=str((Path(descriptor['profile']) / 'etc/phoenix-agent/activated-source').resolve(strict=True)),
                       reviewBase=descriptor['approvedSource'], oldPolicy=descriptor['installedPolicy'],
                       newPolicy=descriptor['candidatePolicy'], target=new['target'], action='switch',
                       reason='Restore safe symlink updates with explicit reviewed checkpoint transition',
                       commit=descriptor['commit'], nonce=secrets.token_hex(32))
        payload = dict(binding=binding, files=files, baseline=baseline,
                       diff=review.source_diff(baseline, files,
                            review.source_modes(Path(descriptor['approvedSource']), baseline),
                            review.source_modes(Path(descriptor['candidateSource']), files)))
        # The existing adapter enforces its two-call/context limits. No retries,
        # credential copying, caller verdicts or automatic human override.
        with tempfile.TemporaryDirectory(prefix='source-recovery-', dir=new['work']) as directory:
            temporary = Path(directory)
            account = pwd.getpwnam(new['reviewerUser'])
            temporary.chmod(0o755)
            review_work = temporary / 'review'
            review_work.mkdir(mode=0o700)
            os.chown(review_work, account.pw_uid, account.pw_gid)
            output = deploy.as_user(new, new['reviewerUser'],
                [new['python'], '-I', new['controller'], new['configPath'], 'worker', str(review_work)],
                review.run, data=json.dumps(payload).encode(), timeout=1400,
                env={'HOME': new['reviewHome'], 'PATH': '/nonexistent'})
            verdict = json.loads(output)
            if not isinstance(verdict, dict) or set(verdict) != {'status', 'verdict'} or verdict['status'] != 'verdict':
                raise ValueError('protected-review-failed')
            try:
                review.validate_verdict(verdict['verdict'], binding)
            except review.ReviewDenied:
                security.pending(new, binding, uid, 'reviewed-source-recovery', 'model-denied',
                                 'Protected security review denied source recovery.', review.run)
                raise ValueError('model-denied') from None
            # The old-policy checkpoint supplies context only. Publish new-policy
            # authority only after a fresh exact bound verdict and locked recheck.
            with deploy.activation_guard(new):
                recheck(descriptor, old, new, deploy, security)
                approved_baseline(descriptor, old, security)
                security.approve(new, binding, 'reviewed-source-recovery', review.run)
            result = deploy.activate_bound(new, binding, temporary, review, {}, uid, os.getpid())
            verify_completion(descriptor, new, deploy, security, review)
            return dict(result, checkpointPublished=True, previousCheckpointVerified=True,
                        installedBindingsVerified=True, unapprovedSourceRequiresReview=True)


def main(descriptor_path, dry_run=False):
    descriptor = json.loads(immutable(descriptor_path).read_text())
    old, new, deploy, security = inspect(descriptor)
    recheck(descriptor, old, new, deploy, security)
    if dry_run:
        print(json.dumps(dict(ok=True, activation=False, protectedCheckpointUnchecked=True,
                             source=descriptor['candidateSource'], closure=descriptor['candidateClosure'])))
        return
    uid = int(os.environ.get('PKEXEC_UID', '-1'))
    result = recover(descriptor, old, new, deploy, security, uid)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != '--inspect'):
            raise ValueError('fixed-arguments-required')
        main(sys.argv[1], len(sys.argv) == 3)
    except Exception as error:
        # No raw worker/model stderr or source data in the operator receipt.
        code = str(error) if isinstance(error, ValueError) and str(error).replace('-', '').isalpha() else 'source-recovery-failed'
        print(json.dumps(dict(ok=False, code=code)))
        raise SystemExit(1)
