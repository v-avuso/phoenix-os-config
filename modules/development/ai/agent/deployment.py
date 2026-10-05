#!/usr/bin/env python3
"""Protected controller: no caller verdict, command, environment or closure input.

The desktop UID is caller identity, not application identity. The bounded source
manifest bridges the worker's isolated Nix store; it is never privileged policy.
"""
import argparse
import contextlib
import hashlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import socket
import stat
import struct
import sys
import tempfile

LIMIT = 1024 * 1024
SOURCE_LIMIT = 896 * 1024
class DeploymentFailure(ValueError):
    def __init__(self, stage, code):
        self.stage, self.code = stage, code
        super().__init__(stage + ': ' + code)


class DeploymentDenied(DeploymentFailure):
    def __init__(self, summary):
        super().__init__('review', 'model-denied')
        self.summary = summary[:1000]
        self.affected_nodes = []


FIELDS = {'files', 'modes', 'commit', 'target', 'action', 'reason'}


def request_valid(request, target):
    if not isinstance(request, dict):
        raise ValueError('unsupported request fields')
    expected = FIELDS | ({'expectedBase', 'expectedProfile'} if request.get('action') in {'boot', 'update'} else set())
    if set(request) != expected:
        raise ValueError('unsupported request fields')
    if request['action'] not in {'test', 'switch', 'boot', 'update'} or request['target'] != target:
        raise ValueError('unsupported action/target')
    if not isinstance(request['reason'], str) or not 1 <= len(request['reason'].strip()) <= 2000:
        raise ValueError('concrete task reason required')
    if not isinstance(request['commit'], str) or not re.fullmatch('[0-9a-f]{40,64}', request['commit']):
        raise ValueError('invalid informational commit')
    if request['action'] in {'boot', 'update'}:
        store_path(request['expectedBase'], 'source')
        store_path(request['expectedProfile'], 'closure')
    files, modes = request['files'], request['modes']
    if not isinstance(files, dict) or not isinstance(modes, dict) or set(files) != set(modes):
        raise ValueError('invalid source manifest')
    if not {'flake.nix', 'flake.lock'} <= set(files) or len(files) > 2000:
        raise ValueError('invalid flake manifest')
    total = 0
    for name, content in files.items():
        if not isinstance(name, str) or not name or any(c in name for c in '\n\r\0'):
            raise ValueError('invalid source name')
        path = Path(name)
        if path.is_absolute() or any(p in {'.', '..', '.git'} for p in name.split('/')) or str(path) != name:
            raise ValueError('unsafe source name')
        if not isinstance(content, str) or modes[name] not in {'100644', '100755'}:
            raise ValueError('unsupported source type')
        total += len(content.encode())
    if any(str(parent) in files for name in files for parent in Path(name).parents if str(parent) != '.'):
        raise ValueError('file/directory prefix collision')
    if total > SOURCE_LIMIT:
        raise ValueError('source exceeds review bound')


def store_path(value, kind):
    pattern = r'/nix/store/[a-z0-9]{32}-' + (r'source' if kind == 'source' else r'nixos-system-[A-Za-z0-9._+-]+')
    if not re.fullmatch(pattern, value) or Path(value).resolve(strict=True) != Path(value):
        raise ValueError('invalid immutable ' + kind)
    info = Path(value).stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('untrusted store owner/mode')
    return value


def activation_executable(closure):
    executable = (Path(closure) / 'bin/switch-to-configuration').resolve(strict=True)
    if not str(executable).startswith('/nix/store/'):
        raise ValueError('activation executable escapes immutable store')
    info = executable.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or not info.st_mode & 0o111:
        raise ValueError('untrusted activation executable')
    return str(executable)


def frozen_github_reference(owner, repo, branch=None, directory=None):
    """Address the declared GitHub branch, including GitHub's default branch."""
    from urllib.parse import quote
    reference = 'github:%s/%s' % (owner, repo)
    if branch is not None:
        reference += '/' + quote(branch, safe='')
    if directory:
        reference += '?dir=' + quote(directory, safe='/')
    return reference


