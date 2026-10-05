#!/usr/bin/env python3
"""Six-hour source updates; isolated preparation, protected boot, safe Git import.

Nix/Git own lock construction and integration. No advisory classification or
caller-written deployment verdict. An affected dirty file always defers updates.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import time
import urllib.request
import uuid

POLICY = 'config/updates.json'
CLI = 'modules/development/ai/codex-package.nix'
ALLOWED = {'flake.lock', POLICY, CLI}
NUMERIC = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}\Z')
REV = re.compile(r'[0-9a-f]{40}\Z')
SOURCES = {'nixpkgs': ('NixOS', 'nixpkgs', 'nixos-26.05'),
           'nixpkgs-unstable': ('NixOS', 'nixpkgs', 'nixos-unstable'),
           'codex-desktop-linux': ('ilysenko', 'codex-desktop-linux', 'main'),
           'codex-desktop-sandbox': ('ilysenko', 'codex-desktop-linux', 'main')}


def fetch(url):
    # Only fixed public HTTPS sources; never inherit OAuth/PAT credentials.
    request = urllib.request.Request(url, headers={'User-Agent': 'phoenix-updates',
                                      'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.geturl().startswith(('https://api.github.com/', 'https://raw.githubusercontent.com/')):
            raise ValueError('unexpected update-source redirect')
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('update-source response too large')
    return json.loads(data)


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get('version') != 1:
        raise ValueError('unsupported update policy')
    if set(policy) - {'version', 'packageSources', 'holds', '_comments'}:
        raise ValueError('unknown policy fields')
    expected = {'firefox', 'codex-desktop', 'codex-cli'}
    if set(policy.get('packageSources', {})) != expected:
        raise ValueError('unsupported package selection')
    sources = policy['packageSources']
    if (sources['firefox'] not in {'nixpkgs', 'nixpkgs-unstable'} or
        sources['codex-desktop'] != {'native': 'codex-desktop-linux', 'sandbox': 'codex-desktop-sandbox'} or
        sources['codex-cli'] != 'codex-cli'):
        raise ValueError('unsupported package adapter')
    holds = policy.get('holds')
    if not isinstance(holds, dict) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_+-]*', app) for app in holds):
        raise ValueError('unsupported hold identifier')
    for app, hold in holds.items():
        if (not isinstance(hold, dict) or set(hold) - {'pin', 'reason', 'resumeAtVersion', 'source'} or
            not {'pin', 'reason'} <= hold.keys() or not isinstance(hold['reason'], str) or not hold['reason'].strip()):
            raise ValueError('hold requires exact pin and reason')
        threshold = hold.get('resumeAtVersion')
        if threshold is not None and (not isinstance(threshold, str) or not NUMERIC.fullmatch(threshold)):
            raise ValueError('resume version must be a stable numeric version or null')
        pin = hold['pin']
        if app not in {'codex-desktop', 'codex-cli'} and (not isinstance(pin, str) or not REV.fullmatch(pin)):
            raise ValueError('package hold requires a full Nixpkgs revision')
        if hold.get('source', 'nixpkgs') not in {'nixpkgs', 'nixpkgs-unstable'}:
            raise ValueError('unsupported held package source')
        if app == 'codex-desktop' and (not isinstance(pin, dict) or set(pin) != {'native', 'sandbox'} or
            any(not isinstance(v, str) or not REV.fullmatch(v) for v in pin.values())):
            raise ValueError('desktop hold requires both exact source revisions')
        if app == 'codex-cli' and (not isinstance(pin, dict) or set(pin) != {'version', 'hash'} or
            not isinstance(pin['version'], str) or not NUMERIC.fullmatch(pin['version']) or
            not re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=', str(pin['hash']))):
            raise ValueError('CLI hold requires stable version and SRI SHA-256')
    return policy


def compare_version(config, c, version, threshold):
    if not NUMERIC.fullmatch(version) or not NUMERIC.fullmatch(threshold):
        return False
    expression = 'builtins.compareVersions %s %s' % (json.dumps(version), json.dumps(threshold))
    return int(c._run([config['nix'], 'eval', '--json', '--expr', expression], env=nix_env(config))) >= 0


def nix_env(config):
    return dict(HOME=config['nixHome'], PATH=config['path'],
                NIX_CONFIG='accept-flake-config = false\n',
                SSL_CERT_FILE=config.get('caBundle', '/etc/ssl/certs/ca-certificates.crt'),
                GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')


def revision(alias, branch=None):
    owner, repo, ref = SOURCES[alias]
    if branch is not None:
        ref = branch
    result = fetch('https://api.github.com/repos/%s/%s/commits/%s' % (owner, repo, ref))
    value = result.get('sha')
    if not isinstance(value, str) or not REV.fullmatch(value):
        raise ValueError('published channel revision unavailable')
    return value


def community(c, rev):
    owner, repo, _ = SOURCES['codex-desktop-linux']
    checks = []
    for page in range(1, 11):
        result = fetch('https://api.github.com/repos/%s/%s/commits/%s/check-runs?per_page=100&page=%d' % (owner, repo, rev, page))
        records = result.get('check_runs')
        if not isinstance(records, list):
            raise ValueError('Community checks unavailable')
        checks.extend(records)
        if len(checks) >= result.get('total_count', 100000):
            break
    else:
        raise ValueError('Community checks exceed pagination bound')
    c.validate_community_checks(rev, {'check_runs': checks})
    return c.validate_community_payload(fetch('https://raw.githubusercontent.com/%s/%s/%s/nix/upstream-linux-packages.json' % (owner, repo, rev)))['version']


def lock_node(lock, alias):
    return lock['nodes'][lock['nodes'][lock['root']]['inputs'][alias]]


def validate_lock(c, before, after, selected):
    if before['root'] != after['root'] or before['version'] != after['version']:
        raise ValueError('lock schema changed')
    if before['nodes'][before['root']]['inputs'] != after['nodes'][after['root']]['inputs']:
        raise ValueError('root lock declarations changed')
    allowed = c._closure(before, selected) | c._closure(after, selected)
    changed = {n for n in before['nodes'].keys() | after['nodes'].keys() if before['nodes'].get(n) != after['nodes'].get(n)}
    if changed - allowed:
        raise ValueError('unselected dependency changed')
    for alias, rev in selected.items():
        owner, repo, _ = SOURCES[alias]
        node = lock_node(after, alias)
        if node['locked'].get('rev') != rev or node['locked'].get('owner') != owner or node['locked'].get('repo') != repo:
            raise ValueError('selected dependency identity changed')
        if node['original'] != lock_node(before, alias)['original']:
            raise ValueError('declared input identity changed')


def integrate(config, c, home, head, commit, paths):
    """Let Git's two-tree merge preserve unrelated staged/unstaged changes.

    Hold the normal index lock, construct its replacement separately, and use
    update-ref's compare-and-swap. No stash, reset, hooks or user-change commits.
    """
    repo = config['repo']
    if c.git(config['git'], repo, home, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('main advanced; candidate retained')
    if c._status_paths(config['git'], repo, home) & paths:
        raise ValueError('affected user edits; candidate retained')
    index = Path(c.git(config['git'], repo, home, 'rev-parse', '--path-format=absolute', '--git-path', 'index').decode().strip())
    lock = Path(str(index) + '.lock')
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    alternate = Path(str(index) + '.phoenix-' + uuid.uuid4().hex)
    try:
        alternate.write_bytes(index.read_bytes())
        env = dict(HOME=str(home), PATH=config['path'], GIT_CONFIG_NOSYSTEM='1',
                   GIT_CONFIG_GLOBAL='/dev/null', GIT_INDEX_FILE=str(alternate), GIT_NO_REPLACE_OBJECTS='1')
        command = [config['git'], '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', repo]
        # Git rejects changes to affected files and keeps unrelated index entries.
        c._run([*command, 'read-tree', '-m', '-u', head, commit], env=env)
        try:
            c._run([*command, 'update-ref', '-m', 'Phoenix automatic package update', 'HEAD', commit, head], env=env)
        except Exception:
            c._run([*command, 'read-tree', '-m', '-u', commit, head], env=env)
            raise
        with os.fdopen(fd, 'wb') as output:
            fd = None
            output.write(alternate.read_bytes())
            output.flush()
            os.fsync(output.fileno())
        os.replace(lock, index)
    finally:
        if fd is not None:
            os.close(fd)
        lock.unlink(missing_ok=True)
        alternate.unlink(missing_ok=True)


def controller(config, c, home, tree, commit, base, profile):
    files, modes = c._manifest(config['git'], tree, home, commit)
    request = dict(files=files, modes=modes, commit=commit, target=config['target'], action='boot',
                   expectedBase=base, expectedProfile=profile,
                   reason='Automatically update supported stable system and selected fresh applications; respect explicit holds and preserve runtime state')
    body = json.dumps(request).encode() + b'\n'
    if len(body) > c.WIRE_LIMIT:
        raise ValueError('source exceeds deployment wire bound')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(7200)
        connection.connect(config['controllerSocket'])
        connection.sendall(body)
        response = bytearray()
        while not response.endswith(b'\n'):
            block = connection.recv(65536)
            if not block or len(response) + len(block) > 65536:
                raise ValueError('controller response lost or oversized')
            response.extend(block)
    result = json.loads(response)
    if result.get('ok') is not True or result.get('action') != 'boot':
        raise ValueError('protected boot review/staging failed: ' + str(result.get('code', 'protocol')))
    return result


def run(config, c):
    repo = Path(config['repo']).resolve(strict=True)
    state = Path(config['state'])
    home = state / 'command-home'
    home.mkdir(exist_ok=True)
    Path(config['nixHome']).mkdir(exist_ok=True)
    head = c.git(config['git'], repo, home, 'rev-parse', 'HEAD').decode().strip()
    # Never turn unreviewed user commits into unattended system deployments.
    base = str(Path(config['baseline']).resolve(strict=True))
    profile = str(Path(config['systemProfile']).resolve(strict=True))
    approved = [base, str((Path(profile) / 'etc/phoenix-agent/activated-source').resolve(strict=True))]
    pending_path = state / 'pending.json'
    if pending_path.exists():
        pending = json.loads(pending_path.read_text())
        if pending['source'] == approved[1]:
            if head != pending['head']:
                return dict(status='deferred', reason='main advanced during staged update; deploy current committed work first')
            try:
                integrate(config, c, home, head, pending['candidate'], set(pending['paths']))
            except Exception:
                return dict(status='deferred', reason='staged update awaits affected local edits', candidate=pending['candidate'])
            pending_path.unlink()
            return dict(status='staged', candidate=pending['candidate'], source=pending['source'])
        pending_path.unlink()  # A newer manual deployment superseded this candidate.
    inventory = c._commit_inventory(config['git'], repo, home, head)
    if not any(inventory == c._inventory(Path(source)) for source in approved):
        return {'status': 'deferred', 'reason': 'main is not the active or staged reviewed source'}
    if c._status_paths(config['git'], repo, home) & ALLOWED:
        return {'status': 'deferred', 'reason': 'updater-owned file has local changes'}
    policy = validate_policy(json.loads(c.git(config['git'], repo, home, 'show', head + ':' + POLICY)))
    before = c._read_lock(repo / 'flake.lock')
    for alias, (owner, source_repo, _branch) in SOURCES.items():
        original = lock_node(before, alias)['original']
        if original.get('type') != 'github' or original.get('owner') != owner or original.get('repo') != source_repo:
            raise ValueError('update source differs from the supported publisher adapter')
    stable_branch = lock_node(before, 'nixpkgs')['original'].get('ref')
    if not isinstance(stable_branch, str) or not re.fullmatch(r'nixos-[0-9]{2}\.[0-9]{2}', stable_branch):
        raise ValueError('stable source must explicitly follow a reviewed NixOS release branch')
    if lock_node(before, 'nixpkgs-unstable')['original'].get('ref') != 'nixos-unstable':
        raise ValueError('fresh source must explicitly follow the tested unstable channel')
    selected = {alias: revision(alias, stable_branch if alias == 'nixpkgs' else None)
                for alias in SOURCES if alias != 'codex-desktop-sandbox'}
    versions = {}
    notes = []
    desktop_revision = selected['codex-desktop-linux']
    selected['codex-desktop-sandbox'] = desktop_revision
    try:
        versions['codex-desktop'] = community(c, desktop_revision)
    except Exception:
        # A publisher's pending checks do not prevent independent Nixpkgs fixes.
        selected.pop('codex-desktop-linux')
        selected.pop('codex-desktop-sandbox')
        notes.append('Community source held: required upstream checks unavailable or unsuccessful')
    release = c.stable_cli_release([fetch('https://api.github.com/repos/openai/codex/releases/latest')])
    if release is not None:
        versions['codex-cli'] = c.CLI_TAG.fullmatch(release['tag_name']).group(1)
        if not compare_version(config, c, versions['codex-cli'], '0.159.0'):
            versions.pop('codex-cli')
    holds = policy['holds']
    releasing = []
    for app, hold in holds.items():
        if app in {'codex-cli', 'codex-desktop'} or hold.get('resumeAtVersion') is None:
            continue
        alias = policy['packageSources']['firefox'] if app == 'firefox' else hold.get('source', 'nixpkgs')
        ref = 'github:NixOS/nixpkgs/' + selected[alias] + '#legacyPackages.x86_64-linux.' + app + '.version'
        versions[app] = c._run([config['nix'], 'eval', '--raw', '--no-write-lock-file', ref], env=nix_env(config), timeout=900).decode().strip()
    for app, hold in holds.items():
        version = versions.get(app)
        if version and hold.get('resumeAtVersion') and compare_version(config, c, version, hold['resumeAtVersion']):
            releasing.append(app)
        elif app == 'codex-desktop':
            selected.pop('codex-desktop-linux', None)
            selected.pop('codex-desktop-sandbox', None)
        elif app == 'codex-cli':
            versions.pop('codex-cli', None)
        # Firefox is pinned per package by the Nix declaration, independently of
        # the shared channel's compositor and other application dependencies.
    if 'codex-desktop' in versions:
        # Never silently downgrade the independently accepted Native or Sandbox
        # payload just because an upstream source branch moved or was restored.
        for alias in ('codex-desktop-linux', 'codex-desktop-sandbox'):
            old_rev = lock_node(before, alias)['locked']['rev']
            old_payload = c.validate_community_payload(fetch(
                'https://raw.githubusercontent.com/ilysenko/codex-desktop-linux/' + old_rev + '/nix/upstream-linux-packages.json'))
            if not compare_version(config, c, versions['codex-desktop'], old_payload['version']):
                selected.pop('codex-desktop-linux', None)
                selected.pop('codex-desktop-sandbox', None)
                if 'codex-desktop' in releasing:
                    releasing.remove('codex-desktop')
                break
    selected = {alias: rev for alias, rev in selected.items() if lock_node(before, alias)['locked']['rev'] != rev}
    current_cli = re.search(r'version = "([0-9.]+)";', c.git(config['git'], repo, home, 'show', head + ':' + CLI).decode())
    cli_version = versions.get('codex-cli')
    if cli_version and current_cli and not compare_version(config, c, cli_version, current_cli.group(1)):
        cli_version = None
    if current_cli and cli_version == current_cli.group(1):
        cli_version = None
    fingerprint = hashlib.sha256(json.dumps(dict(head=head, selected=selected, cli=cli_version, releasing=releasing, base=base, profile=profile), sort_keys=True).encode()).hexdigest()
    if not selected and not cli_version and not releasing:
        return dict(status='unchanged', notes=notes)
    attempt = state / 'attempt.json'
    if attempt.exists():
        previous = json.loads(attempt.read_text())
        if previous.get('fingerprint') == fingerprint and time.time() - previous.get('time', 0) < 86400:
            return {'status': 'deferred', 'reason': 'unchanged failed candidate; retry tomorrow', 'notes': notes}
    attempt.write_text(json.dumps(dict(fingerprint=fingerprint, time=time.time())))
    branch = 'codex/updates/' + uuid.uuid4().hex
    tree = state / 'worktrees' / branch.rsplit('/', 1)[-1]
    tree.parent.mkdir(exist_ok=True)
    c.git(config['git'], repo, home, 'worktree', 'add', '-b', branch, str(tree), head)
    commit = None
    try:
        for alias, rev in selected.items():
            owner, source_repo, _ = SOURCES[alias]
            c._run([config['nix'], 'flake', 'lock', '--override-input', alias,
                    'github:%s/%s/%s' % (owner, source_repo, rev), '--output-lock-file', 'flake.lock'],
                   cwd=tree, env=nix_env(config), timeout=1800)
        validate_lock(c, before, c._read_lock(tree / 'flake.lock'), selected)
        if cli_version:
            c._run([config['nixUpdate'], '--flake', '--version', cli_version, 'codex-cli'],
                   cwd=tree, env=nix_env(config), timeout=1800)
            actual = c._run([config['nix'], 'eval', '--raw', '--no-write-lock-file',
                            '.#packages.x86_64-linux.codex-cli.version'],
                           cwd=tree, env=nix_env(config), timeout=900).decode().strip()
            if actual != cli_version:
                raise ValueError('CLI updater did not persist the verified stable version')
        for app in releasing:
            del policy['holds'][app]
        if releasing:
            (tree / POLICY).write_text(json.dumps(policy, indent=2) + '\n')
        paths = c._working_paths(config['git'], tree, home, head)
        if not paths or not paths <= ALLOWED:
            raise ValueError('update changed unexpected files')
        c.git(config['git'], tree, home, 'add', '--', *sorted(paths))
        c.git(config['git'], tree, home, '-c', 'user.name=Phoenix Update Service', '-c', 'user.email=phoenix-updates@localhost',
              'commit', '-m', 'feat(updates): refresh supported package sources', '-m',
              'Advance published channels and verified stable application releases without a local cooldown.\n'
              'Respect exact holds; remove only satisfied resume thresholds.\n'
              'Deployment must pass the protected build/source review before boot staging; keep the running system unchanged.')
        commit = c.git(config['git'], tree, home, 'rev-parse', 'HEAD').decode().strip()
        # Recheck policy/HEAD immediately before asking the protected controller.
        if c.git(config['git'], repo, home, 'rev-parse', 'HEAD').decode().strip() != head or c._status_paths(config['git'], repo, home) & paths:
            return dict(status='deferred', reason='checkout changed', candidate=commit, branch=branch)
        result = controller(config, c, home, tree, commit, base, profile)
        try:
            integrate(config, c, home, head, commit, paths)
        except Exception:
            # Explicitly report the narrow late race: boot staging succeeded,
            # main checkout was preserved; never pretend normal switch has pins.
            pending = dict(status='staged-pending-integration', candidate=commit, branch=branch,
                           source=result['source'], head=head, paths=sorted(paths),
                           reason='checkout changed during protected review')
            (state / 'pending.json').write_text(json.dumps(pending))
            return pending
        attempt.unlink(missing_ok=True)
        return dict(status='staged', candidate=commit, source=result['source'], notes=notes)
    finally:
        c.git(config['git'], repo, home, 'worktree', 'remove', '--force', str(tree))
        if commit is None:
            c.git(config['git'], repo, home, 'branch', '-D', branch)


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    spec = importlib.util.spec_from_file_location('candidate', config['candidateScript'])
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    state = Path(config['state'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'runner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = run(config, c)
        except Exception as error:
            result = dict(status='failed', reason=str(error)[:300])
        destination = state / 'last-result.json'
        fd, name = tempfile.mkstemp(dir=state, prefix='.result-')
        with os.fdopen(fd, 'w') as output:
            json.dump(result, output)
            output.write('\n')
        os.replace(name, destination)
        print(json.dumps(result))
        return 1 if result['status'] in {'failed', 'staged-pending-integration'} else 0


if __name__ == '__main__':
    sys.exit(main())
