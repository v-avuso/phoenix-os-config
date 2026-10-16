"""Isolated guest socket fixture: production dispatch, explicit realization/model doubles."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main(descriptor, mode, case=None):
    public = json.loads(Path(descriptor).read_text())
    deploy = load('peer_controller', public['controller'])
    review = load('peer_review', public['review'])
    files = review.baseline_files(Path(public['source']))
    if mode == 'client':
        request = (dict(authorization=deploy.authorization.named('deployment.test', {'target': 'metal'}, 'peer-fixture', 'metadata'))
                   if case == 'metadata' else dict(files=files, modes={name: '100644' for name in files},
                    commit='a' * 40, action='test', target='metal', reason=case, task='peer-fixture'))
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(5); connection.connect('/run/peer-fixture/control.sock')
            try:
                connection.sendall(json.dumps(request).encode() + b'\n')
                data = b''
                while not data.endswith(b'\n'):
                    block = connection.recv(65536)
                    if not block: break
                    data += block
                result = json.loads(data)
            except (OSError, ValueError):
                result = dict(ok=False, transportRejected=True)
        print(json.dumps(result)); return
    if mode != 'serve' or os.geteuid() != 0:
        raise ValueError('guest root server required')
    root = Path('/var/lib/peer-fixture'); root.mkdir(mode=0o755)
    (root / 'requests').mkdir(mode=0o755)
    profile = Path('/nix/var/nix/profiles/system')
    if not profile.exists():
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.symlink_to(Path('/run/current-system').resolve(strict=True))
    counts = dict(review=0, activation=0)
    def save(): (root / 'counts.json').write_text(json.dumps(counts))
    save()
    config = dict(target='metal', work=str(root / 'requests'), builderUser='builder', reviewerUser='reviewer',
                  baseline='/etc/phoenix-agent/activated-source', clientUid=1000, operatorUid=1001,
                  modelReviewEnabled=True, reviewHome='/home/reviewer', reviewScript=public['review'], nix='fixture-nix', nixStore='fixture-store',
                  python='fixture-python', controller=public['controller'], configPath='fixture',
                  authorizationPolicy=deploy.authorization.default_policy(True, 1000, 1001, updater=1002))
    def command(argv, **kwargs):
        if argv[0] != 'fixture-store': raise AssertionError('unexpected OS command')
        Path(argv[argv.index('--add-root') + 1]).symlink_to(argv[-1]); return b''
    review.run = command
    def decision(config, binding, *args):
        counts['review'] += 1; save()
        if binding['reason'] == 'error': raise review.ReviewVerdictError('review-invocation-failed')
        return dict(binding, approved=binding['reason'] != 'deny', summary='deterministic guest model double')
    review.review = decision
    def as_user(config, user, argv, run, **kwargs):
        if argv[:3] == ['fixture-nix', 'store', 'add-path']:
            if review.baseline_files(Path(argv[3])) != files: raise AssertionError('unexpected frozen files')
            return public['source'].encode()
        if argv[:2] == ['fixture-nix', 'build']: return public['closure'].encode()
        if user != 'reviewer': raise AssertionError('unexpected subprocess boundary')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()), contextlib.ExitStack() as stack:
            original = sys.stdin; sys.stdin = io.StringIO(kwargs['data'].decode())
            stack.callback(setattr, sys, 'stdin', original)
            deploy.worker(config, argv[-1])
        return output.getvalue().encode()
    def activate(*args):
        counts['activation'] += 1; save(); return dict(ok=True, activation=False)
    deploy.load_review = lambda _: review
    deploy.as_user = as_user
    deploy.activate_bound = activate
    # No changes to serve/process/process_inner/authorization or SO_PEERCRED.
    deploy.serve(config)


if __name__ == '__main__':
    main(*sys.argv[1:])
