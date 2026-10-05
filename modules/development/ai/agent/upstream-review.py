"""Bounded exact locked-source evidence for the protected deployment reviewer.

Nix resolves immutable sources as the unprivileged builder. Capture changed
module/build/containment authority, not a hash-only claim or caller evidence.
Ordinary Nixpkgs package maintenance retains distribution trust; this is not a
malware scanner. Missing, binary, excessive or unsupported evidence fails closed.
"""
import difflib
import hashlib
import json
from pathlib import Path
import re

LIMIT = 768 * 1024
MAX_BATCHES = 24

class Evidence(str):
    """Root-generated lineage; never derive input names by parsing source text."""
    def __new__(cls, text, nodes):
        result = super().__new__(cls, text)
        result.nodes = sorted(nodes)
        return result


def relevant(owner, repo, name):
    if (owner, repo) == ('openai', 'codex') and name == 'MODULE.bazel.lock':
        # Bazel repository-cache metadata is not used by the prebuilt CLI's
        # runtime or reviewer isolation. Release-build provenance remains
        # publisher trust; this scope does not reproduce the release binary.
        return False
    if (owner, repo) == ('NixOS', 'nixpkgs'):
        return (name in {'flake.nix', 'default.nix', 'nixos/default.nix'} or
                name.startswith(('nixos/modules/', 'nixos/lib/', 'lib/', 'pkgs/stdenv/', 'pkgs/build-support/',
                                 'pkgs/by-name/bu/bubblewrap/', 'pkgs/by-name/op/openshell/')))
    # External inputs can import arbitrary local support files. Read the entire
    # changed source text; never guess that an extension cannot supply authority.
    return True


def inventory(root, owner, repo):
    result = {}
    for path in Path(root).rglob('*'):
        name = str(path.relative_to(root))
        if not relevant(owner, repo, name):
            continue
        if path.is_symlink():
            # Unchanged vendor license links are not executable evidence. Never
            # follow them; changed links fail closed before reading content.
            result[name] = ('link:' + hashlib.sha256(str(path.readlink()).encode()).hexdigest(), path)
            continue
        if path.is_file():
            with path.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            result[name] = (str(bool(path.stat().st_mode & 0o111)) + ':' + digest, path)
    return result


def evidence(before_files, after_files, resolve):
    before = json.loads(before_files['flake.lock'])['nodes']
    after = json.loads(after_files['flake.lock'])['nodes']
    batches, output, size, nodes = [], [], 0, set()
    for node in sorted(before.keys() | after.keys()):
        old, new = before.get(node, {}).get('locked'), after.get(node, {}).get('locked')
        if old == new:
            continue
        for locked in (old, new):
            if (not isinstance(locked, dict) or locked.get('type') != 'github' or
                not re.fullmatch(r'[A-Za-z0-9_.-]+', str(locked.get('owner'))) or
                not re.fullmatch(r'[A-Za-z0-9_.-]+', str(locked.get('repo'))) or
                not re.fullmatch(r'[0-9a-f]{40}', str(locked.get('rev'))) or not locked.get('narHash')):
                raise ValueError('changed dependency lacks supported exact source evidence')
        if (old['owner'], old['repo']) != (new['owner'], new['repo']):
            raise ValueError('changed dependency source identity requires deliberate review')
        owner, repo = new['owner'], new['repo']
        previous = inventory(resolve(old), owner, repo)
        current = inventory(resolve(new), owner, repo)
        header = '\nExact upstream authority diff: %s %s/%s %s -> %s\n' % (node, owner, repo, old['rev'], new['rev'])
        for name in sorted(previous.keys() | current.keys()):
            if previous.get(name, (None,))[0] == current.get(name, (None,))[0]:
                continue
            if any(record[name][1].is_symlink() for record in (previous, current) if name in record):
                raise ValueError('changed module source contains a symlink')
            if any(record[name][1].stat().st_size > LIMIT for record in (previous, current) if name in record):
                raise ValueError('one upstream implementation exceeds review bound')
            old_bytes = previous[name][1].read_bytes() if name in previous else b''
            new_bytes = current[name][1].read_bytes() if name in current else b''
            try:
                old_text, new_text = old_bytes.decode(), new_bytes.decode()
            except UnicodeError:
                raise ValueError('changed dependency authority contains binary evidence') from None
            change = ''.join(difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True),
                              fromfile=node + '/old/' + name, tofile=node + '/new/' + name))
            change = 'Source executable mode: %s -> %s\n' % (
                previous.get(name, ('absent',))[0].split(':')[0],
                current.get(name, ('absent',))[0].split(':')[0]) + change
            # Full new implementations supplement a contextual diff, preventing
            # hidden surrounding authority from being omitted to fit a bound.
            change += '\nExact candidate implementation: ' + node + '/' + name + '\n' + new_text + '\n'
            change = header + change
            length = len(change.encode())
            if length > LIMIT:
                raise ValueError('one upstream implementation exceeds review bound')
            if size + length > LIMIT:
                batches.append(Evidence(''.join(output), nodes))
                if len(batches) >= MAX_BATCHES:
                    raise ValueError('upstream evidence exceeds batch bound')
                output, size, nodes = [], 0, set()
            size += length
            output.append(change)
            nodes.add(node)
    if output:
        batches.append(Evidence(''.join(output), nodes))
    return batches