def activate(config, closure, action, run):
    activation_action = 'boot' if action == 'update' else action
    command = [closure + '/bin/switch-to-configuration', activation_action]
    if action == 'test':
        previous = str(Path('/run/current-system').resolve(strict=True))
        try:
            run(command, timeout=600, env=config['activationEnvironment'])
        except Exception:
            try:
                run([previous + '/bin/switch-to-configuration', 'test'], timeout=600,
                    env=config['activationEnvironment'])
            except Exception:
                raise DeploymentFailure('activation', 'rollback-incomplete') from None
            raise
        return
    profile = '/nix/var/nix/profiles/system'
    previous = str(Path(profile).resolve(strict=True))
    previous_runtime = str(Path('/run/current-system').resolve(strict=True))
    try:
        run([config['nixEnv'], '--profile', profile, '--set', closure], timeout=60)
        run(command, timeout=600, env=config['activationEnvironment'])
    except Exception:
        # Profile update can time out after changing the symlink. Recovery
        # therefore also covers that operation, and attempts every restore step.
        failures = []
        recovery = [
            ([config['nixEnv'], '--profile', profile, '--set', previous], 60, None),
            ([previous + '/bin/switch-to-configuration', 'boot'], 600, config['activationEnvironment']),
        ]
        # Boot staging never touched the running system or mutable desktop
        # baselines, including on failure. Do not turn rollback into activation.
        if action == 'switch':
            recovery.append(([previous_runtime + '/bin/switch-to-configuration', 'test'],
                             600, config['activationEnvironment']))
        for argv, timeout, env in recovery:
            try:
                run(argv, timeout=timeout, **({'env': env} if env is not None else {}))
            except Exception:
                failures.append(argv[0])
        if failures:
            raise DeploymentFailure('activation', 'rollback-incomplete') from None
        raise



