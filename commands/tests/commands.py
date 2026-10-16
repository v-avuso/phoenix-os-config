#!/usr/bin/env python3
"""Exercise command contracts without rebuilding, elevating, or ending a session."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Commands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phoenix-command-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.repo = self.base / "checkout with spaces"
        self.repo.mkdir()
        (self.repo / "flake.nix").write_text("{}\n")
        self.record = self.base / "record.json"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "PHOENIX_REPO_ROOT": str(self.repo),
            "PHOENIX_TARGET": "metal",
            "TMPDIR": str(self.base),
            "COMMAND_RECORD": str(self.record),
            "XDG_CURRENT_DESKTOP": "",
            "XDG_SESSION_DESKTOP": "",
            "HYPRLAND_INSTANCE_SIGNATURE": "",
        }
        for name in ("nixos-rebuild", "hyprctl", "qdbus", "hyprshutdown"):
            executable = self.bin / name
            executable.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['COMMAND_RECORD']).write_text(json.dumps(\n"
                "    {'command': Path(sys.argv[0]).name, 'args': sys.argv[1:], 'cwd': os.getcwd()}))\n"
            )
            executable.chmod(0o755)
        selector = self.bin / "phoenix-source"
        selector.write_text((ROOT / "commands/phoenix-source").read_text().replace("#!/usr/bin/env python3", "#!" + sys.executable))
        selector.chmod(0o755)
        target = self.bin / "phoenix-target"
        target.write_text((ROOT / "commands/phoenix-target").read_text())
        target.chmod(0o755)

    def run_command(self, name, *args, env=None):
        return subprocess.run(
            ["bash", str(ROOT / "commands" / name), *args],
            env=self.env | (env or {}),
            cwd=self.base,
            capture_output=True,
            text=True,
        )

    def recorded(self):
        return json.loads(self.record.read_text())

    def test_print_is_side_effect_free_and_preserves_arguments(self):
        for action in ("build", "dry-build", "test", "switch", "boot"):
            with self.subTest(action=action):
                result = self.run_command("phoenix-rebuild", "--print", action,
                                          "--option", "example", "value with spaces")
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = ["nixos-rebuild"]
                if action in ("test", "switch", "boot"):
                    expected.append("--sudo")
                expected += [action, "--flake", f"{self.repo}#metal",
                             "--option", "example", "value with spaces"]
                self.assertEqual(shlex.split(result.stdout), expected)
                self.assertFalse(self.record.exists())
                self.assertFalse((self.base / "phoenix-rebuild").exists())

    def test_build_and_dry_build_are_unprivileged(self):
        for action in ("build", "dry-build"):
            with self.subTest(action=action):
                result = self.run_command("phoenix-rebuild", action, "--no-write-lock-file")
                self.assertEqual(result.returncode, 0, result.stderr)
                record = self.recorded()
                self.assertEqual(record["args"], [action, "--flake", f"{self.repo}#metal",
                                                  "--no-write-lock-file"])
                self.assertEqual(record["cwd"], str(self.base / "phoenix-rebuild"))

    def test_activation_only_adds_sudo_to_underlying_rebuild(self):
        for action in ("test", "switch", "boot"):
            with self.subTest(action=action):
                result = self.run_command("phoenix-rebuild", action, env={"PHOENIX_TARGET": "vm"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.recorded()["args"],
                                 ["--sudo", action, "--flake", f"{self.repo}#vm"])
                self.assertEqual(self.recorded()["cwd"], str(self.base))

    def test_human_activation_keeps_terminal_rebuild_despite_helper_environment(self):
        other = self.make_worktree()
        for action in ("test", "switch", "boot"):
            result = self.run_command("phoenix-rebuild", action, "--branch", "feature",
                                      "--reason", "Optional human context", "--option", "example", "value",
                                      env={"phoenix_deployment_helper":"/missing/helper"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.recorded()["args"], ["--sudo", action, "--flake", f"{other}#metal", "--option", "example", "value"])

    def test_invalid_action_target_and_missing_checkout_stop_before_execution(self):
        cases = [("delete", {}, 2),
                 ("build", {"PHOENIX_TARGET": "unknown"}, 2),
                 ("build", {"PHOENIX_REPO_ROOT": "/nonexistent/phoenix-test"}, 127)]
        for action, env, status in cases:
            with self.subTest(action=action, env=env):
                result = self.run_command("phoenix-rebuild", action, env=env)
                self.assertEqual(result.returncode, status)
                self.assertFalse(self.record.exists())

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def make_worktree(self, destination=None):
        self.git("init", "-b", "main")
        self.git("add", "flake.nix")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-m", "fixture")
        other = destination or self.base / "other worktree"
        other.parent.mkdir(parents=True, exist_ok=True)
        self.git("worktree", "add", "-b", "feature", str(other))
        (other / "flake.nix").write_text("{ dirty = true; }\n")
        return other

    def test_narrow_managed_worktree_namespace_keeps_profile_sibling_private(self):
        bwrap = shutil.which("bwrap")
        if not bwrap: self.skipTest("Bubblewrap unavailable; namespace acceptance pending")
        home = self.base / "home"
        managed = home / ".codex/worktrees"
        other = self.make_worktree(managed / "task/repo")
        canary = home / ".codex/auth-canary"
        canary.write_text("synthetic-private-profile")
        git = str(Path(shutil.which("git")).resolve())
        code = """import os,subprocess
