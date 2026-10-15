#!/usr/bin/env python3
"""Explicit protected-UID live adapter trial; OS/build/activation remain stubs."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import re
import stat
import unittest


def immutable_file(value):
    path = Path(value).resolve(strict=True)
    info = path.stat()
    if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+(?:/[^/]+)*', str(path)) or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('immutable input required')
    return str(path)


def configuration(path):
    config = json.loads(Path(immutable_file(path)).read_text())
    if set(config) != {'codex', 'bwrap', 'caBundle', 'reviewHome', 'model', 'effort'}:
        raise ValueError('invalid trial configuration')
    if (config['reviewHome'], config['model'], config['effort']) != ('/var/lib/phoenix-deploy-review', 'gpt-6-luna', 'high'):
        raise ValueError('fixed reviewer identity/model required')
    for key in ('codex', 'bwrap', 'caBundle'):
        config[key] = immutable_file(config[key])
    if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-codex-0\.159\.0/bin/codex', config['codex']):
        raise ValueError('pinned reviewer CLI required')
    if Path(config['bwrap']).name != 'bwrap':
        raise ValueError('bubblewrap executable required')
    return config


class TrialResult(unittest.TestResult):
    """Retain only static exception codes and our fixture's source line."""
    def capture(self, case, error):
        value = getattr(error[1], 'code', None)
        if isinstance(value, str):
            case.live_failure = value  # Emission remains restricted by the allowlist.
        trace = error[2]
        while trace:
            if Path(trace.tb_frame.f_code.co_filename).resolve() == Path(__file__).with_name('agent-deployment.py').resolve():
                case.live_fixture_line = trace.tb_lineno
            trace = trace.tb_next

    def addError(self, case, error):
        self.capture(case, error)
        super().addError(case, error)

    def addFailure(self, case, error):
        self.capture(case, error)
        super().addFailure(case, error)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid-review', action='store_true')
    parser.add_argument('--config', help='reviewed immutable public configuration, never credentials')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    stage, code, calls = 'opt-in', 'opt-in-required', 0
    case = None
    try:
        if not args.dry_run and not args.allow_paid_review:
            raise ValueError('explicit paid-review opt-in required')
        stage, code = 'configuration', 'configuration-invalid'
        config = configuration(args.config) if args.config else None
        if args.dry_run:
            print(json.dumps(dict(status='dry-run', configured=config is not None, modelInvocationLimit=2,
                                  protectedUser='phoenix-deploy-review', activation='stubbed')))
            return 0
        if config is None:
            raise ValueError('immutable public auth-route configuration required')
        stage, code = 'identity', 'protected-identity-required'
        account = pwd.getpwnam('phoenix-deploy-review')
        if os.getuid() != account.pw_uid or os.geteuid() != account.pw_uid or account.pw_uid == 0:
            raise ValueError('run only as protected reviewer')
        stage, code = 'auth-home', 'auth-home-unavailable'
        home = Path(config['reviewHome']).lstat()
        if not stat.S_ISDIR(home.st_mode) or home.st_uid != account.pw_uid or home.st_mode & 0o077:
            raise ValueError('protected reviewer home unavailable')
        stage, code = 'fixture', 'fixture-assertion-failed'
        spec = importlib.util.spec_from_file_location('integration_fixture', Path(__file__).with_name('agent-deployment.py'))
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        case = fixture.DeploymentTests('test_controller_worker_adapter_and_checkpoints_as_one_disposable_workflow')
        case.live_review = config
        result = TrialResult()
        # Never emit fixture tracebacks, prompts, model verdicts or CLI stderr.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            case.run(result)
        if not result.wasSuccessful():
            raise ValueError('isolated live trial failed; no automatic retry')
        print(json.dumps(case.live_receipt, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        if case is not None:
            stage = getattr(case, 'live_stage', stage)
            calls = getattr(case, 'live_invocations', 0)
            candidate = getattr(case, 'live_failure', '')
            allowed = {'review-authentication-missing', 'review-authentication-failed',
                       'review-cli-incompatible-suspected', 'review-model-unavailable-suspected',
                       'review-rate-limit-suspected', 'review-transport-failed-suspected',
                       'review-startup-failed', 'review-timeout', 'review-output-limit',
                       'review-invocation-failed', 'reviewer-invocation-failed', 'schema-invalid',
                       'binding-mismatch', 'context-compacted', 'review-context-oversized',
                       'context-request-invalid', 'context-request-oversized', 'model-denied',
                       'baseline-authentication-required', 'baseline-policy-mismatch',
                       'baseline-provenance-missing', 'baseline-provenance-invalid',
                       'baseline-target-mismatch', 'baseline-runtime-mismatch',
                       'baseline-state-changed', 'baseline-verification-failed'}
            if candidate in allowed:
                code = candidate
        print(json.dumps(dict(status='blocked-or-failed', stage=stage, code=code,
                              modelInvocations=calls, fixtureLine=getattr(case, 'live_fixture_line', None),
                              activation='stubbed', retry=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
