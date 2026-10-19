#!/usr/bin/env python3
"""Focused fixtures for frozen-source review binding; no network or activation."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import shutil
import socket
import threading
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("deploy_review", Path(__file__).resolve().parents[5] / "modules/development/ai/agent/deploy-review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_native_operator_failures_reach_shared_cli_formatter(self):
        root = Path(__file__).resolve().parents[5]
        spec = importlib.util.spec_from_file_location('operator_deployment', root / 'modules/development/ai/agent/deployment.py')
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        with tempfile.TemporaryDirectory() as directory:
            operator_config = Path(directory) / 'operator.json'
            operator_config.write_text(json.dumps(dict(modelReviewEnabled=False)))
            client_config = Path(directory) / 'client.json'
            client_config.write_text(json.dumps(dict(clientOnly=True, operatorCommand=['fixture-operator'])))
            def snapshot(_config, source):
                for name in ('flake.nix', 'flake.lock'):
                    (source / name).write_text('{}')
                return 'a' * 40, {'flake.nix': '{}', 'flake.lock': '{}'}
            pending = deploy.DeploymentFailure('disruption', 'inspection-required')
            pending.pending_nonce = 'b' * 64
            pending.pending_metadata = dict(pendingKind='disruption', pendingSourceFingerprint='c' * 32,
                pendingTarget='metal', pendingAction='test', pendingClosureFingerprint='d' * 32 + '-nixos-system-fixture',
                proofLimit='unit-artifacts-only', findings=['system:fixture.service:changed-or-removed'])
            for mode in ('overflow', 'pending'):
                def operator_run(argv, *, data, **kwargs):
                    self.assertEqual(argv, ['fixture-operator'])
                    output = io.StringIO()
                    with mock.patch.object(sys, 'argv', ['deployment', str(operator_config), 'operator']), \
                         mock.patch.object(sys, 'stdin', mock.Mock(buffer=io.BytesIO(data))), \
                         mock.patch.object(deploy.os, 'geteuid', return_value=0), \
                         mock.patch.object(deploy, 'LIMIT', len(data) - 1 if mode == 'overflow' else deploy.LIMIT), \
                         mock.patch.object(deploy, 'process', side_effect=pending) as process, \
                         contextlib.redirect_stdout(output):
                        deploy.main()
                    envelope = json.loads(output.getvalue())
                    self.assertFalse(envelope['ok'])
                    if mode == 'overflow':
                        process.assert_not_called()
                        self.assertEqual((envelope['stage'], envelope['code']), ('source-transport', 'wire-capacity-exceeded'))
                    else:
                        process.assert_called_once()
                        self.assertTrue(process.call_args.kwargs['operator'])
                    return output.getvalue().encode()
                stderr = io.StringIO()
                with self.subTest(mode=mode), \
                     mock.patch.object(sys, 'argv', ['deploy-review', str(client_config), '--target', 'metal', '--action', 'test', '--reason', 'Diagnostic fixture']), \
                     mock.patch.object(review, 'snapshot', side_effect=snapshot), \
                     mock.patch.object(review, 'git', return_value=b'main'), \
                     mock.patch.object(review, 'warn_deployment_diff'), \
                     mock.patch.object(review, 'run', side_effect=operator_run), \
                     contextlib.redirect_stderr(stderr), self.assertRaises(ValueError) as failure:
                    review.main()
                expected = 'wire-capacity-exceeded' if mode == 'overflow' else 'inspection-required'
                self.assertIn(expected, str(failure.exception))
                if mode == 'pending':
                    self.assertTrue(stderr.getvalue().startswith('WARNING: Protected unit inspection requires approval: '))
                    self.assertIn('--disruption-override ' + pending.pending_nonce, stderr.getvalue())
                    display = json.loads(stderr.getvalue().splitlines()[0].removeprefix('WARNING: Protected unit inspection requires approval: '))
                    for key, value in pending.pending_metadata.items():
                        self.assertEqual(display[key], value)

    def test_security_pending_failure_is_visibly_critical(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaisesRegex(ValueError, 'review.*model-denied'):
            review.deployment_failure(dict(stage='review', code='model-denied', pendingNonce='a' * 64,
                pendingKind='security', summary='The change weakens authentication.'))
        self.assertTrue(stderr.getvalue().startswith('Reviewer explanation (advisory): The change weakens authentication.'))
        self.assertLess(stderr.getvalue().index('Reviewer explanation'), stderr.getvalue().index('--security-override'))
        self.assertIn('--security-override ' + 'a' * 64, stderr.getvalue())
        self.assertNotIn('PRIVATE', stderr.getvalue())

    def test_denial_summary_is_bounded_and_controls_are_removed(self):
        for summary in [None, {}, [], 42, '', '\x1b\n\r\u202e', 'reason\x1b\n\r\u202e' + 'x' * 2000]:
            with self.subTest(summary=repr(summary)[:40]):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(ValueError):
                    review.deployment_failure(dict(stage='review', code='model-denied', summary=summary))
                output = stderr.getvalue()
                self.assertEqual(len(output.splitlines()), 1)
                self.assertNotIn('\x1b', output)
                self.assertNotIn('\u202e', output)
                self.assertLessEqual(len(output), len('Reviewer explanation (advisory): ') + 1001)
                if not isinstance(summary, str) or not summary or summary.startswith('\x1b'):
                    self.assertIn('No reviewer explanation was provided.', output)

    def test_denial_notification_is_generic_and_failure_does_not_hide_denial(self):
        for outcome in [b'', OSError('no session'), subprocess.TimeoutExpired('notify', 2)]:
            stderr = io.StringIO()
            with mock.patch.object(review, 'run', side_effect=outcome if isinstance(outcome, Exception) else None,
                                   return_value=b'') as run, contextlib.redirect_stderr(stderr), self.assertRaises(ValueError):
                review.deployment_failure(dict(stage='review', code='model-denied', summary='private rationale'),
                                          dict(notifySend='/fixture/notify-send'))
            self.assertIn('private rationale', stderr.getvalue())
            self.assertNotIn('private rationale', str(run.call_args))
            self.assertEqual(run.call_args.kwargs['timeout'], 2)
        for executable in [None, 'notify-send', ['sh', '-c']]:
            with mock.patch.object(review, 'run') as run, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(ValueError):
                review.deployment_failure(dict(stage='review', code='model-denied'), dict(notifySend=executable))
            run.assert_not_called()

    def test_failure_formatter_omits_untrusted_text_and_invalid_metadata(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaisesRegex(ValueError, 'protocol.*invalid-or-denied'):
            review.deployment_failure(dict(stage=['PRIVATE'], code='PRIVATE raw stderr', error='PRIVATE native',
                summary='PRIVATE model text', pendingNonce='PRIVATE nonce', findings=['PRIVATE source text']))
        self.assertEqual(stderr.getvalue(), '')

    def test_selected_worktree_reaches_authenticated_snapshot(self):
        root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = base / "repo"
            repo.mkdir()
            def git(*args):
                subprocess.run(["git", "-C", str(repo), *args], check=True,
                               capture_output=True)
            git("init", "-b", "main")
            (repo / "flake.nix").write_text("{}")
            (repo / "flake.lock").write_text("{}")
            git("add", "flake.nix", "flake.lock")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-m", "fixture")
            other = base / "home/.codex/worktrees/task/repo"
            other.parent.mkdir(parents=True)
            git("worktree", "add", "-b", "feature", str(other))
            (other / "flake.nix").write_text("dirty selected content")
            executable = base / "selector"
            executable.write_text((root / "commands/phoenix-source").read_text().replace(
                "#!/usr/bin/env python3", "#!" + sys.executable))
            executable.chmod(0o755)
            config = base / "config.json"
            config.write_text(json.dumps(dict(repo=str(repo), git=shutil.which("git"),
                sourceSelector=str(executable), clientOnly=True, modelReviewEnabled=False)))
            original_snapshot = review.snapshot
            def snapshot(cfg, destination):
                self.assertEqual(cfg["repo"], str(other))
                _, files = original_snapshot(cfg, destination)
                self.assertEqual(files["flake.nix"], "dirty selected content")
                raise RuntimeError("stop before authentication or activation")
            for selector in (("--branch", "feature"), ("--worktree", str(other))):
                with mock.patch.object(sys, "argv", ["deploy-review", str(config), *selector,
                        "--target", "vm", "--reason", "fixture", "--action", "test"]), \
                     mock.patch.object(review, "snapshot", side_effect=snapshot), \
                     self.assertRaisesRegex(RuntimeError, "stop before authentication"):
                    review.main()
            self.assertEqual((repo / "flake.nix").read_text(), "{}")
            self.assertEqual(subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"]).strip(), b"main")

    def test_review_enabled_sandbox_worktree_reaches_socket_submission(self):
        import os

        root = Path(__file__).resolve().parents[5]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo = base / "repo"
            repo.mkdir()

            def git(*args):
                subprocess.run(["git", "-C", str(repo), *args], check=True,
                               capture_output=True)

            git("init", "-b", "main")
            for name in ("flake.nix", "flake.lock"):
                (repo / name).write_text("{}")
            git("add", ".")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-m", "fixture")
            other = base / "home/.codex/worktrees/task/repo"
            other.parent.mkdir(parents=True)
            git("worktree", "add", "-b", "feature", str(other))
            (other / "flake.nix").write_text("dirty selected content")
            (other / "new.nix").write_text("new selected content")

            record = base / "request.json"
            controller = base / "authenticated-stub"
            controller.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                "from pathlib import Path\n"
                "request = json.load(sys.stdin)\n"
                f"Path({str(record)!r}).write_text(json.dumps(request))\n"
                "print(json.dumps({'ok': True}))\n"
            )
            controller.chmod(0o755)
            selector = base / "phoenix-source"
            selector.write_text((root / "commands/phoenix-source").read_text().replace(
                "#!/usr/bin/env python3", "#!" + sys.executable))
            selector.chmod(0o755)
            cfg = base / "config.json"
            config = dict(repo=str(repo), git=shutil.which("git"),
                          sourceSelector=str(selector), clientOnly=True,
                          modelReviewEnabled=True, sandboxClient=True, operatorCommand=[],
                          deploymentSocket=str(base / "deployment.sock"))
            cfg.write_text(json.dumps(config))
            helper = base / "client"
            client_script = root / "modules/development/ai/agent/deploy-review.py"
            helper.write_text(
                f'#!/bin/sh\nexec {sys.executable} {client_script} {cfg} "$@"\n'
            )
            helper.chmod(0o755)
            # The agent route invokes this immutable client, never the human rebuild
            # wrapper's deliberately ignored legacy helper environment variable.
            env = os.environ | {"PATH": str(base) + ":" + os.environ["PATH"]}
            args = [str(helper), "--target", "metal", "--action", "test",
                    "--branch", "feature", "--reason", "Validate requested dirty source"]
            # Actual sandbox shape: review ON, no baseline/host authentication,
            # real selector/freeze, and a fixed local socket controller double.
            self.assertNotIn("baseline", config)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(config["deploymentSocket"])
                listener.listen()
                listener.settimeout(3)
                response = b'{"ok":true}\n'
                def submit():
                    try:
                        connection, _ = listener.accept()
                    except socket.timeout:
                        return
                    with connection, connection.makefile("rb") as stream:
                        request = json.loads(stream.readline())
                        record.write_text(json.dumps(request))
                        connection.sendall(response)
                worker = threading.Thread(target=submit)
                worker.start()
                try:
                    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10)
                finally:
                    worker.join(timeout=4)
                self.assertFalse(worker.is_alive())
                response = json.dumps(dict(ok=False, stage='review', code='model-denied',
                                           summary='Synthetic authentication concern.', pendingKind='security',
                                           pendingNonce='a' * 64)).encode() + b'\n'
                worker = threading.Thread(target=submit)
                worker.start()
                try:
                    denied = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10)
                finally:
                    worker.join(timeout=4)
                self.assertFalse(worker.is_alive())
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn('Reviewer explanation (advisory): Synthetic authentication concern.', denied.stderr)
                self.assertLess(denied.stderr.index('Reviewer explanation'), denied.stderr.index('--security-override'))
            self.assertEqual(result.returncode, 0, result.stderr)
            request = json.loads(record.read_text())
            self.assertEqual(request["reason"], "Validate requested dirty source")
            self.assertEqual(request["files"]["flake.nix"], "dirty selected content")
            self.assertEqual(request["files"]["new.nix"], "new selected content")
            self.assertEqual((request["target"], request["action"]), ("metal", "test"))

            controller.write_text("#!/bin/sh\nexit 23\n")
            config.update(modelReviewEnabled=False, sandboxClient=False, operatorCommand=[str(controller)])
            cfg.write_text(json.dumps(config))
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            config["sandboxClient"] = True
            cfg.write_text(json.dumps(config))
            result = subprocess.run(args, env=env, capture_output=True, text=True)
            self.assertIn("host Polkit authentication", result.stderr)
            self.assertNotEqual(result.returncode, 0)

    def test_verdict_binding(self):
        binding = {"source": "/nix/store/source", "nonce": "fresh", "target": "metal", "closure": "/nix/store/bound-system"}
        good = dict(binding, approved=True, summary="reviewed")
        review.validate_verdict(good, binding)
        for bad in [dict(good, nonce="old"), dict(good, source="other"),
                    dict(good, approved=False), dict(good, approved="true"),
                    dict(good, closure="/nix/store/other-system"), dict(good, untrusted_extra=True), {"approved": True}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                review.validate_verdict(bad, binding)

    def test_diff_only_first_prompt_and_one_context_round(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            config = self.review_config(temporary)
            binding = {'source': 'frozen', 'nonce': 'fresh'}
            candidate = {'a.nix': 'changed\nsecret-unrequested-context\n', 'private': 'never sent'}
            baseline = {'a.nix': 'original\ncontext needed\n'}
            prompts = []
            def fixture(argv, **kwargs):
                prompt = kwargs['data'].decode()
                prompts.append(prompt)
                if len(prompts) == 1:
                    self.assertNotIn('secret-unrequested-context', prompt)
                    self.assertNotIn('never sent', prompt)
                    self.assertNotIn('full_source', prompt)
                    verdict = dict(binding, approved=None, summary='need authority context',
                        context=[dict(source='baseline', path='a.nix', start=2, end=2)])
                else:
                    self.assertIn('context needed', prompt)
                    self.assertNotIn('secret-unrequested-context', prompt)
                    schema = json.loads((temporary/'work/schema.json').read_text())
                    self.assertNotIn('context', schema['properties'])
                    verdict = dict(binding, approved=True, summary='safe')
                (temporary/'work/verdict.json').write_text(json.dumps(verdict))
                return b''
            with mock.patch.object(review, 'run', side_effect=fixture):
                result = review.review(config, binding, candidate, '-original\n+changed\n', temporary, baseline)
            self.assertTrue(result['approved'])
            self.assertEqual(len(prompts), 2)

    def test_context_resolver_rejects_unbounded_and_foreign_access(self):
        sources = {'candidate': {'x': 'one\ntwo\n'}, 'baseline': {}}
        good = dict(source='candidate', path='x', start=1, end=1)
        self.assertEqual(review.resolve_context([good], sources)[0]['text'], 'one\n')
        for request in [dict(good,path='/etc/passwd'), dict(good,path='../x'), dict(good,source='store'),
                        dict(good,start=0), dict(good,end=3), dict(good,start=True), dict(good,command='cat')]:
            with self.subTest(request=request), self.assertRaises(review.ReviewVerdictError):
                review.resolve_context([request], sources)
        with self.assertRaises(review.ReviewVerdictError): review.resolve_context([good]*9,sources)
        with self.assertRaises(review.ReviewVerdictError):
            review.resolve_context([good], {'candidate': {'x': 'x'*(review.CONTEXT_LIMIT+1)}, 'baseline': {}})

    def test_second_context_request_fails_without_third_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory); config=self.review_config(temporary); binding={'source':'frozen'}
            verdict=dict(binding,approved=None,summary='need context',context=[dict(source='candidate',path='x',start=1,end=1)])
            def fixture(*args,**kwargs):
                (temporary/'work/verdict.json').write_text(json.dumps(verdict)); return b''
            with mock.patch.object(review,'run',side_effect=fixture) as calls:
                with self.assertRaises(review.ReviewVerdictError): review.review(config,binding,{'x':'one'},'diff',temporary)
            self.assertEqual(calls.call_count,2)

    def test_first_final_schema_and_secret_safe_process_diagnostics(self):
        for approved in [True, False]:
            with tempfile.TemporaryDirectory() as directory:
                temporary=Path(directory);config=self.review_config(temporary);binding={'source':'frozen'}
                def fixture(*args,**kwargs):
                    (temporary/'work/verdict.json').write_text(json.dumps(dict(binding,approved=approved,summary='security decision',context=[])))
                    return b''
                with mock.patch.object(review,'run',side_effect=fixture) as calls:
                    if approved:self.assertTrue(review.review(config,binding,{},'diff',temporary)['approved'])
                    else:
                        with self.assertRaises(review.ReviewDenied):review.review(config,binding,{},'diff',temporary)
                self.assertEqual(calls.call_count,1)
        with self.assertRaises(review.ReviewVerdictError) as failure:
            review.run([sys.executable,'-c',"import sys; print('401 Unauthorized SECRET',file=sys.stderr); sys.exit(1)"],fail_on_compaction=True)
        self.assertEqual(failure.exception.code,'review-authentication-failed')
        self.assertNotIn('SECRET',str(failure.exception))

    def test_cli_errors_remain_static_and_untrusted_diagnostics(self):
        cases = [('unexpected argument --secret', 'review-cli-incompatible-suspected'),
                 ('model not found SECRET', 'review-model-unavailable-suspected'),
                 ('rate limit SECRET', 'review-rate-limit-suspected'),
                 ('error sending request SECRET', 'review-transport-failed-suspected'),
                 ('source contains 401 SECRET', 'review-invocation-failed')]
        for message, code in cases:
            with self.subTest(code=code), self.assertRaises(review.ReviewVerdictError) as failure:
                review.run([sys.executable, '-c', 'import sys; print(' + repr(message) + ',file=sys.stderr); sys.exit(1)'], fail_on_compaction=True)
            self.assertEqual(failure.exception.code, code)
            self.assertNotIn('SECRET', str(failure.exception))

    def test_large_diff_warning_is_estimate_only_and_notification_is_optional(self):
        small='x'*(4*(review.LARGE_DIFF_WARNING_TOKENS-1))
        large='x'*(4*review.LARGE_DIFF_WARNING_TOKENS)
        with mock.patch.object(review,'run') as run,contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(review.warn_large_diff({'notifySend':'/fixed/notify-send'},small),23999)
            run.assert_not_called();self.assertEqual(output.getvalue(),'')
            self.assertEqual(review.warn_large_diff({'notifySend':'/fixed/notify-send'},large),24000)
            argv=run.call_args.args[0]
            self.assertEqual(argv[0],'/fixed/notify-send')
            self.assertEqual(run.call_args.kwargs['timeout'],2)
            self.assertIn('estimated from characters / 4',output.getvalue())
            self.assertIn('does not limit deployment',output.getvalue())
        for notification in [None,'relative-command',['sh','-c']]:
            with mock.patch.object(review,'run') as run,contextlib.redirect_stderr(io.StringIO()):
                review.warn_large_diff({'notifySend':notification},large)
            run.assert_not_called()
        with mock.patch.object(review,'run',side_effect=OSError('notification unavailable')),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(review.warn_large_diff({'notifySend':'/fixed/notify-send'},large),24000)

    def test_bounded_process(self):
        self.assertEqual(review.run([sys.executable, "-c", "print('ok')"]), b"ok\n")
        self.assertEqual(review.run([sys.executable, "-c", "import sys; print(\"path\"); print(\"log\", file=sys.stderr)"]), b"path\n")
        with self.assertRaises(ValueError):
            review.run([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.05)
        with self.assertRaises(ValueError):
            review.run([sys.executable, "-c", "print('x' * 3000000)"])

    def test_update_build_streams_before_exit_and_retains_failure_tail(self):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / 'observed'
            script = ("import sys,time,pathlib; print('building package',file=sys.stderr,flush=True); "
                      "time.sleep(.2); assert pathlib.Path(sys.argv[1]).exists(); "
                      "print('specific build failure',file=sys.stderr); sys.exit(7)")
            def progress(text):
                events.append(text)
                receipt.touch()
            with self.assertRaises(review.BuildError) as failure:
                review.run_build([sys.executable, '-c', script, str(receipt)], progress=progress)
        self.assertEqual(failure.exception.code, 'build-failed')
        self.assertIn('specific build failure', failure.exception.diagnostics)
        self.assertIn('building package', ''.join(events))

    def test_update_build_verbose_stderr_does_not_abort_build(self):
        result = review.run_build([sys.executable, '-c',
            "import sys; sys.stderr.write('x'*3000000); print('/closure')"])
        self.assertEqual(result, b'/closure\n')
        with self.assertRaises(review.BuildError) as failure:
            review.run_build([sys.executable, '-c', 'import time; time.sleep(2)'], timeout=.05)
        self.assertEqual(failure.exception.code, 'build-timeout')

    def test_bounded_process_rejects_compaction_marker(self):
        for marker in ["context compacted\n", "log\ncontext compacted\nnext\n"]:
            with self.subTest(marker=marker), self.assertRaises(review.ReviewVerdictError) as rejected:
                review.run([sys.executable, "-c", "import sys; sys.stderr.write(" + repr(marker) + ")"],
                           fail_on_compaction=True)
            self.assertEqual(rejected.exception.code, "context-compacted")
        self.assertEqual(review.run([sys.executable, "-c", "import sys; print('quoted context compacted text', file=sys.stderr); print('ok')"],
                                    fail_on_compaction=True), b"ok\n")

    def review_config(self, temporary, policy_text="trusted policy"):
        state = temporary / "state"
        state.mkdir()
        (state / "auth.json").write_text("fixture-only-auth")
        policy = temporary / "policy"
        policy.write_text(policy_text)
        return dict(reviewHome=str(state), policy=str(policy), bwrap="bwrap", codex="codex",
                    model="gpt-6.1-sol", effort="medium", caBundle="/nix/store/cert/ca-bundle.crt")

    def test_complete_serialized_instruction_and_schema_bound(self):
        for binding, policy_text, files, diff in [
            ({"source": "frozen"}, "p" * 400000, {"source.nix": "s" * 400000}, "d" * 700000),
            ({"source": "b" * 250000}, "p" * 600000, {}, ""),
        ]:
            with self.subTest(schema_binding=len(binding['source'])), tempfile.TemporaryDirectory() as directory:
                temporary = Path(directory)
                config = self.review_config(temporary, policy_text)
                source = temporary / "source"
                source.mkdir()
                for name, text in files.items():
                    (source / name).write_text(text)
                with mock.patch.object(review, "run") as run:
                    with self.assertRaises(review.ReviewVerdictError) as rejected:
                        review.review(config, binding, files, diff, temporary)
                    self.assertEqual(rejected.exception.code, "review-context-oversized")
                    run.assert_not_called()

    def test_compacted_child_verdict_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            config = self.review_config(temporary)
            binding = {"source": "frozen", "nonce": "fresh"}
            verdict = dict(binding, approved=True, summary="looks valid but compacted")
            original_run = review.run
            def execute_fixture(argv, **kwargs):
                self.assertIn("--color", argv)
                self.assertEqual(argv[argv.index("--color") + 1], "never")
                self.assertNotIn("--json", argv)
                self.assertNotIn("model_context_window", " ".join(argv))
                script = ("from pathlib import Path; import sys; "
                          "Path(" + repr(str(temporary / "work/verdict.json")) + ").write_text(" + repr(json.dumps(verdict)) + "); "
                          "print('context compacted', file=sys.stderr)")
                return original_run([sys.executable, "-c", script], **kwargs)
            with mock.patch.object(review, "run", side_effect=execute_fixture), mock.patch.object(review, "validate_verdict") as validate:
                with self.assertRaises(review.ReviewVerdictError) as rejected:
                    review.review(config, binding, {}, "", temporary)
                self.assertEqual(rejected.exception.code, "context-compacted")
                validate.assert_not_called()
                self.assertEqual(json.loads((temporary / "work/verdict.json").read_text()), verdict)

    def test_source_resource_bound_keeps_all_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory)
            text = "x" * (512 * 1024 + 1)
            (baseline / "complete.nix").write_text(text)
            self.assertEqual(review.baseline_files(baseline), {"complete.nix": text})
            (baseline / "complete.nix").write_text("x" * (review.SOURCE_LIMIT + 1))
            with self.assertRaisesRegex(ValueError, "source transport capacity"):
                review.baseline_files(baseline)
        self.assertEqual(review.SOURCE_LIMIT, 4 * 1024 * 1024)
        self.assertEqual(review.REVIEW_INPUT_LIMIT, 1024 * 1024)
        self.assertEqual(review.OUTPUT_LIMIT, 2 * 1024 * 1024)

    def test_deployed_diff(self):
        diff = review.source_diff({"old": "retired\n", "same": "old\n"}, {"same": "new\n", "added": "yes\n"})
        self.assertIn("-retired", diff)
        self.assertIn("+new", diff)
        self.assertIn("+yes", diff)

    def test_reviewer_certificate_mount_is_self_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            state = temporary / "state"
            state.mkdir()
            (state / "auth.json").write_text("{}")
            policy = temporary / "policy"
            policy.write_text("trusted policy")
            config = dict(reviewHome=str(state), policy=str(policy), bwrap="bwrap", codex="codex",
                          model="gpt-6.1-sol", effort="medium", caBundle="/nix/store/cert/ca-bundle.crt")
            with mock.patch.object(review, "run", side_effect=ValueError("probe stopped")) as run:
                with self.assertRaisesRegex(ValueError, "probe stopped"):
                    review.review(config, {"source": "frozen"}, {}, "", temporary)
                argv = run.call_args.args[0]
                mounts = [argv[index + 1:index + 3] for index, value in enumerate(argv) if value == "--ro-bind"]
                self.assertIn([config["caBundle"], "/etc/ssl/certs/ca-certificates.crt"], mounts)
                self.assertIn([config["caBundle"], "/etc/ssl/certs/ca-bundle.crt"], mounts)
                self.assertNotIn(["/etc/ssl", "/etc/ssl"], mounts)
                self.assertNotIn(["/etc", "/etc"], mounts)
                location = argv.index("SSL_CERT_FILE")
                self.assertEqual(argv[location + 1], "/etc/ssl/certs/ca-certificates.crt")
                self.assertIn("--clearenv", argv)

    def test_baseline_keeps_all_effective_files(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory)
            (baseline / "ignored-but-effective.nix").write_text("must review")
            self.assertEqual(review.baseline_files(baseline), {"ignored-but-effective.nix": "must review"})
            (baseline / ".git").mkdir()
            with self.assertRaisesRegex(ValueError, "Git metadata"):
                review.baseline_files(baseline)
            (baseline / ".git").rmdir()
            (baseline / "escape").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "symlink"):
                review.baseline_files(baseline)

    def test_mode_changes_and_private_bounded_audit(self):
        self.assertIn("100644 -> 100755", review.source_diff({"script": "same"}, {"script": "same"},
                      {"script": "100644"}, {"script": "100755"}))
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = {"reviewHome": str(home)}
            binding = dict(source="store", commit="sha", base="deployed", target="metal", action="review", reason="secret-prompt", nonce="non-reusable")
            review.audit(config, binding, "review-failed")
            self.assertFalse((home / "audit.jsonl").exists())
            (home / "auth.json").write_text("credential-must-not-log")
            review.audit(config, binding, "review-approved", dict(approved=True, summary="fine"))
            log = home / "audit.jsonl"
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("secret-prompt", log.read_text())
            self.assertNotIn("credential-must-not-log", log.read_text())
            self.assertNotIn("non-reusable", log.read_text())
            log.write_text("x" * review.OUTPUT_LIMIT)
            review.audit(config, binding, "built", dict(approved=True, summary="fine"), "closure")
            self.assertTrue((home / "audit.previous.jsonl").exists())
            self.assertEqual(json.loads(log.read_text())["closure"], "closure")
            log.unlink(); log.symlink_to(home / "auth.json")
            with self.assertRaises(OSError):
                review.audit(config, binding, "built")
            self.assertEqual((home / "auth.json").read_text(), "credential-must-not-log")

    def test_snapshot_includes_working_tree_and_git_visible_untracked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, frozen = root / "repo", root / "frozen"
            repo.mkdir(); frozen.mkdir()
            git = shutil.which("git")
            def execute(*args):
                subprocess.run([git, "-C", str(repo), *args], check=True, capture_output=True)
            execute("init")
            execute("config", "user.name", "Fixture")
            execute("config", "user.email", "fixture@example.invalid")
            for name, text in {"flake.nix": "{}", "flake.lock": "{}", ".gitattributes": "kept export-ignore\n", "kept": "must-review", "large": "x" * (512 * 1024 + 1)}.items():
                (repo / name).write_text(text)
            execute("add", "."); execute("commit", "-m", "fixture")
            helper = root / "rogue-fsmonitor"
            marker = root / "executed"
            helper.write_text("#!/bin/sh\ntouch " + str(marker) + "\n")
            helper.chmod(0o755)
            execute("config", "core.fsmonitor", str(helper))
            config = {"repo": str(repo), "git": git}
            commit, files = review.snapshot(config, frozen)
            self.assertFalse(marker.exists(), "repository fsmonitor must never run on host")
            self.assertEqual(files["kept"], "must-review")
            self.assertEqual((frozen / "kept").read_text(), "must-review")
            self.assertEqual(files["large"], "x" * (512 * 1024 + 1))
            (repo / "kept").write_text("working tree edit")
            (repo / "untracked").write_text("include me")
            (repo / "untracked").chmod(0o755)
            (repo / ".gitignore").write_text("private-note\n")
            (repo / "private-note").write_text("ignored data")
            execute("add", ".gitignore")
            edited, files = review.snapshot(config, root / "edited")
            self.assertEqual(edited, commit, "HEAD remains informational provenance")
            self.assertEqual(files["kept"], "working tree edit")
            self.assertEqual(files["untracked"], "include me")
            self.assertNotIn("private-note", files)
            self.assertEqual((root / "edited/kept").read_text(), "working tree edit")
            self.assertTrue((root / "edited/untracked").stat().st_mode & 0o111)
            (repo / "kept").unlink()
            _, files = review.snapshot(config, root / "deleted")
            self.assertNotIn("kept", files)
            self.assertEqual((repo / "kept").exists(), False)
            (repo / "kept").write_text("working tree edit")
            (repo / "untracked").unlink()
            (repo / "private-note").unlink()
            (repo / ".gitignore").unlink()
            (repo / "large").write_text("x" * (review.SOURCE_LIMIT + 1))
            with self.assertRaisesRegex(ValueError, "source exceeds transport capacity"):
                review.snapshot(config, root / "unused")
            (repo / "large").write_text("x")
            (repo / "escape").symlink_to("/etc/passwd")
            with self.assertRaises(ValueError):
                review.snapshot(config, root / "unused")


    def test_unsupported_adapter_is_typed_before_auth_or_execution(self):
        with mock.patch.object(review, 'run') as run, self.assertRaises(review.ReviewVerdictError) as failure:
            review.review({'adapter': 'other'}, {}, {}, '', Path('/unused'))
        self.assertEqual(failure.exception.code, 'review-adapter-unsupported')
        run.assert_not_called()

if __name__ == "__main__":
    unittest.main()