from pathlib import Path
repo,other,canary,git=__import__('sys').argv[1:]
assert str(Path.cwd())==other
assert not Path(canary).exists()
common=subprocess.check_output([git,'rev-parse','--git-common-dir'],text=True).strip()
assert Path(common).resolve()==Path(repo)/'.git'
Path('flake.nix').write_text('namespace dirty content')
assert 'flake.nix' in subprocess.check_output([git,'status','--porcelain'],text=True)
print('cwd/common-metadata/edit/profile-isolation passed')
"""
        command=[bwrap,'--unshare-user','--unshare-pid','--die-with-parent',
                 '--ro-bind','/nix/store','/nix/store','--proc','/proc','--dev','/dev',
                 '--tmpfs','/tmp','--bind',str(self.repo),str(self.repo),
                 '--bind',str(managed),str(managed),'--setenv','HOME',str(home),
                 '--setenv','GIT_CONFIG_GLOBAL','/dev/null','--setenv','GIT_CONFIG_SYSTEM','/dev/null',
                 '--chdir',str(other),sys.executable,'-I','-c',code,str(self.repo),str(other),str(canary),git]
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        if result.returncode and any(message in result.stderr for message in (
                'No permissions to create a new namespace','Creating new namespace failed: Operation not permitted')):
            self.skipTest('User namespace unavailable; no privileged fallback')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((other/'flake.nix').read_text(),'namespace dirty content')
        self.assertEqual((self.repo/'flake.nix').read_text(),'{}\n')
        self.assertEqual(canary.read_text(),'synthetic-private-profile')

    def test_explicit_sources_include_dirty_worktree_without_checkout_switch(self):
        other = self.make_worktree()
        for selector in (("--branch", "feature"), ("--worktree", str(other))):
            for action in ("build", "dry-build", "test", "switch", "boot"):
                result = self.run_command("phoenix-rebuild", action, "--print", *selector,
                                          "--option", "example", "value with spaces",
                                          env={"PHOENIX_TARGET": "vm"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"{other}#vm", shlex.split(result.stdout))
                self.assertEqual(shlex.split(result.stdout)[-3:],
                                 ["--option", "example", "value with spaces"])
        self.assertEqual(self.git("branch", "--show-current").strip(), "main")
        self.assertIn("dirty", (other / "flake.nix").read_text())
        self.assertFalse(self.record.exists())

    def test_invalid_source_selectors_fail_before_execution(self):
        self.make_worktree()
        self.git("branch", "unmounted")
        for args in (("--branch", "unknown"), ("--branch", "unmounted"),
                     ("--worktree", str(self.base)), ("--branch",),
                     ("--branch", "feature", "--worktree", str(self.repo))):
            result = self.run_command("phoenix-rebuild", "build", *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.record.exists())

    def test_ambiguous_branch_and_forwarded_selector_value(self):
        other = self.make_worktree()
        duplicate = self.base / "duplicate"
        self.git("worktree", "add", "--force", str(duplicate), "feature")
        result = self.run_command("phoenix-rebuild", "--branch", "feature", "--print", "build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambiguous", result.stderr)
        result = self.run_command("phoenix-rebuild", "--worktree", str(other), "--print", "build",
                                  "--option", "example", "--branch")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(shlex.split(result.stdout)[-3:], ["--option", "example", "--branch"])

    def test_target_detection_and_override_precedence(self):
        detector = self.bin / "systemd-detect-virt"
        for vm, override, expected in ((True, "", "vm"), (False, "", "metal"),
                                       (True, "metal", "metal"), (False, "vm", "vm")):
            with self.subTest(vm=vm, override=override):
                detector.write_text(f"#!/bin/sh\nexit {0 if vm else 1}\n")
                detector.chmod(0o755)
                result = self.run_command("phoenix-target", "--info",
                                          env={"PHOENIX_TARGET": override})
                self.assertEqual(result.returncode, 0, result.stderr)
                source = "env:PHOENIX_TARGET" if override else (
                    "systemd-detect-virt" if vm else "fallback")
                self.assertEqual(result.stdout, f"target={expected} source={source}\n")

    def test_hyprland_logout_dispatches_graceful_shutdown(self):
        result = self.run_command("phoenix-logout", env={"HYPRLAND_INSTANCE_SIGNATURE": "fixture"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["command"], "hyprctl")
        self.assertEqual(self.recorded()["args"],
                         ["dispatch", f"hl.dsp.exec_cmd('{self.bin}/hyprshutdown --vt 1')"])

    def test_plasma_logout_keeps_dbus_path(self):
        result = self.run_command("phoenix-logout", env={"XDG_CURRENT_DESKTOP": "KDE"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["command"], "qdbus")
        self.assertEqual(self.recorded()["args"], ["org.kde.Shutdown", "/Shutdown", "logout"])

    def test_unsupported_logout_does_not_execute(self):
        result = self.run_command("phoenix-logout")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.record.exists())


if __name__ == "__main__":
    unittest.main()
