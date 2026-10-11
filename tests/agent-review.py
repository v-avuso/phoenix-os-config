#!/usr/bin/env python3
"""Focused fixtures for frozen-source review binding; no network or activation."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("deploy_review", Path(__file__).resolve().parents[1] / "modules/development/ai/agent/deploy-review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_selected_worktree_reaches_authenticated_snapshot(self):
        root = Path(__file__).resolve().parents[1]
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
            other = base / "other worktree"
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
            review.run([sys.executable,'-c',"import sys; print('401 authentication SECRET',file=sys.stderr); sys.exit(1)"],fail_on_compaction=True)
        self.assertEqual(failure.exception.code,'review-authentication-failed')
        self.assertNotIn('SECRET',str(failure.exception))

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


if __name__ == "__main__":
    unittest.main()
