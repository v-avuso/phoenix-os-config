#!/usr/bin/env python3
"""Root-owned bounded security checkpoints, independent of activated source.

Call only while holding the deployment lock. Caller branch is metadata only,
never approval. Exact source identity, target and installed policy authorize reuse.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
import tempfile

RETENTION = 32


class ApprovalBaselineRequired(ValueError):
    """Activation markers are not protected security approval records."""


def legacy_policy_digest(config):
    digest = hashlib.sha256()
    for key in ('policy', 'reviewScript', 'securityReviewScript', 'controller'):
        digest.update(key.encode() + b'\0' + Path(config[key]).read_bytes() + b'\0')
    for key in ('authorizationLibrary', 'deploymentTransportPolicy', 'sourceManifestLibrary'):
        if config.get(key):
            digest.update(key.encode() + b'\0' + Path(config[key]).read_bytes() + b'\0')
    # These are immutable installed execution identities/options. Changing the
    # sandbox, credentials identity, runtime or builder must invalidate approval.
    execution_keys = ('adapter', 'clientUid', 'operatorUid', 'updaterUid', 'modelReviewEnabled',
                      'reservations', 'disruptionGuard', 'activationEnvironment', 'codex', 'model', 'effort', 'bwrap', 'python', 'setpriv', 'caBundle',
                      'reviewerUser', 'builderUser', 'nix', 'nixStore', 'systemdRun', 'target', 'system')
    digest.update(json.dumps({key: config.get(key) for key in execution_keys}, sort_keys=True).encode())
    authority = config.get('authorizationPolicy')
    if isinstance(authority, str):
        digest.update(b'authorizationPolicy\0' + Path(authority).read_bytes())
    elif authority is not None:
        digest.update(b'authorizationPolicy\0' + json.dumps(authority, sort_keys=True).encode())
    return digest.hexdigest()


TOOL_KEYS = ('python', 'nix', 'nixStore', 'nixEnv', 'bwrap', 'setpriv',
             'systemdRun', 'systemctl', 'codex', 'caBundle', 'targetGuard')
HELPER_BINDINGS = {'AUTHORIZATION_PATH': 'authorizationLibrary',
                   'TRANSPORT_PATH': 'deploymentTransportPolicy',
                   'SOURCE_MANIFEST_PATH': 'sourceManifestLibrary'}


def identity_version(config):
    version = config.get('securityIdentityVersion', 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError('security-identity-version-unsupported')
    return version


def authority_bytes(config, key):
    data = Path(config[key]).read_bytes()
    if key not in ('controller', 'reviewScript'):
        return data
    # Canonicalize only standalone, declared helper assignments. All surrounding
    # code and the referenced helpers' bytes remain part of authority.
    text = data.decode()
    tree = ast.parse(text)
    replacements = []
    lines = text.splitlines(keepends=True)
    for name, field in HELPER_BINDINGS.items():
        if not config.get(field):
            continue  # Repository-only legacy fixtures have no packaged helpers.
        matches = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
        if len(matches) != 1:
            raise ValueError('authority-helper-binding-invalid')
        node = matches[0]
        if (len(node.targets) != 1 or not isinstance(node.value, ast.Constant)
                or node.value.value != config[field] or node.lineno != node.end_lineno):
            raise ValueError('authority-helper-binding-invalid')
        line = lines[node.lineno - 1]
        # AST columns count UTF-8 bytes. Rewrite only the literal, not the line.
        raw = line.encode()
        replacements.append((node.lineno - 1, raw[:node.value.col_offset] +
                             json.dumps('@' + field + '@').encode() + raw[node.value.end_col_offset:]))
    lines = text.splitlines(keepends=True)
    for index, replacement in replacements:
        lines[index] = replacement.decode()
    return ''.join(lines).encode()


def policy_digest(config):
    if identity_version(config) == 1:
        return legacy_policy_digest(config)
    digest = hashlib.sha256(b'phoenix-security-authority-v2\0')
    for key in ('policy', 'reviewScript', 'securityReviewScript', 'controller', 'routineUpdateScript',
                'authorizationLibrary', 'deploymentTransportPolicy', 'sourceManifestLibrary',
                'disruptionScript', 'commandLibrary', 'commandReviewPolicy', 'commandExec'):
        if config.get(key):
            digest.update(key.encode() + b'\0' + authority_bytes(config, key) + b'\0')
    keys = ('adapter', 'clientUid', 'operatorUid', 'updaterUid', 'modelReviewEnabled',
            'reservations', 'disruptionGuard', 'activationEnvironment', 'model', 'effort',
            'reviewerUser', 'builderUser', 'target', 'system', 'commands', 'commandCurrentAuthority',
            'securityReviewState', 'reviewHome', 'work', 'baseline', 'activationLock', 'activationSpool',
            'commandState', 'disruptionState', 'disruptionInfo')
    settings = {key: config.get(key) for key in keys}
    if config.get('reservations'):
        settings['reservations'] = dict(config['reservations'])
        for key in ('engine', 'adapter'):
            digest.update(('reservations.' + key).encode() + b'\0' +
                          Path(settings['reservations'][key]).read_bytes() + b'\0')
            settings['reservations'][key] = '@' + key + '@'
    digest.update(json.dumps(settings, sort_keys=True).encode())
    # Roles and environment variable names are authority; their immutable package
    # paths are execution identity. A distributor update cannot add a new role.
    digest.update(json.dumps({key: bool(config.get(key)) for key in TOOL_KEYS}, sort_keys=True).encode())
    digest.update(json.dumps(sorted(config.get('activationEnvironmentTools', {}))).encode())
    if set(config.get('activationEnvironmentTools', {})) & set(config.get('activationEnvironment', {})):
        raise ValueError('activation-environment-overlap')
    authority = config.get('authorizationPolicy')
    if isinstance(authority, str):
        digest.update(b'authorizationPolicy\0' + Path(authority).read_bytes())
    elif authority is not None:
        digest.update(b'authorizationPolicy\0' + json.dumps(authority, sort_keys=True).encode())
    return digest.hexdigest()


def toolchain_digest(config):
    if identity_version(config) != 2:
        raise ValueError('toolchain-identity-version-required')
    value = {key: config.get(key) for key in TOOL_KEYS}
    value['activationEnvironmentTools'] = config.get('activationEnvironmentTools', {})
    return hashlib.sha256(b'phoenix-execution-v2\0' + json.dumps(value, sort_keys=True).encode()).hexdigest()


def record_identity(config):
    return dict(identityVersion=2, toolchain=toolchain_digest(config)) if identity_version(config) == 2 else {}


def bound_config(record, verify_source):
    source, closure = record['source'], record['closure']
    verify_source(source, 'source')
    verify_source(closure, 'closure')
    if str((Path(closure) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != source:
        raise ValueError('approval-closure-source-invalid')
    actual = closure_config(closure)
    if (identity_version(actual) != 2 or record.get('identityVersion') != 2
            or record.get('policy') != policy_digest(actual)
            or record.get('toolchain') != toolchain_digest(actual)
            or record.get('target') != actual['target']):
        raise ValueError('approval-identity-binding-invalid')
    return actual


def approved_predecessor(config, predecessor, verify_source):
    for _, record in records(config, 'approved'):
        if record.get('policy') != policy_digest(config) or record.get('target') != config['target']:
            continue
        choices = [record]
        if record.get('origin') == 'distributor-update':
            choices.append(record.get('predecessorApproval', {}))
        match = next((value for value in choices if all(value.get(key) == predecessor[key]
                                                      for key in ('source', 'closure'))), None)
        if match is not None:
            validate_transition(config, record, verify_source)
            # Root-issued compact evidence also survives pruning of the original
            # record. Validate its containing receipt before using that evidence.
            return {key: match[key] for key in ('identityVersion', 'policy', 'toolchain', 'target', 'source', 'closure')}
    raise ValueError('approved-predecessor-required')


def approve_update(config, binding, predecessor, branch, run, verify_source, before_publish=None):
    if os.geteuid() != 0 or identity_version(config) != 2 or binding.get('action') != 'update':
        raise ValueError('validated-update-root-entry-required')
    previous = approved_predecessor(config, predecessor, verify_source)
    successor = closure_config(binding['closure'])
    if policy_digest(successor) != policy_digest(config):
        raise ValueError('update-policy-changed')
    record = {key: binding[key] for key in ('source', 'closure', 'target')}
    record.update(record_identity(successor), policy=policy_digest(config), branch=branch_key(branch),
                  origin='distributor-update', predecessorSource=previous['source'],
                  predecessorClosure=previous['closure'], predecessorToolchain=previous['toolchain'],
                  predecessorApproval=previous)
    validate_transition(config, record, verify_source)
    identifier = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    retain(config, 'approved', identifier, record, run, before_publish)


def immutable_file(path):
    if not isinstance(path, (str, Path)):
        raise ValueError('transition-immutable-metadata-required')
    path = Path(path).resolve(strict=True)
    info = path.stat()
    if not str(path).startswith('/nix/store/') or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('transition-immutable-metadata-required')
    return path


def closure_config(closure):
    unit = immutable_file(Path(closure) / 'etc/systemd/system/phoenix-deploy.service')
    starts = [line.split('=', 1)[1] for line in unit.read_text().splitlines() if line.startswith('ExecStart=')]
    if len(starts) != 1:
        raise ValueError('transition-controller-binding-invalid')
    argv = shlex.split(starts[0])
    if len(argv) != 5 or argv[1] != '-I' or argv[4] != 'serve':
        raise ValueError('transition-controller-binding-invalid')
    config = json.loads(immutable_file(argv[3]).read_text())
    if not isinstance(config, dict):
        raise ValueError('transition-controller-binding-invalid')
    if argv != [config['python'], '-I', config['controller'], argv[3], 'serve']:
        raise ValueError('transition-controller-binding-invalid')
    for key in ('policy', 'reviewScript', 'securityReviewScript', 'controller',
                'authorizationLibrary', 'deploymentTransportPolicy', 'sourceManifestLibrary', 'authorizationPolicy',
                'routineUpdateScript', 'disruptionScript', 'commandLibrary', 'commandReviewPolicy', 'commandExec',
                *TOOL_KEYS):
        if config.get(key):
            immutable_file(config[key])
    if config.get('reservations'):
        for key in ('engine', 'adapter'):
            immutable_file(config['reservations'][key])
    for value in config.get('activationEnvironmentTools', {}).values():
        immutable_file(value)
    return dict(config, configPath=argv[3])


def validate_transition(config, record, verify_source):
    """Verify a root-published, human-authorized receipt without relabelling history.

    The predecessor approval is embedded because ordinary retention can prune its
    separate record. Root-only publication supplies provenance; no caller receipt
    or reviewer verdict can enter this path through the deployment socket.
    """
    if identity_version(config) == 2:
        if record.get('policy') != policy_digest(config) or record.get('target') != config['target']:
            raise ValueError('approval-policy-binding-invalid')
        bound_config(record, verify_source)
        if record.get('origin') == 'distributor-update':
            previous = record.get('predecessorApproval')
            expected = {'identityVersion', 'policy', 'toolchain', 'target', 'source', 'closure'}
            if (not isinstance(previous, dict) or set(previous) != expected or
                    previous.get('source') != record.get('predecessorSource') or
                    previous.get('closure') != record.get('predecessorClosure') or
                    previous.get('toolchain') != record.get('predecessorToolchain') or
                    previous.get('policy') != record['policy'] or previous.get('target') != record['target'] or
                    'transition' in record):
                raise ValueError('update-predecessor-binding-invalid')
            bound_config(previous, verify_source)
            return
    elif 'identityVersion' in record or record.get('origin') == 'distributor-update':
        raise ValueError('approval-identity-version-invalid')
    if record.get('origin') != 'administrator-reviewed-transition':
        if 'transition' in record:
            raise ValueError('transition-origin-invalid')
        return
    proof = record.get('transition')
    if not isinstance(proof, dict) or set(proof) != {'version', 'administratorUid', 'predecessorPolicy', 'predecessorCheckpoint', 'successorPolicy', 'source', 'closure', 'target'}:
        raise ValueError('transition-receipt-invalid')
    if type(proof['version']) is not int or proof['version'] != 1 or type(proof['administratorUid']) is not int or proof['administratorUid'] != config['operatorUid']:
        raise ValueError('transition-administrator-invalid')
    for field in ('source', 'closure', 'target'):
        if proof[field] != record[field]:
            raise ValueError('transition-successor-binding-invalid')
    if proof['successorPolicy'] != record['policy'] or record['policy'] != policy_digest(config) or (proof['predecessorPolicy'] == record['policy'] and identity_version(config) == 1):
        raise ValueError('transition-policy-binding-invalid')
    previous = proof['predecessorCheckpoint']
    if not isinstance(previous, dict) or any(previous.get(key) != value for key, value in
            (('policy', proof['predecessorPolicy']), ('target', record['target']),
             ('source', record.get('predecessorSource')), ('closure', record.get('predecessorClosure')))):
        raise ValueError('transition-predecessor-binding-invalid')
    for prefix in ('', 'predecessor'):
        source = record['source' if not prefix else 'predecessorSource']
        closure = record['closure' if not prefix else 'predecessorClosure']
        verify_source(source, 'source')
        verify_source(closure, 'closure')
        if str((Path(closure) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != source:
            raise ValueError('transition-closure-source-invalid')
    predecessor_config = closure_config(record['predecessorClosure'])
    if (proof['predecessorPolicy'] == record['policy'] and
            toolchain_digest(predecessor_config) == record['toolchain']):
        raise ValueError('transition-unchanged-identity')
    if policy_digest(predecessor_config) != proof['predecessorPolicy']:
        raise ValueError('transition-predecessor-policy-invalid')
    if policy_digest(closure_config(record['closure'])) != proof['successorPolicy']:
        raise ValueError('transition-successor-policy-invalid')


def approve_transition(config, binding, branch, run, *, predecessor_policy, predecessor_source,
                       predecessor_closure, uid, verify_source):
    if os.geteuid() != 0 or uid != config['operatorUid'] or not config.get('modelReviewEnabled'):
        raise ValueError('transition-native-administrator-required')
    previous = next((record for _, record in records(config, 'approved')
                     if all(record.get(key) == value for key, value in
                            (('policy', predecessor_policy), ('target', config['target']),
                             ('source', predecessor_source), ('closure', predecessor_closure)))), None)
    if previous is None:
        raise ValueError('transition-predecessor-approval-required')
    validate_transition(closure_config(predecessor_closure), previous, verify_source)
    # Retain only exact predecessor evidence, not a recursive chain of receipts.
    previous = {key: previous[key] for key in ('policy', 'target', 'source', 'closure')}
    record = {key: binding[key] for key in ('source', 'closure', 'target')}
    record.update(policy=policy_digest(config), branch=branch_key(branch),
                  origin='administrator-reviewed-transition', predecessorSource=predecessor_source,
                  predecessorClosure=predecessor_closure)
    record.update(record_identity(config))
    record['transition'] = dict(version=1, administratorUid=uid, predecessorPolicy=predecessor_policy,
        predecessorCheckpoint=previous, successorPolicy=record['policy'], **{key: record[key] for key in ('source', 'closure', 'target')})
    validate_transition(config, record, verify_source)
    identifier = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    retain(config, 'approved', identifier, record, run)


def state_directory(config):
    if os.geteuid() != 0:
        raise ValueError('security state is root-only')
    path = Path(config['securityReviewState'])
    # Provisioned by the installed system, not created beneath caller directories.
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError('untrusted security state directory')
    return path


def read_record(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 16384:
            raise ValueError('untrusted security state record')
        value = json.loads(os.read(fd, 16385))
        if not isinstance(value, dict):
            raise ValueError('invalid security state record')
        return value
    finally:
        os.close(fd)


def write_record(path, record):
    fd, temporary_name = tempfile.mkstemp(prefix='.record-', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            data = json.dumps(record, sort_keys=True).encode()
            if len(data) > 16384:
                raise ValueError('security state record oversized')
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def branch_key(branch):
    return hashlib.sha256(branch.encode()).hexdigest()


def records(config, suffix):
    directory = state_directory(config)
    result = []
    for path in sorted(directory.glob('*.' + suffix + '.json')):
        result.append((path, read_record(path)))
    return result


def choose_checkpoint(config, target, source, closure, branch, baseline, files, review, verify_source):
    policy = policy_digest(config)
    exact, candidates = False, []
    for _, record in records(config, 'approved'):
        if record.get('policy') != policy or record.get('target') != target:
            continue
        validate_transition(config, record, verify_source)
        approved_source = record.get('source')
        verify_source(approved_source, 'source')
        approved_closure = record.get('closure')
        verify_source(approved_closure, 'closure')
        if str((Path(approved_closure) / 'etc/phoenix-agent/activated-source').resolve(strict=True)) != approved_source:
            raise ValueError('approved closure/source binding changed')
        if approved_source == source and approved_closure == closure:
            exact = True
        # Every candidate is independently approved under this policy and target.
        # Branch labels never limit authority, nor authorize merged combinations.
        candidates.append((approved_source, review.baseline_files(Path(approved_source))))
    if not candidates:
        raise ApprovalBaselineRequired('explicit reviewed checkpoint transition required for installed policy')
    # Diff size is only a selection heuristic among independently approved states.
    candidate_modes = review.source_modes(Path(source), files)
    selected = min(candidates, key=lambda item: len(review.source_diff(
        item[1], files, review.source_modes(Path(item[0]), item[1]), candidate_modes).encode()))
    return exact, selected[0], selected[1]


def prune_orphan_roots(directory):
    # Crash leftovers never authorize and must not create unbounded GC retention.
    for path in directory.iterdir():
        match = re.fullmatch(r'([a-f0-9]{64})\.(approved|pending)\.(source|closure|predecessorSource|predecessorClosure)', path.name)
        if match and not (directory / (match[1] + '.' + match[2] + '.json')).exists():
            path.unlink()


def retain(config, kind, identifier, record, run, before_publish=None):
    directory = state_directory(config)
    prune_orphan_roots(directory)
    if kind not in {'approved', 'pending'} or not re.fullmatch('[a-f0-9]{64}', identifier):
        raise ValueError('invalid security record identity')
    # Retain exact immutable source and closure before publishing authorization.
    for field in ('source', 'closure', 'predecessorSource', 'predecessorClosure'):
        if field not in record:
            continue
        root_path = directory / (identifier + '.' + kind + '.' + field)
        if root_path.is_symlink():
            if root_path.resolve(strict=True) != Path(record[field]):
                raise ValueError('security GC root mismatch')
        elif root_path.exists():
            raise ValueError('invalid security GC root')
        else:
            run([config['nixStore'], '--add-root', str(root_path), '--indirect', '--realise', record[field]])
    if before_publish is not None:
        before_publish()
    record = dict(record, timestamp=time.time())
    write_record(directory / (identifier + '.' + kind + '.json'), record)
    entries = records(config, 'approved') + records(config, 'pending')
    for path, old in sorted(entries, key=lambda item: item[1]['timestamp'], reverse=True)[RETENTION:]:
        path.unlink()
        prefix = path.name[:-5]
        for field in ('source', 'closure', 'predecessorSource', 'predecessorClosure'):
            (directory / (prefix + '.' + field)).unlink(missing_ok=True)


def approve(config, binding, branch, run, before_publish=None):
    record = {key: binding[key] for key in ('source', 'closure', 'target')}
    identity = {}
    if identity_version(config) == 2:
        successor = closure_config(binding['closure'])
        if policy_digest(successor) != policy_digest(config):
            raise ValueError('approval-policy-binding-invalid')
        identity = record_identity(successor)
    record.update(policy=policy_digest(config), branch=branch_key(branch), **identity)
    identifier = hashlib.sha256((record['policy'] + record['target'] + record['source'] + record['closure'] + record['branch']).encode()).hexdigest()
    retain(config, 'approved', identifier, record, run, before_publish)


def pending(config, binding, uid, branch, code, summary, run):
    record = dict(binding, policy=policy_digest(config), **record_identity(config), uid=uid, branch=branch,
                  code=code, summary=summary[:1000])
    retain(config, 'pending', binding['nonce'], record, run)
    return binding['nonce']


def load_pending(config, nonce, uid, verify_source):
    if not re.fullmatch('[a-f0-9]{64}', nonce):
        raise ValueError('invalid pending nonce')
    record = read_record(state_directory(config) / (nonce + '.pending.json'))
    if record.get('nonce') != nonce or record.get('uid') != uid or record.get('policy') != policy_digest(config) or record.get('target') != config['target']:
        raise ValueError('pending decision identity/policy changed')
    if identity_version(config) == 2 and any(record.get(key) != value for key, value in record_identity(config).items()):
        raise ValueError('pending-toolchain-identity-changed')
    if record.get('action') not in {'test', 'switch', 'boot'}:
        raise ValueError('pending decision action invalid')
    for field, kind in (('source', 'source'), ('closure', 'closure'), ('base', 'source'), ('profile', 'closure')):
        verify_source(record[field], kind)
    return record


def consume_pending(config, nonce):
    directory = state_directory(config)
    # Publishing approval can prune this older pending record at retention capacity.
    (directory / (nonce + '.pending.json')).unlink(missing_ok=True)
    for field in ('source', 'closure'):
        (directory / (nonce + '.pending.' + field)).unlink(missing_ok=True)