def cli_version(files):
    # This is the protected reviewer, not the independently updated user CLI.
    recipe = files.get('modules/development/ai/agent/reviewer-codex.nix',
                       files.get('modules/development/ai/codex.nix', ''))
    match = re.search(r'version = "([0-9]+\.[0-9]+\.[0-9]+)";', recipe)
    if match is None:
        raise ValueError('reviewer CLI adapter no longer has a conventional stable version')
    return match.group(1)


def cli_evidence(before, after, resolve):
    """CLI also executes protected reviews: inspect all changed publisher authority.

    Publisher tag sources supplement release-artifact trust; this is not binary
    reproducibility/provenance proof. Unknown paths/renderer semantics fail closed.
    """
    adapters = {"modules/development/ai/agent/reviewer-codex.nix", "modules/development/ai/codex.nix"}
    if not adapters.intersection(before.keys() | after.keys()):
        return []
    old_version, new_version = cli_version(before), cli_version(after)
    if old_version == new_version:
        return []
    old_root, new_root = Path(resolve(old_version)), Path(resolve(new_version))
    paths = ['codex-rs/exec/src/lib.rs',
             'codex-rs/exec/src/event_processor_with_human_output.rs',
             'codex-rs/core/src/compact.rs', 'codex-rs/protocol/src/protocol.rs']
    renderer = (new_root / paths[1]).read_text()
    if 'context compacted' not in renderer:
        raise ValueError('CLI compaction guard interface requires a reviewed adapter update')
    # Review every changed publisher source file, including configuration,
    # rule loading, execution, sandbox options and vendored containment. The
    # marker is only a preflight; it does not establish the isolation contract.
    previous = inventory(old_root, 'openai', 'codex')
    current = inventory(new_root, 'openai', 'codex')
    batches, output, size, nodes = [], [], 0, set()
    for name in sorted(previous.keys() | current.keys()):
        if previous.get(name, (None,))[0] == current.get(name, (None,))[0]:
            continue
        for record in (previous, current):
            if name in record and (record[name][1].is_symlink() or record[name][1].stat().st_size > LIMIT):
                raise ValueError('CLI authority file exceeds review bound or changes a symlink')
        old_text = previous[name][1].read_text() if name in previous else ''
        new_text = current[name][1].read_text() if name in current else ''
        text = ('Official CLI authority: rust-v%s -> rust-v%s\nExact source trees: %s -> %s\n' %
                (old_version, new_version, old_root, new_root))
        text += 'Source executable mode: %s -> %s\n' % (
            previous.get(name, ('absent',))[0].split(':')[0], current.get(name, ('absent',))[0].split(':')[0])
        text += ''.join(difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True),
                                            fromfile='old/' + name, tofile='new/' + name))
        text += '\nExact candidate implementation: ' + name + '\n' + new_text
        length = len(text.encode())
        if length > LIMIT:
            raise ValueError('CLI authority evidence exceeds review bound')
        if size + length > LIMIT:
            batches.append(Evidence(''.join(output), nodes))
            if len(batches) >= MAX_BATCHES:
                raise ValueError('CLI authority evidence exceeds batch bound')
            output, size, nodes = [], 0, set()
        output.append(text); size += length; nodes.add('reviewer-cli')
    if output:
        batches.append(Evidence(''.join(output), nodes))
    return batches
