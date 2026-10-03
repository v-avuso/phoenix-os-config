#!/usr/bin/env python3
"""Focused fixtures for frozen-source review binding; no network or activation."""
import importlib.util
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
    def test_verdict_binding(self):
        binding = {"source": "/nix/store/source", "nonce": "fresh", "target": "metal"}
        good = dict(binding, approved=True, summary="reviewed")
        review.validate_verdict(good, binding)
        for bad in [dict(good, nonce="old"), dict(good, source="other"),
                    dict(good, approved=False), dict(good, approved="true"),
                    dict(good, untrusted_extra=True), {"approved": True}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                review.validate_verdict(bad, binding)

    def test_bounded_process(self):
        self.assertEqual(review.run([sys.executable, "-c", "print('ok')"]), b"ok\n")
        self.assertEqual(review.run([sys.executable, "-c", "import sys; print(\"path\"); print(\"log\", file=sys.stderr)"]), b"path\n")
        with self.assertRaises(ValueError):
            review.run([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.05)
        with self.assertRaises(ValueError):
            review.run([sys.executable, "-c", "print('x' * 3000000)"])

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

    def test_frozen_blobs_and_dirty_rejection(self):
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
            for name, text in {"flake.nix": "{}", "flake.lock": "{}", ".gitattributes": "kept export-ignore\n", "kept": "must-review"}.items():
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
            (repo / "dirty").write_text("untracked")
            with self.assertRaises(ValueError):
                review.snapshot(config, root / "unused")
            (repo / "dirty").unlink()
            (repo / "escape").symlink_to("/etc/passwd")
            execute("add", "."); execute("commit", "-m", "symlink")
            with self.assertRaises(ValueError):
                review.snapshot(config, root / "unused")


if __name__ == "__main__":
    unittest.main()
