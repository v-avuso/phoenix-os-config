#!/usr/bin/env python3
"""Bounded immutable unit comparison; never executes candidate activation scripts."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

STORE = re.compile(r'/nix/store/[a-z0-9]{32}-[^/\s]+(?:/[^\s]*)?')


class InspectionRequired(ValueError):
    pass


def immutable(path):
    path = Path(path).resolve(strict=True)
    if not STORE.fullmatch(str(path)):
        raise InspectionRequired('unsupported-immutable-layout')
    info = path.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise InspectionRequired('untrusted-immutable-artifact')
    return path


def content(path):
    path = immutable(path)
    if not path.is_file() or path.stat().st_size > 256 * 1024:
        raise InspectionRequired('unsupported-unit-artifact')
    return path.read_bytes()


def unit_artifacts(directory, name):
    directory = immutable(directory)
    result = {}
    unit = directory / name
    if not unit.exists() and '@' in name and not name.split('@', 1)[1].startswith('.'):
        unit = directory / (name.split('@', 1)[0] + '@.' + name.rsplit('.', 1)[1])
    if unit.exists() or unit.is_symlink():
        result['unit'] = hashlib.sha256(content(unit)).hexdigest()
    stem, suffix = name.rsplit('.', 1)
    dropin_names = {name + '.d', suffix + '.d'}
    if '@' in stem:
        dropin_names.add(stem.split('@', 1)[0] + '@.' + suffix + '.d')
    # Native systemd also inherits type-wide and dash-prefix drop-ins.
    base = stem.split('@', 1)[0]
    parts = base.split('-')
    for count in range(1, len(parts)):
        dropin_names.add('-'.join(parts[:count]) + '-.' + suffix + '.d')
    for folder in sorted(dropin_names):
        dropins = directory / folder
        if dropins.exists():
            for path in sorted(immutable(dropins).iterdir()):
                if path.name.endswith('.conf'):
                    result['dropin:' + folder + '/' + path.name] = hashlib.sha256(content(path)).hexdigest()
    # Include outgoing and incoming dependency edges. A changed session target
    # can stop PartOf applications without changing their unit bytes.
    for folder in sorted(directory.iterdir()):
        if folder.name.endswith(('.wants', '.requires')) and folder.is_dir():
            for edge in sorted(immutable(folder).iterdir()):
                if folder.name.startswith(name + '.') or edge.name == name:
                    result['edge:' + folder.name + '/' + edge.name] = hashlib.sha256(content(edge)).hexdigest()
    return result


def home_units(config, closure):
    system = immutable(Path(closure) / 'etc/systemd/system')
    name = 'home-manager-' + config['operatorName'] + '.service'
    text = content(system / name).decode('utf-8')
    starts = re.findall(r'^ExecStart=(.*)$', text, re.M)
    # Verified native NixOS HM service has one fixed hm-setup-env executable and
    # one generation argument. No shell, quoting, specifiers or extra arguments.
    pattern = r'(/nix/store/[a-z0-9]{32}-hm-setup-env) (/nix/store/[a-z0-9]{32}-home-manager-generation)'
    if len(starts) != 1 or not re.fullmatch(pattern, starts[0]):
        raise InspectionRequired('unsupported-home-manager-layout')
    wrapper, generation = re.fullmatch(pattern, starts[0]).groups()
    immutable(wrapper)
    immutable(generation)
    return immutable(Path(generation) / 'home-files/.config/systemd/user')


def active_units(config):
    result = {'system': [], 'user': []}
    settings = config['disruptionGuard']
    for scope, names in [('system', settings['systemUnits']), ('user', settings['userUnits'])]:
        argv = [config['systemctl']]
        if scope == 'user':
            argv += ['--user', '--machine=' + config['operatorName'] + '@.host']
        argv += ['show', '--property=Id', '--property=ActiveState', '--', *names]
        try:
            output = subprocess.run(argv, check=True, capture_output=True, timeout=10).stdout.decode('utf-8')
            records = [dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
                       for block in output.strip().split('\n\n')]
            if {record.get('Id') for record in records} != set(names):
                raise ValueError()
            if any(record.get('ActiveState') not in {'active', 'inactive', 'failed', 'activating', 'deactivating', 'reloading', 'maintenance', 'refreshing'} for record in records):
                raise ValueError()
            result[scope] = sorted(record['Id'] for record in records
                                   if record.get('ActiveState') in {'active', 'activating', 'reloading', 'deactivating'})
        except (OSError, ValueError, subprocess.SubprocessError):
            raise InspectionRequired('active-unit-query-unavailable') from None
    return result


def native_no_restart(before, after, name, old, new):
    # Bounded native exception: no drop-ins, identical dependency edges and Unit
    # section, both generations explicitly disable restart, neither requests reload.
    if name != 'display-manager.service' or set(old) != set(new) or 'unit' not in old:
        return False
    if any(key.startswith('dropin:') for key in old) or any(old[key] != new[key] for key in old if key != 'unit'):
        return False
    a, b = content(before / name).decode(), content(after / name).decode()
    def fields(text):
        service = text.split('[Service]\n', 1)
        if len(service) != 2:
            return None
        body = service[1].split('\n[', 1)[0]
        restart = re.findall(r'^X-RestartIfChanged=(.*)$', body, re.M)
        reload = re.findall(r'^X-ReloadIfChanged=(.*)$', body, re.M)
        return service[0], restart, reload
    x, y = fields(a), fields(b)
    return x is not None and y is not None and x[0] == y[0] and x[1] == y[1] == ['false'] and x[2] in ([], ['false']) and y[2] in ([], ['false'])


def inspect(config, runtime, candidate, active):
    settings = config['disruptionGuard']
    findings, artifacts = [], {}
    for scope, key in [('system', 'systemUnits'), ('user', 'userUnits')]:
        try:
            before = immutable(Path(runtime) / 'etc/systemd/system') if scope == 'system' else home_units(config, runtime)
            after = immutable(Path(candidate) / 'etc/systemd/system') if scope == 'system' else home_units(config, candidate)
            for name in settings[key]:
                old, new = unit_artifacts(before, name), unit_artifacts(after, name)
                artifacts[scope + ':' + name] = [old, new]
                if name in active[scope] and old != new and not (scope == 'system' and native_no_restart(before, after, name, old, new)):
                    findings.append(scope + ':' + name + ':changed-or-removed')
        except (InspectionRequired, OSError, UnicodeError) as error:
            findings.append(scope + ':inspection-required')
    proof = {'runtime': runtime, 'candidate': candidate, 'active': active,
             'policy': policy(config), 'artifacts': artifacts, 'findings': findings}
    proof['digest'] = hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
    return proof


def policy(config):
    return hashlib.sha256((json.dumps(config['disruptionGuard'], sort_keys=True) +
        str(config['operatorUid']) + config['operatorName'] + str(config.get('modelReviewEnabled')) + str(config.get('configPath'))).encode() + Path(__file__).read_bytes()).hexdigest()


def probe(config, runtime, candidate):
    try:
        return inspect(config, runtime, candidate, active_units(config))
    except InspectionRequired:
        proof = {'runtime': runtime, 'candidate': candidate, 'policy': policy(config),
                 'findings': ['active-unit-query-unavailable'], 'active': None}
        proof['digest'] = hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
        return proof


def state_directory(config):
    path = Path(config['disruptionState'])
    info = path.lstat()
    if os.geteuid() != 0 or not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError('untrusted disruption state')
    return path


def read_record(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 65536:
            raise ValueError('untrusted disruption record')
        return json.load(stream)


def write_record(path, value, public=False):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644 if public else 0o600)
    if public:
        os.fchmod(fd, 0o644)
    if len(json.dumps(value, sort_keys=True).encode()) > 65536:
        os.close(fd)
        path.unlink()
        raise ValueError('disruption record oversized')
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
