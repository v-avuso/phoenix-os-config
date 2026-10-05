#!/usr/bin/env python3
"""CLI-boundary fixtures for isolated update candidate preparation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules/services/updates"))
import candidate


class CandidateFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "fixture")
        self._git("config", "user.email", "fixture@example.invalid")
        self._git("config", "commit.gpgSign", "false")
        (self.repo / "flake.nix").write_text("{ outputs = { self }: { }; }\n")
        (self.repo / "flake.lock").write_text(json.dumps(self.lock(), sort_keys=True) + "\n")
        self._git("add", "flake.nix", "flake.lock")
        self._git("commit", "-qm", "baseline")
        self.head = self._git("rev-parse", "HEAD").stdout.strip()
        self.approved = self.root / "approved"
        self.approved.mkdir()
        for name in ("flake.nix", "flake.lock"):
            (self.approved / name).write_bytes((self.repo / name).read_bytes())
        self.nix = self.root / "nix-fixture.py"
        self.nix.write_text("""#!%s
import json, pathlib, sys
if '--override-input' not in sys.argv or '--output-lock-file' not in sys.argv:
    raise SystemExit(3)
lock_path = pathlib.Path('flake.lock')
data = json.loads(lock_path.read_text())
alias = sys.argv[sys.argv.index('--override-input') + 1]
source = sys.argv[sys.argv.index('--override-input') + 2]
revision = source.rsplit('/', 1)[-1]
node = data['nodes'][data['nodes']['root']['inputs'][alias]]
node['locked']['rev'] = revision
lock_path.write_text(json.dumps(data, sort_keys=True) + '\\n')
""" % sys.executable)
        self.nix.chmod(0o755)
        self.requests = []

    def _git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.repo), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    @staticmethod
    def lock():
        inputs = {name: name for name in candidate.INPUTS}
        nodes = {"root": {"inputs": inputs}}
        for name, (owner, repo, ref) in candidate.INPUTS.items():
            nodes[name] = {"original": {"ref": ref, "owner": owner, "repo": repo},
                           "locked": {"rev": "1" * 40, "owner": owner, "repo": repo},
                           "inputs": {}}
        return {"version": 7, "root": "root", "nodes": nodes}

    def config(self):
        state = self.root / "state"
        return {"repo": str(self.repo), "state": str(state), "git": shutil.which("git"),
                "nix": str(self.nix), "nixHome": str(state / "nix-home"), "approvedCommit": self.head,
                "approvedSource": str(self.approved), "requireStore": False,
                "controllerSocket": "/tmp/unused-controller.sock", "target": "metal"}

    def request(self, **changes):
        request = {"version": 1, "mainHead": self.head, "observationOk": True,
                   "applications": ["firefox"],
                   "pins": {"nixpkgs-updates-fast": {"revision": "2" * 40,
                                                        "days": 1,
                                                        "source": "nixos-26.05"}}}
        request.update(changes)
        return request

    def test_dirty_unrelated_file_and_normal_pins_survive_controller_rejection(self):
        dirty = self.repo / "personal-note.txt"
        dirty.write_text("keep my edit\n")
        def reject(_socket_path, _target, _commit, files, modes, _timeout):
            self.requests.append({"action": "boot", "reason": candidate.REASON,
                                  "files": files, "modes": modes})
            return {"ok": False, "reason": "fixture rejection"}
        with patch.object(candidate, "_controller", reject):
            result = candidate.prepare(self.config(), self.request())
        self.assertEqual(result["status"], "controller-rejected")
        self.assertEqual(dirty.read_text(), "keep my edit\n")
        self.assertEqual(self.requests[0]["action"], "boot")
        self.assertEqual(self.requests[0]["reason"], candidate.REASON)
        self.assertEqual(self._git("rev-parse", "HEAD").stdout.strip(), self.head)
        lock = json.loads((self.repo / "flake.lock").read_text())
        self.assertEqual(lock["nodes"]["nixpkgs-updates-fast"]["locked"]["rev"], "1" * 40)
        self.assertNotEqual(result["status"], "running")
        self.assertTrue(result["mergeBackRequired"])

    def test_failed_observation_does_not_create_worktree_or_change_head(self):
        with self.assertRaises(candidate.CandidateError):
            candidate.prepare(self.config(), self.request(observationOk=False))
        self.assertEqual(self._git("rev-parse", "HEAD").stdout.strip(), self.head)

    def test_dirty_or_staged_lock_is_never_overwritten(self):
        lock = self.repo / "flake.lock"
        lock.write_text("user lock edit\n")
        self._git("add", "flake.lock")
        result = candidate.prepare(self.config(), self.request())
        self.assertEqual(result["status"], "pending-integration")
        self.assertEqual(lock.read_text(), "user lock edit\n")
        self.assertIn("M  flake.lock", self._git("status", "--porcelain=v1").stdout)

    def test_staged_unrelated_edit_survives_candidate_preparation(self):
        staged = self.repo / "user-config.txt"
        staged.write_text("keep staged edit\n")
        self._git("add", "user-config.txt")
        def reject(_socket_path, _target, _commit, _files, _modes, _timeout):
            return {"ok": False}
        with patch.object(candidate, "_controller", reject):
            result = candidate.prepare(self.config(), self.request())
        self.assertEqual(result["status"], "controller-rejected")
        self.assertEqual(self._git("rev-parse", "HEAD").stdout.strip(), self.head)
        self.assertEqual(staged.read_text(), "keep staged edit\n")
        status = self._git("status", "--porcelain=v1").stdout
        self.assertIn("A  user-config.txt", status)

    def test_concurrent_main_commit_is_rejected_before_candidate_creation(self):
        (self.repo / "new-main.txt").write_text("main advanced\n")
        self._git("add", "new-main.txt")
        self._git("commit", "-qm", "concurrent main change")
        with self.assertRaisesRegex(candidate.CandidateError, "main HEAD changed"):
            candidate.prepare(self.config(), self.request())
        self.assertEqual((self.repo / "new-main.txt").read_text(), "main advanced\n")

    def test_unexpected_lock_graph_change_is_rejected(self):
        before = self.lock()
        after = json.loads(json.dumps(before))
        after["nodes"]["nixpkgs"]["locked"]["rev"] = "2" * 40
        with self.assertRaises(candidate.CandidateError):
            candidate.validate_lock_change(before, after, {"nixpkgs-updates-fast": {
                "revision": "2" * 40}})

    def test_stable_cli_tag_filter_excludes_drafts_prereleases_and_noncanonical_tags(self):
        releases = [
            {"draft": False, "prerelease": False, "tag_name": "rust-v1.2.3", "published_at": "2026-01-01T00:00:00Z"},
            {"draft": False, "prerelease": True, "tag_name": "rust-v9.0.0", "published_at": "2026-02-01T00:00:00Z"},
            {"draft": False, "prerelease": False, "tag_name": "rust-v2.0.0-rc1", "published_at": "2026-03-01T00:00:00Z"},
        ]
        self.assertEqual(candidate.stable_cli_release(releases)["tag_name"], "rust-v1.2.3")


if __name__ == "__main__":
    unittest.main()
