#!/usr/bin/env python3
"""Root-owned bounded security checkpoints, independent of activated source.

Call only while holding the deployment lock. Caller branch is an index hint,
never approval. Exact source identity, target and installed policy authorize reuse.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import tempfile

RETENTION = 32


def policy_digest(config):
    digest = hashlib.sha256()
    for key in ('policy', 'reviewScript', 'securityReviewScript', 'controller'):
        digest.update(key.encode() + b'\0' + Path(config[key]).read_bytes() + b'\0')
    # These are immutable installed execution identities/options. Changing the
    # sandbox, credentials identity, runtime or builder must invalidate approval.
    execution_keys = ('codex', 'model', 'effort', 'bwrap', 'python', 'setpriv', 'caBundle',
                      'reviewerUser', 'builderUser', 'nix', 'nixStore', 'systemdRun', 'target', 'system')
    digest.update(json.dumps({key: config.get(key) for key in execution_keys}, sort_keys=True).encode())
    return digest.hexdigest()


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
    exact, candidates = False, [(baseline, review.baseline_files(Path(baseline)))]
    for _, record in records(config, 'approved'):
        if record.get('policy') != policy or record.get('target') != target:
            continue
        approved_source = record.get('source')
        verify_source(approved_source, 'source')
        if approved_source == source and record.get('closure') == closure:
            verify_source(record['closure'], 'closure')
            exact = True
        if record.get('branch') == branch_key(branch):
            candidates.append((approved_source, review.baseline_files(Path(approved_source))))
    # Diff size is only a selection heuristic among independently approved states.
    selected = min(candidates, key=lambda item: len(review.source_diff(item[1], files).encode()))
    return exact, selected[0], selected[1]


def prune_orphan_roots(directory):
    # Crash leftovers never authorize and must not create unbounded GC retention.
    for path in directory.iterdir():
        match = re.fullmatch(r'([a-f0-9]{64})\.(approved|pending)\.(source|closure)', path.name)
        if match and not (directory / (match[1] + '.' + match[2] + '.json')).exists():
            path.unlink()


def retain(config, kind, identifier, record, run):
    directory = state_directory(config)
    prune_orphan_roots(directory)
    if kind not in {'approved', 'pending'} or not re.fullmatch('[a-f0-9]{64}', identifier):
        raise ValueError('invalid security record identity')
    # Retain exact immutable source and closure before publishing authorization.
    for field in ('source', 'closure'):
        root_path = directory / (identifier + '.' + kind + '.' + field)
        if root_path.is_symlink():
            if root_path.resolve(strict=True) != Path(record[field]):
                raise ValueError('security GC root mismatch')
        elif root_path.exists():
            raise ValueError('invalid security GC root')
        else:
            run([config['nixStore'], '--add-root', str(root_path), '--indirect', '--realise', record[field]])
    record = dict(record, timestamp=time.time())
    write_record(directory / (identifier + '.' + kind + '.json'), record)
    entries = records(config, 'approved') + records(config, 'pending')
    for path, old in sorted(entries, key=lambda item: item[1]['timestamp'], reverse=True)[RETENTION:]:
        path.unlink()
        prefix = path.name[:-5]
        for field in ('source', 'closure'):
            (directory / (prefix + '.' + field)).unlink(missing_ok=True)


def approve(config, binding, branch, run):
    record = {key: binding[key] for key in ('source', 'closure', 'target')}
    record.update(policy=policy_digest(config), branch=branch_key(branch))
    identifier = hashlib.sha256((record['policy'] + record['target'] + record['source'] + record['closure'] + record['branch']).encode()).hexdigest()
    retain(config, 'approved', identifier, record, run)


def pending(config, binding, uid, branch, code, summary, run):
    record = dict(binding, policy=policy_digest(config), uid=uid, branch=branch,
                  code=code, summary=summary[:1000])
    retain(config, 'pending', binding['nonce'], record, run)
    return binding['nonce']


def load_pending(config, nonce, uid, verify_source):
    if not re.fullmatch('[a-f0-9]{64}', nonce):
        raise ValueError('invalid pending nonce')
    record = read_record(state_directory(config) / (nonce + '.pending.json'))
    if record.get('nonce') != nonce or record.get('uid') != uid or record.get('policy') != policy_digest(config) or record.get('target') != config['target']:
        raise ValueError('pending decision identity/policy changed')
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
