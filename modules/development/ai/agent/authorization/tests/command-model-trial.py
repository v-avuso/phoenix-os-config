"""Fixed real-review/root-id trial. No deployment, login or general executor."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import re
import signal
import stat
import subprocess
import sys
import tempfile


def immutable(path):
    result = Path(path).resolve(strict=True)
    info = result.stat()
    if (not str(result).startswith('/nix/store/') or not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0 or info.st_mode & 0o022):
        raise ValueError('immutable-input-required')
    return result


def validate_config(public, config):
    if (set(public) != {'version','gateBwrap','gateCodex','trialAuthority','controller','config','executable','provider','operatorUid'}
            or public['version'] != 1 or type(public['operatorUid']) is not int or public['operatorUid'] <= 0
            or config['operatorUid'] != public['operatorUid'] or config['clientUid'] != public['operatorUid']
            or config.get('modelReviewEnabled') is not True or config.get('adapter') != 'codex'
            or (config['model'],config['effort']) != ('gpt-6-luna','high')
            or config['reviewerUser'] != 'phoenix-deploy-review' or config['reviewHome'] != '/var/lib/phoenix-deploy-review'
            or config['codex'] != public['provider']):
        raise ValueError('trial-config-invalid')
    entries = config['commands']['entries']
    if config['commands']['enable'] is not True or set(entries) != {'identity-review'}:
        raise ValueError('trial-config-invalid')
    entry = entries['identity-review']
    if (set(entry) != {'executable','arguments','rationale','mode','timeout'}
            or entry['executable'] != public['executable'] or entry['arguments'] != ['-u']
            or entry['mode'] != 'review' or entry['timeout'] != 10
            or not isinstance(entry['rationale'],str) or not entry['rationale'].strip()):
        raise ValueError('trial-config-invalid')
    for path in (public['controller'],public['config'],public['gateBwrap'],public['gateCodex'],
                 public['trialAuthority'],public['provider'],public['executable'],config['commandLibrary'],
                 config['commandExec'],config['reviewScript'],config['commandReviewPolicy'],config['python'],
                 config['systemdRun'],config['systemctl'],config['setpriv']):
        immutable(path)
    authority = json.loads(immutable(public['trialAuthority']).read_text())
    if authority['registry'] != config['commands']:
        raise ValueError('trial-config-invalid')


def require_operator(config, effective_uid, authenticated_uid):
    if effective_uid != 0 or authenticated_uid != str(config['operatorUid']):
        raise ValueError('operator-authentication-required')


def private_config(config, public, root, reviewer):
    root.chmod(0o711)
    work = root/'requests'; work.mkdir(mode=0o711)
    state = root/'cache'; state.mkdir(mode=0o700)
    budget = root/'budget'; budget.mkdir(mode=0o755)
    used = budget/'used'; used.write_text('0'); used.chmod(0o600)
    os.chown(used,reviewer.pw_uid,reviewer.pw_gid)
    current = root/'current-authority'; current.symlink_to(public['trialAuthority'])
    trial = dict(config,work=str(work),commandState=str(state),commandCurrentAuthority=str(current),
                 commandAuthority=public['trialAuthority'],bwrap=public['gateBwrap'],codex=public['gateCodex'])
    path = root/'config.json';trial['configPath']=str(path)
    path.write_text(json.dumps(trial));path.chmod(0o444)
    return trial,used


def interrupt(*_):
    raise InterruptedError('trial-interrupted')


def cleanup_units(config, units):
    failed = False
    for unit in units:
        if not re.fullmatch(r'phoenix-command-[a-f0-9]{32}\.service',unit):
            raise ValueError('trial-unit-invalid')
        for operation in ('stop','reset-failed'):
            try:
                subprocess.run([config['systemctl'],operation,unit],stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,check=False)
            except (OSError,subprocess.TimeoutExpired): failed=True
        try:
            status=subprocess.run([config['systemctl'],'is-active','--quiet',unit],stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,check=False)
            if status.returncode not in (3,4): failed=True
        except (OSError,subprocess.TimeoutExpired): failed=True
    if failed: raise ValueError('trial-cleanup-failed')


def controlled_trial(deploy, config, public, root):
    reviewer=pwd.getpwnam(config['reviewerUser'])
    trial,used=private_config(config,public,root,reviewer)
    request=dict(version=1,operation='identity-review',task='registered-command-model-trial',
                 reason='Controlled real review of fixed root id -u; no activation or configuration mutation.',
                 authority=hashlib.sha256(immutable(public['trialAuthority']).read_bytes()).hexdigest())
    # Observe only exact units created by the actual executor; never enumerate or
    # stop unrelated live services. No executor or verdict is substituted.
    original=subprocess.Popen; units=set()
    def observe(argv,*args,**kwargs):
        if isinstance(argv,list) and argv[:1]==[config['systemdRun']]:
            for arg in argv:
                if isinstance(arg,str) and arg.startswith('--unit='): units.add(arg[7:])
        return original(argv,*args,**kwargs)
    subprocess.Popen=observe
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            first=deploy.command_process(trial,request,config['operatorUid'],operator=False,pid=os.getpid())
            if not first.get('ok'):
                error=ValueError('trial-review-or-execution-failed');error.code=first.get('code');raise error
            if first.get('stdout') != '0\n' or first.get('exitCode') != 0 or used.read_text() != '1':
                raise ValueError('trial-proof-invalid')
            second=deploy.command_process(trial,request,config['operatorUid'],operator=False,pid=os.getpid())
        if (not second.get('ok') or second.get('stdout') != '0\n' or second.get('exitCode') != 0
                or used.read_text() != '1' or len(list((root/'cache').glob('*.json'))) != 1):
            raise ValueError('trial-cache-invalid')
        return dict(status='passed',modelInvocations=1,exactCacheReuse=True,rootOutput='0',activation=False,
                    noActivationRequested=True,ownedUnitsCleaned=True,authentication='fixed-root-trial-not-native-command-dialog')
    finally:
        subprocess.Popen=original
        cleanup_units(config,units)


def main(descriptor, dry_run=False):
    stage='configuration';root=None;receipt=None
    try:
        public=json.loads(immutable(descriptor).read_text())
        config=json.loads(immutable(public['config']).read_text())
        validate_config(public,config)
        if dry_run:
            print(json.dumps(dict(status='dry-run',modelInvocations=0,activation=False,
                                  proof='fixed-immutable-config-no-credential-access')))
            return 0
        stage='authentication';require_operator(config,os.geteuid(),os.environ.get('PKEXEC_UID'))
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,interrupt)
        signal.alarm(330)
        before=(str(Path('/run/current-system').resolve()),str(Path('/nix/var/nix/profiles/system').resolve()))
        stage='controller'
        spec=importlib.util.spec_from_file_location('command_trial_controller',immutable(public['controller']))
        deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
        stage='review-root-noop'
        with tempfile.TemporaryDirectory(prefix='phoenix-checkpoint-trial-',dir='/var/tmp') as directory:
            root=Path(directory)
            receipt=controlled_trial(deploy,config,public,root)
        after=(str(Path('/run/current-system').resolve()),str(Path('/nix/var/nix/profiles/system').resolve()))
        receipt.update(ownedStateCleaned=not root.exists(),runtimeObservedUnchanged=before[0]==after[0],
                       profileObservedUnchanged=before[1]==after[1])
        signal.alarm(0)
        print(json.dumps(receipt));return 0
    except Exception as error:
        signal.alarm(0)
        allowed={'operator-authentication-required','trial-config-invalid','immutable-input-required',
            'trial-interrupted','trial-unit-invalid','trial-cleanup-failed','trial-proof-invalid','trial-cache-invalid',
            'command-review-denied','command-review-error','command-review-timeout','command-review-authentication-missing',
            'command-review-authentication-failed','command-review-rate-limit-suspected','command-review-model-unavailable-suspected',
            'command-review-transport-failed-suspected','command-schema-invalid','command-binding-mismatch','command-context-compacted',
            'command-timeout','command-output-limit','command-cleanup-timeout','command-cleanup-failed'}
        candidate=getattr(error,'code',None) or str(error)
        print(json.dumps(dict(status='blocked-or-failed',stage=stage,code=candidate if candidate in allowed else 'trial-failed',
            modelInvocations='at-most-one' if stage=='review-root-noop' else 0,activation=False,
            ownedStateCleaned=root is None or not root.exists())))
        return 1


if __name__=='__main__':
    if len(sys.argv) not in (2,3) or (len(sys.argv)==3 and sys.argv[2]!='--dry-run'):
        raise SystemExit('fixed trial arguments required')
    raise SystemExit(main(sys.argv[1],len(sys.argv)==3))
