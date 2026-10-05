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

LIMIT = 256 * 1024


def relevant(owner, repo, name):
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
            raise ValueError('changed module source contains a symlink')
        if path.is_file():
            result[name] = (str(bool(path.stat().st_mode & 0o111)) + ':' + hashlib.sha256(path.read_bytes()).hexdigest(), path)
    return result


def evidence(before_files, after_files, resolve):
    before = json.loads(before_files['flake.lock'])['nodes']
    after = json.loads(after_files['flake.lock'])['nodes']
    output, size = [], 0
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
        output.append(header)
        size += len(header.encode())
        for name in sorted(previous.keys() | current.keys()):
            if previous.get(name, (None,))[0] == current.get(name, (None,))[0]:
                continue
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
            size += len(change.encode())
            if size > LIMIT:
                raise ValueError('upstream source evidence exceeds review bound')
            output.append(change)
    return ''.join(output)