def load_review(config):
    spec = importlib.util.spec_from_file_location('review', config['reviewScript'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def as_user(config, user, argv, run, **kwargs):
    account = pwd.getpwnam(user)
    return run([config['setpriv'], '--reuid', str(account.pw_uid), '--regid', str(account.pw_gid),
                '--clear-groups', '--no-new-privs', *argv], **kwargs)


def collect_upstream(upstream, action, before, after, resolve_locked, resolve_cli):
    """Manual deployments retain evidence for locked inputs and the reviewer CLI."""
    if action == 'update':
        return []
    batches = []
    if before.get('flake.lock') != after.get('flake.lock'):
        batches.extend(upstream.evidence(before, after, resolve_locked))
    batches.extend(upstream.cli_evidence(before, after, resolve_cli))
    return batches


def process(config, request, uid, pid, operator=False):
    state = {'stage': 'request'}
    try:
        request_valid(request, config['target'])
        if not config.get('modelReviewEnabled', True) and request['action'] != 'update':
            if not operator or os.geteuid() != 0:
                raise DeploymentFailure('authentication', 'operator-authentication-required')
        if config.get('work'):
            with (Path(config['work']).parent / 'deployment.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return process_inner(config, request, uid, pid, state)
        return process_inner(config, request, uid, pid, state)
    except DeploymentFailure:
        raise
    except Exception as error:
        # Static stage/type classifications only; never relay native stderr,
        # source strings, credentials or model-written summary as diagnostics.
        code = ('timeout' if isinstance(error, TimeoutError) else
                'invalid-json' if isinstance(error, json.JSONDecodeError) else
                'io-failed' if isinstance(error, OSError) else 'rejected-or-failed')
        raise DeploymentFailure(state['stage'], code) from None


def process_inner(config, request, uid, pid, state):
    request_valid(request, config['target'])
    review_required = request['action'] != 'update' and config.get('modelReviewEnabled', True)
    state['stage'] = 'freeze'
    review = load_review(config)
    reason_hash = hashlib.sha256(request['reason'].strip().encode()).hexdigest()
    print(json.dumps(dict(event='requested', uid=uid, pid=pid, action=request['action'],
                          target=request['target'], reason_sha256=reason_hash)), flush=True)
    with tempfile.TemporaryDirectory(prefix='request-', dir=config['work']) as directory:
        temporary = Path(directory)
        temporary.chmod(0o755)
        source = temporary / 'source'
        source.mkdir(mode=0o755)
        for name, content in request['files'].items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            for parent in path.parents:
                if parent == source.parent:
                    break
                parent.chmod(0o755)
            path.write_text(content)
            path.chmod(0o755 if request['modes'][name] == '100755' else 0o644)
        build_home = temporary / 'build'
        build_home.mkdir(mode=0o700)
        account = pwd.getpwnam(config['builderUser'])
        os.chown(build_home, account.pw_uid, account.pw_gid)
        env = {'HOME': str(build_home), 'PATH': '/nonexistent',
               'NIX_CONFIG': 'accept-flake-config = false\n'}
        source_store = as_user(config, config['builderUser'], [config['nix'], 'store', 'add-path', str(source)],
                               review.run, env=env).decode().strip()
        store_path(source_store, 'source')
        review.run([config['nixStore'], '--add-root', str(temporary / 'source-root'),
                    '--indirect', '--realise', source_store])
        if review.baseline_files(Path(source_store)) != request['files'] or review.source_modes(Path(source_store), request['files']) != request['modes']:
            raise ValueError('stored source differs from request')
        state['stage'] = 'baseline'
        baseline = str(Path(config['baseline']).resolve(strict=True))
        profile = str(Path('/nix/var/nix/profiles/system').resolve(strict=True))
        if request['action'] in {'boot', 'update'} and (request['expectedBase'] != baseline or request['expectedProfile'] != profile):
            raise ValueError('update baseline/profile changed before review')
        store_path(baseline, 'source')
        old = review.baseline_files(Path(baseline))
        store_path(profile, 'closure')
        profile_source = str((Path(profile) / 'etc/phoenix-agent/activated-source').resolve(strict=True))
        store_path(profile_source, 'source')
        # Boot staging may advance several times before reboot. Its root-owned
        # immutable source is the preceding approved dependency baseline; do not
        # repeatedly spend reviews on the same already-staged upstream changes.
        previous_dependencies = review.baseline_files(Path(profile_source))
        upstream_batches = []
        if request['action'] == 'update':
            state['stage'] = 'routine-policy'
            update_spec = importlib.util.spec_from_file_location('routine_update', config['routineUpdateScript'])
            update = importlib.util.module_from_spec(update_spec)
            update_spec.loader.exec_module(update)

            def evaluate_package(alias, revision, attribute, system):
                del alias  # The lock validator has already bound the selected root alias.
                ref = 'github:NixOS/nixpkgs/%s#legacyPackages.%s.%s.version' % (revision, system, attribute)
                return as_user(config, config['builderUser'], [config['nix'], 'eval', '--raw',
                    '--no-write-lock-file', ref], review.run, env=env, timeout=900).decode().strip()

            def verify_current_source(alias, node):
                original, locked = node.get('original', {}), node.get('locked', {})
                if alias is not None:
                    branches = {
                        'nixpkgs': original.get('ref'),
                        'nixpkgs-unstable': 'nixos-unstable',
                        'codex-desktop-linux': 'main',
                        'codex-desktop-sandbox': 'main',
                    }
                    branch = branches[alias]
                else:
                    if original.get('type') != 'github':
                        raise ValueError('changed dependency source type requires manual review')
                    branch = original.get('rev') or original.get('ref')
                owner, repo = original.get('owner'), original.get('repo')
                if (original.get('type') != 'github' or not isinstance(owner, str) or
                        not isinstance(repo, str) or (branch is not None and not isinstance(branch, str)) or
                        not re.fullmatch(r'[A-Za-z0-9_.-]+', owner) or
                        not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or
                        (branch is not None and not re.fullmatch(r'[A-Za-z0-9_./-]+', branch))):
                    raise ValueError('changed input has no supported frozen GitHub source')
                reference = frozen_github_reference(owner, repo, branch, original.get('dir'))
                metadata = json.loads(as_user(config, config['builderUser'],
                    [config['nix'], 'flake', 'metadata', '--json', '--no-write-lock-file', reference],
                    review.run, env=env, timeout=600))
                exact = metadata.get('locked', {})
                if any(exact.get(key) != locked.get(key) for key in ('owner', 'repo', 'rev', 'narHash')):
                    raise ValueError('candidate input is not the current declared publisher head')
                store_path(metadata['path'], 'source')
                if alias in {'codex-desktop-linux', 'codex-desktop-sandbox'}:
                    update.validate_community_payload(metadata['path'])
                    update.validate_community_checks(locked['rev'])

            def desktop_package_version(candidate_lock):
                node = update._node(candidate_lock, 'codex-desktop-linux')
                locked = node['locked']
                reference = 'github:%s/%s/%s?narHash=%s' % (
                    locked['owner'], locked['repo'], locked['rev'], locked['narHash'])
                metadata = json.loads(as_user(config, config['builderUser'],
                    [config['nix'], 'flake', 'metadata', '--json', '--no-write-lock-file', reference],
                    review.run, env=env, timeout=600))
                exact = metadata.get('locked', {})
                if any(exact.get(key) != locked.get(key) for key in ('owner', 'repo', 'rev', 'narHash')):
                    raise ValueError('community version source differs from candidate lock')
                store_path(metadata['path'], 'source')
                payload = json.loads((Path(metadata['path']) / 'nix/upstream-linux-packages.json').read_text())
                version = payload.get('version') if isinstance(payload, dict) else None
                if not isinstance(version, str) or not update.VERSION.fullmatch(version):
                    raise ValueError('community source has no stable version')
                return version

            def compare_versions(left, right):
                if not update.VERSION.fullmatch(left) or not update.VERSION.fullmatch(right):
                    raise ValueError('invalid stable version comparison')
                a, b = [int(part) for part in left.split('.')], [int(part) for part in right.split('.')]
                width = max(len(a), len(b))
                a.extend([0] * (width - len(a)))
                b.extend([0] * (width - len(b)))
                return (a > b) - (a < b)

            previous_modes = review.source_modes(Path(profile_source), previous_dependencies)
            update.validate_source(previous_dependencies, previous_modes, request['files'], request['modes'],
                                   config['system'], compare_versions, evaluate_package, desktop_package_version,
                                   verify_current_source)
        else:
            state['stage'] = 'upstream-evidence'
        if review_required:
            spec = importlib.util.spec_from_file_location('upstream_review', config['upstreamReviewScript'])
            upstream = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(upstream)
            def resolve_locked(locked):
                from urllib.parse import quote
                reference = 'github:%s/%s/%s?narHash=%s' % (locked['owner'], locked['repo'],
                    locked['rev'], quote(locked['narHash'], safe=''))
                metadata = json.loads(as_user(config, config['builderUser'],
                    [config['nix'], 'flake', 'metadata', '--json', '--no-write-lock-file', reference],
                    review.run, env=env, timeout=600))
                if any(metadata['locked'].get(k) != locked.get(k) for k in ('owner', 'repo', 'rev', 'narHash')):
                    raise ValueError('resolved upstream source does not match lock')
                store_path(metadata['path'], 'source')
                return metadata['path']
            def resolve_cli(version):
                record = json.loads(as_user(config, config['builderUser'],
                    [config['nix'], 'flake', 'prefetch', '--json', 'github:openai/codex/rust-v' + version],
                    review.run, env=env, timeout=600))
                store_path(record['storePath'], 'source')
                return record['storePath']
            upstream_batches = collect_upstream(upstream, request['action'], previous_dependencies,
                                                request['files'], resolve_locked, resolve_cli)
        if review_required and len(upstream_batches) > upstream.MAX_BATCHES:
            raise ValueError('combined upstream evidence exceeds batch bound')
        state['stage'] = 'build'
        print(json.dumps(dict(event='building', uid=uid, pid=pid, source=source_store)), flush=True)
        closure = as_user(config, config['builderUser'], [config['nix'], 'build', '--no-link', '--print-out-paths',
                          '--no-write-lock-file', '--option', 'accept-flake-config', 'false',
                          'path:' + source_store + '#nixosConfigurations.' + request['target'] + '.config.system.build.toplevel'],
                          review.run, env=env, timeout=3600).decode().strip()
        state['stage'] = 'closure-binding'
        store_path(closure, 'closure')
        activation_executable(closure)
        review.run([config['nixStore'], '--add-root', str(temporary / 'closure-root'),
                    '--indirect', '--realise', closure])
        if str((Path(closure) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != source_store:
            raise ValueError('closure does not record exact reviewed source')
        binding = {key: request[key] for key in ('commit', 'target', 'action', 'reason')}
        binding.update(source=source_store, base=baseline, profile=profile,
                       profileSource=profile_source, closure=closure, nonce=secrets.token_hex(32))
        if review_required:
            work = temporary / 'review'
            work.mkdir(mode=0o700)
            reviewer = pwd.getpwnam(config['reviewerUser'])
            os.chown(work, reviewer.pw_uid, reviewer.pw_gid)
            payload = {'binding': binding, 'files': request['files'],
                       'diff': review.source_diff(old, request['files'], review.source_modes(Path(baseline), old), request['modes']), 'upstreamBatches': upstream_batches,
                       'upstreamNodes': [getattr(batch, 'nodes', []) for batch in upstream_batches]}
            state['stage'] = 'review'
            print(json.dumps(dict(event='reviewing', uid=uid, pid=pid, source=source_store, closure=closure)), flush=True)
            output = as_user(config, config['reviewerUser'], [config['python'], '-I', config['controller'],
                             config['configPath'], 'worker', str(work)], review.run,
                             data=json.dumps(payload).encode(), timeout=min(7200, 700 * (len(upstream_batches) + 1)),
                             env={'HOME': config['reviewHome'], 'PATH': '/nonexistent'})
            state['stage'] = 'verdict'
            result = json.loads(output)
            if not isinstance(result, dict) or result.get('status') not in {'verdict', 'error'}:
                raise DeploymentFailure('verdict', 'worker-envelope-invalid')
            if result['status'] == 'error':
                code = result.get('code')
                if code not in {'reviewer-invocation-failed', 'schema-invalid', 'binding-mismatch',
                                'context-compacted', 'review-context-oversized', 'upstream-model-denied'}:
                    code = 'worker-envelope-invalid'
                raise DeploymentFailure('review', code)
            verdict = result.get('verdict')
            if 'upstreamDenialIndex' in result:
                index = result['upstreamDenialIndex']
                if type(index) is not int or not 0 <= index < len(upstream_batches):
                    raise DeploymentFailure('verdict', 'upstream-denial-index')
                try:
                    review.validate_verdict(verdict, upstream_binding(binding, upstream_batches[index], index, getattr(upstream_batches[index], 'nodes', [])))
                except review.ReviewDenied as error:
                    denial = DeploymentDenied(error.verdict['summary'])
                    denial.affected_nodes = getattr(upstream_batches[index], 'nodes', [])
                    raise denial from None
                except review.ReviewVerdictError as error:
                    raise DeploymentFailure('verdict', error.code) from None
                raise DeploymentFailure('verdict', 'upstream-denial-approved')
            try:
                upstream_verdicts = result.get('upstreamVerdicts', [])
                if not isinstance(upstream_verdicts, list) or len(upstream_verdicts) != len(upstream_batches):
                    raise DeploymentFailure('verdict', 'upstream-verdict-count')
                for index, (batch, upstream_verdict) in enumerate(zip(upstream_batches, upstream_verdicts)):
                    review.validate_verdict(upstream_verdict, upstream_binding(binding, batch, index, getattr(batch, 'nodes', [])))
                review.validate_verdict(verdict, binding)
            except review.ReviewDenied as error:
                raise DeploymentDenied(error.verdict['summary']) from None
            except review.ReviewVerdictError as error:
                raise DeploymentFailure('verdict', error.code) from None
        state['stage'] = 'baseline-recheck'
        if str(Path(config['baseline']).resolve(strict=True)) != baseline:
            raise ValueError('activated baseline changed during review')
        if str(Path('/nix/var/nix/profiles/system').resolve(strict=True)) != profile:
            raise ValueError('boot profile changed during review')
        if str((Path(profile) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != profile_source:
            raise ValueError('approved profile source changed during review')
        print(json.dumps(dict(event='approved', uid=uid, pid=pid, source=source_store,
                              closure=closure, action=request['action'], target=request['target'])), flush=True)
        # Upstream transient service owns activation even if the new system
        # explicitly changes/removes this controller. No shell or caller unit name.
        state['stage'] = 'activation'
        # A temporary-tested prior runtime may have no profile generation. Keep
        # it alive after candidate activation moves the current-system GC root.
        previous_runtime = str(Path('/run/current-system').resolve(strict=True))
        store_path(previous_runtime, 'closure')
        review.run([config['nixStore'], '--add-root', str(temporary / 'rollback-runtime-root'),
                    '--indirect', '--realise', previous_runtime])
        review.run([config['systemdRun'], '--quiet', '--wait', '--collect',
                    '--service-type=exec', '--property=RuntimeMaxSec=2100', '--property=TimeoutStopSec=15s',
                    '--unit=phoenix-deploy-activation-' + binding['nonce'],
                    config['python'], '-I', config['controller'], config['configPath'],
                    'activate', closure, request['action'], '--expected-base', baseline,
                    '--expected-source', source_store, '--expected-profile', profile], timeout=2200)

        return dict(ok=True, source=source_store, closure=closure, action=request['action'])


def upstream_binding(binding, batch, index, nodes=None):
    return dict(binding, scope='upstream-authority-' + str(index),
                evidenceDigest=hashlib.sha256(batch.encode()).hexdigest(), affectedInputNodes=json.dumps(nodes or [], separators=(',', ':')))


def worker(config, directory):
    review = load_review(config)
    payload = json.load(sys.stdin)
    temporary = Path(directory)
    # Source modes are read by the shared reviewer from this immutable link.
    (temporary / 'source').symlink_to(payload['binding']['source'], target_is_directory=True)
    try:
        upstream_verdicts = []
        for index, batch in enumerate(payload.get('upstreamBatches', [])):
            scoped = temporary / ('upstream-' + str(index))
            scoped.mkdir(mode=0o700)
            (scoped / 'source').symlink_to(payload['binding']['source'], target_is_directory=True)
            upstream_verdicts.append(review.review(config,
                upstream_binding(payload['binding'], batch, index, payload.get('upstreamNodes', [[]]*len(payload['upstreamBatches']))[index]), {}, batch, scoped))
        verdict = review.review(config, payload['binding'], payload['files'], payload['diff'], temporary)
        result = dict(status='verdict', verdict=verdict)
        if upstream_verdicts:
            result['upstreamVerdicts'] = upstream_verdicts
    except review.ReviewDenied as error:
        result = dict(status='verdict', verdict=error.verdict)
        if 'scope' in error.verdict:
            result['upstreamDenialIndex'] = index
        elif upstream_verdicts:
            result['upstreamVerdicts'] = upstream_verdicts
    except review.ReviewVerdictError as error:
        result = dict(status='error', code=error.code)
    except Exception:
        # Do not reflect native/API stderr, which may contain credentials.
        result = dict(status='error', code='reviewer-invocation-failed')
    print(json.dumps(result))


def serve(config):
    if os.getuid() != 0:
        raise ValueError('controller requires installed root service')
    listener = socket.socket(fileno=3)  # systemd socket activation; no caller path.
    while True:
        connection, _ = listener.accept()
        uid = pid = -1
        try:
            pid, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != config['clientUid']:
                raise ValueError('caller UID denied')
            connection.settimeout(10)
            data = bytearray()
            while not data.endswith(b'\n'):
                block = connection.recv(min(65536, LIMIT + 1 - len(data)))
                if not block or len(data) > LIMIT:
                    raise ValueError('incomplete or oversized request')
                data.extend(block)
                if len(data) > LIMIT:
                    raise ValueError('oversized request')
            result = process(config, json.loads(data), uid, pid)
            print(json.dumps(dict(event='activated', uid=uid, pid=pid, **result)), flush=True)
        except Exception as error:
            # Avoid attacker strings, model output, task contents or credentials in journal.
            stage = error.stage if isinstance(error, DeploymentFailure) else 'protocol'
            code = error.code if isinstance(error, DeploymentFailure) else 'invalid-or-denied'
            print(json.dumps(dict(event='failed', uid=uid, pid=pid, stage=stage, code=code)), flush=True)
            result = dict(ok=False, stage=stage, code=code, error='Deployment failed at ' + stage + ' (' + code + ').')
            if isinstance(error, DeploymentDenied):
                result['summary'] = error.summary
                result['affectedInputNodes'] = error.affected_nodes
        try:
            connection.sendall(json.dumps(result).encode() + b'\n')
        except OSError:
            pass
        finally:
            connection.close()


def bootstrap(config):
    if os.getuid() != 0:
        raise ValueError('bootstrap requires graphical Polkit authentication')
    marker = Path(config['migrationMarker'])
    if marker.is_file() and (Path(config['reviewHome']) / 'auth.json').is_file():
        print('Reviewer authentication already belongs to protected controller; no login repeated.')
        return
    home_fd = os.open(config['loginHome'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    migration_lock = None
    try:
        migration_lock = os.open('migration.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=home_fd)
        lock_info = os.fstat(migration_lock)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1 or lock_info.st_uid not in {0, config['clientUid']}:
            raise ValueError('unsafe migration lock')
        os.fchown(migration_lock, config['clientUid'], -1)
        os.fchmod(migration_lock, 0o600)
        fcntl.flock(migration_lock, fcntl.LOCK_EX)
        bootstrap_transfer(config, home_fd)
    finally:
        if migration_lock is not None:
            os.close(migration_lock)
        os.close(home_fd)


def bootstrap_transfer(config, home_fd):
    marker = Path(config['migrationMarker'])
    fd = os.open('auth.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=home_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != config['clientUid'] or info.st_nlink != 1 or info.st_size > 65536:
            raise ValueError('invalid retained reviewer authentication')
        data = os.read(fd, 65537)
        json.loads(data)
    finally:
        os.close(fd)
    home = Path(config['reviewHome'])
    home_info = home.lstat()
    account = pwd.getpwnam(config['reviewerUser'])
    if not stat.S_ISDIR(home_info.st_mode) or home_info.st_uid != account.pw_uid or home_info.st_mode & 0o077:
        raise ValueError('unsafe protected reviewer home')
    # Atomic replacement never truncates a pre-existing symlink/hardlink target.
    fd, name = tempfile.mkstemp(prefix='.auth-', dir=home)
    try:
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
        os.fchown(fd, account.pw_uid, account.pw_gid)
        os.fchmod(fd, 0o600)
        os.close(fd)
        fd = None
        os.replace(name, home / 'auth.json')
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(name):
            os.unlink(name)
    # Re-check the exact opened inode before removing only its legacy name.
    current = os.stat('auth.json', dir_fd=home_fd, follow_symlinks=False)
    if (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size) != (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size):
        raise ValueError('legacy reviewer state changed during ownership transfer')
    marker_fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        os.fchmod(marker_fd, 0o644)
        os.write(marker_fd, b'Protected reviewer owns retained authentication.\n')
        os.fsync(marker_fd)
    finally:
        os.close(marker_fd)
    os.unlink('auth.json', dir_fd=home_fd)
    print('Protected reviewer authentication transferred; legacy refresh disabled; no credentials emitted.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('mode', choices=['serve', 'worker', 'bootstrap', 'activate', 'operator'])
    parser.add_argument('directory', nargs='?')
    parser.add_argument('action', nargs='?', choices=['test', 'switch', 'boot', 'update'])
    parser.add_argument('--expected-base')
    parser.add_argument('--expected-source')
    parser.add_argument('--expected-profile')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    config['configPath'] = args.config
    if args.mode == 'operator':
        # This route is entered only via the immutable graphical Polkit command.
        # The ordinary socket never treats disabled model review as approval.
        if os.geteuid() != 0 or config.get('modelReviewEnabled', True):
            raise ValueError('operator route requires root and explicitly disabled model review')
        data = sys.stdin.buffer.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('operator request exceeds transport bound')
        request = json.loads(data)
        if request.get('action') not in {'test', 'switch', 'boot'}:
            raise ValueError('operator route only accepts manual deployment actions')
        with contextlib.redirect_stdout(sys.stderr):
            result = process(config, request, int(os.environ.get('PKEXEC_UID', '0')), os.getpid(), operator=True)
        print(json.dumps(result))
    elif args.mode == 'activate':
        if os.getuid() != 0 or args.action is None:
            raise ValueError('activation is root-controller only')
        store_path(args.directory, 'closure')
        activation_executable(args.directory)
        if not args.expected_base or not args.expected_source:
            raise DeploymentFailure('activation', 'missing-binding')
        store_path(args.expected_source, 'source')
        if str(Path(config['baseline']).resolve(strict=True)) != args.expected_base:
            raise DeploymentFailure('activation', 'baseline-changed')
        if not args.expected_profile or str(Path('/nix/var/nix/profiles/system').resolve(strict=True)) != args.expected_profile:
            raise DeploymentFailure('activation', 'profile-changed')
        if str((Path(args.directory) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != args.expected_source:
            raise DeploymentFailure('activation', 'source-mismatch')
        activate(config, args.directory, args.action, load_review(config).run)
    elif args.mode == 'worker':
        worker(config, args.directory)
    elif args.mode == 'bootstrap':
        bootstrap(config)
    else:
        serve(config)


if __name__ == '__main__':
    main()
