#!/usr/bin/env python3
"""Scheduled source updates; isolated preparation, protected boot, safe Git import.

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
ALLOWED = {'flake.lock', POLICY}
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
    if set(policy) - {'version', 'packageSources', 'holds', 'patches', '_comments'}:
        raise ValueError('unknown policy fields')
    expected = {'firefox', 'codex-desktop', 'codex-cli'}
    if set(policy.get('packageSources', {})) != expected:
        raise ValueError('unsupported package selection')
    sources = policy['packageSources']
    if (sources['firefox'] not in {'nixpkgs', 'nixpkgs-unstable'} or
        sources['codex-desktop'] != {'native': 'codex-desktop-linux', 'sandbox': 'codex-desktop-sandbox'} or
        sources['codex-cli'] not in {'nixpkgs', 'nixpkgs-unstable'}):
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
        if app != 'codex-desktop' and (not isinstance(pin, str) or not REV.fullmatch(pin)):
            raise ValueError('package hold requires a full Nixpkgs revision')
        if hold.get('source', 'nixpkgs') not in {'nixpkgs', 'nixpkgs-unstable'} or (app not in {'firefox', 'codex-cli', 'codex-desktop'} and hold.get('source', 'nixpkgs') != 'nixpkgs'):
            raise ValueError('ordinary holds must observe their stable package source')
        if app == 'codex-desktop' and (not isinstance(pin, dict) or set(pin) != {'native', 'sandbox'} or
            any(not isinstance(v, str) or not REV.fullmatch(v) for v in pin.values())):
            raise ValueError('desktop hold requires both exact source revisions')
    patches = policy.get('patches', {})
    if not isinstance(patches, dict):
        raise ValueError('patches must be a package-keyed object')
    for app, fix in patches.items():
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_+-]*', app) or app == 'codex-desktop' or
            not isinstance(fix, dict) or set(fix) - {'reason', 'patchFiles', 'removeAtVersion', 'source'} or
            not isinstance(fix.get('reason'), str) or not fix['reason'].strip() or
            not isinstance(fix.get('patchFiles'), list) or not fix['patchFiles'] or
            any(not isinstance(path, str) or not re.fullmatch(r'config/update-patches/[A-Za-z0-9_+-]+\.patch', path)
                for path in fix['patchFiles'])):
            raise ValueError('temporary patch requires reason and central patch files')
        threshold = fix.get('removeAtVersion')
        if threshold is not None and (not isinstance(threshold, str) or not NUMERIC.fullmatch(threshold)):
            raise ValueError('patch removal version must be stable numeric or null')
        if fix.get('source', 'nixpkgs') not in {'nixpkgs', 'nixpkgs-unstable'} or (app not in {'firefox', 'codex-cli'} and fix.get('source', 'nixpkgs') != 'nixpkgs'):
            raise ValueError('ordinary patches must observe their stable package source')
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
    if c.git(config['git'], repo, home, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip() != config.get('sourceBranch', 'main'):
        raise ValueError('configured update branch is not checked out')
    if c.git(config['git'], repo, home, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('main advanced; candidate retained')
    if c._status_paths(config['git'], repo, home) & paths:
        raise ValueError('affected user edits; candidate retained')
    index = Path(c.git(config['git'], repo, home, 'rev-parse', '--path-format=absolute', '--git-path', 'index').decode().strip())
    lock = Path(str(index) + '.lock')
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    alternate = Path(str(index) + '.phoenix-' + uuid.uuid4().hex)
    try:
        if c.git(config['git'], repo, home, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip() != config.get('sourceBranch', 'main'):
            raise ValueError('configured update branch changed before index lock')
        alternate.write_bytes(index.read_bytes())
        env = dict(c.git_env(repo, home), PATH=config['path'], GIT_INDEX_FILE=str(alternate))
        command = c.git_command(config['git'], repo, home)
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


def cleanup_branches(config, c, home, keep=()):
    """Remove only recognizable service-authored candidates with no worktree."""
    if not config.get('cleanupBranches', True):
        return
    repo = config['repo']
    checked_out = {line[7:] for line in c.git(config['git'], repo, home, 'worktree', 'list', '--porcelain').decode().splitlines()
                   if line.startswith('branch ')}
    branches = c.git(config['git'], repo, home, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/codex/updates/').decode().splitlines()
    legacy = 'modules/development/ai/codex-package.nix'
    for branch in branches:
        suffix = branch.removeprefix('codex/updates/')
        if branch in keep or 'refs/heads/' + branch in checked_out or not re.fullmatch(r'(?:[0-9a-f]{32}|[0-9]{8}-[0-9]{6}(?:-[0-9]+)?)', suffix):
            continue
        author = c.git(config['git'], repo, home, 'show', '-s', '--format=%ae', branch).decode().strip()
        paths = set(c.git(config['git'], repo, home, 'diff-tree', '--no-commit-id', '--name-only', '-r', branch).decode().splitlines())
        if author == 'phoenix-updates@localhost' and paths and paths <= ALLOWED | {legacy}:
            c.git(config['git'], repo, home, 'branch', '-D', branch)


class UpdateDenied(ValueError):
    def __init__(self, result):
        super().__init__('deterministic boot staging failed: ' + str(result.get('summary', result.get('code', 'protocol')))[:1000])
        self.nodes = result.get('affectedInputNodes', [])


def controller(config, c, home, tree, commit, base, profile):
    files, modes = c._manifest(config['git'], tree, home, commit)
    request = dict(files=files, modes=modes, commit=commit, target=config['target'], action='update',
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
    if result.get('ok') is not True or result.get('action') != 'update':
        raise UpdateDenied(result)
    return result


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.state-')
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def run(config, c):
    repo = Path(config['repo']).resolve(strict=True)
    state = Path(config['state'])
    home = state / 'command-home'
    home.mkdir(exist_ok=True)
    Path(config['nixHome']).mkdir(exist_ok=True)
    source_branch = config.get('sourceBranch', 'main')
    if c.git(config['git'], repo, home, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip() != source_branch:
        return dict(status='deferred', reason='configured update branch is not checked out')
    head = c.git(config['git'], repo, home, 'rev-parse', 'refs/heads/' + source_branch).decode().strip()
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
            if config.get('cleanupBranches', True):
                cleanup_branches(config, c, home)
            return dict(status='staged', candidate=pending['candidate'], source=pending['source'])
        pending_path.unlink()  # A newer manual deployment superseded this candidate.
        cleanup_branches(config, c, home)
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
    selected['codex-desktop-sandbox'] = selected['codex-desktop-linux']
    versions = {}
    notes = []
    desktop_revision = selected.get('codex-desktop-linux')
    try:
        if desktop_revision is None:
            raise ValueError('Community revision retained after protected rejection')
        versions['codex-desktop'] = community(c, desktop_revision)
    except Exception:
        # A publisher's pending checks do not prevent independent Nixpkgs fixes.
        selected.pop('codex-desktop-linux', None)
        selected.pop('codex-desktop-sandbox', None)
        notes.append('Community source held: required upstream checks unavailable or unsuccessful')
    holds = policy['holds']
    releasing = []
    for app, hold in [*holds.items(), *policy.get('patches', {}).items()]:
        if app == 'codex-desktop' or hold.get('resumeAtVersion', hold.get('removeAtVersion')) is None:
            continue
        alias = policy['packageSources'][app] if app in {'firefox', 'codex-cli'} else hold.get('source', 'nixpkgs')
        ref = 'github:NixOS/nixpkgs/' + selected.get(alias, lock_node(before, alias)['locked']['rev']) + '#legacyPackages.x86_64-linux.' + ('codex' if app == 'codex-cli' else app) + '.version'
        versions[app] = c._run([config['nix'], 'eval', '--raw', '--no-write-lock-file', ref], env=nix_env(config), timeout=900).decode().strip()
    for app, hold in holds.items():
        version = versions.get(app)
        if version and hold.get('resumeAtVersion') and compare_version(config, c, version, hold['resumeAtVersion']):
            releasing.append(app)
        elif app == 'codex-desktop':
            selected.pop('codex-desktop-linux', None)
            selected.pop('codex-desktop-sandbox', None)
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
    removing_patches = [app for app, fix in policy.get('patches', {}).items()
                        if (app not in holds or app in releasing) and versions.get(app) and fix.get('removeAtVersion') and
                        compare_version(config, c, versions[app], fix['removeAtVersion'])]
    fingerprint = hashlib.sha256(json.dumps(dict(head=head, selected=selected, releasing=releasing,
        removingPatches=removing_patches, base=base, profile=profile), sort_keys=True).encode()).hexdigest()
    if not selected and not releasing and not removing_patches:
        cleanup_branches(config, c, home)
        return dict(status='unchanged', notes=notes)
    attempt = state / 'attempt.json'
    if attempt.exists():
        previous = json.loads(attempt.read_text())
        if previous.get('fingerprint') == fingerprint and time.time() - previous.get('time', 0) < 86400:
            return {'status': 'deferred', 'reason': 'unchanged failed candidate; retry tomorrow', 'notes': notes}
    attempt.write_text(json.dumps(dict(fingerprint=fingerprint, time=time.time())))
    stamp = time.strftime('%Y%m%d-%H%M%S')
    branch = 'codex/updates/' + stamp
    existing = set(c.git(config['git'], repo, home, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/codex/updates/').decode().splitlines())
    suffix = 0
    while branch in existing:
        suffix += 1
        branch = 'codex/updates/' + stamp + '-' + str(suffix)
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
        for app in releasing:
            del policy['holds'][app]
        for app in removing_patches:
            del policy['patches'][app]
        if releasing or removing_patches:
            (tree / POLICY).write_text(json.dumps(policy, indent=2) + '\n')
        paths = c._working_paths(config['git'], tree, home, head)
        if not paths or not paths <= ALLOWED:
            raise ValueError('update changed unexpected files')
        c.git(config['git'], tree, home, 'add', '--', *sorted(paths))
        c.git(config['git'], tree, home, '-c', 'user.name=Phoenix Update Service', '-c', 'user.email=phoenix-updates@localhost',
              'commit', '-m', 'feat(updates): refresh supported package sources', '-m',
              'Advance published channels and verified stable application releases without a local cooldown.\n'
              'Respect exact holds; remove only satisfied resume thresholds.\n'
              'Deployment must pass deterministic source and build checks before boot staging; keep the running system unchanged.')
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
                           reason='checkout changed during deterministic build/staging')
            (state / 'pending.json').write_text(json.dumps(pending))
            return pending
        attempt.unlink(missing_ok=True)
        return dict(status='staged', candidate=commit, source=result['source'], notes=notes)
    finally:
        c.git(config['git'], repo, home, 'worktree', 'remove', '--force', str(tree))
        if commit is None:
            c.git(config['git'], repo, home, 'branch', '-D', branch)
        elif config.get('cleanupBranches', True):
            cleanup_branches(config, c, home, keep=(branch,) if pending_path.exists() else ())


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
            result = dict(status='failed', reason=str(error)[:1000])
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
