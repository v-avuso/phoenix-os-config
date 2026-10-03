#!/usr/bin/env python3
"""Host launcher protocol and fail-closed fixtures; no real gateway or login."""
import importlib.util
import json
import os
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("agent_launch", ROOT / "modules/development/ai/agent/launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


class LauncherFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {key: "/fixed/" + key for key in ("openshell", "native", "podman", "systemctl", "ssh", "image", "policy", "profile")}
        self.config.update(state=str(self.root / "state"), workspaces=[str(self.root)], default_workdir=str(self.root), mounts=str(self.root / "mounts"))
        (self.root / "mounts").write_text('{}')
        (self.root / "state").mkdir()
        (self.root / "state/account-id.json").write_text('"00000000-0000-0000-0000-000000000001"')

    @staticmethod
    def success(command, **kwargs):
        if command[1:4] == ["--color=never", "provider", "list"]:
            output = b'phoenix-codex\n'
        else:
            output = b'[{"name":"openshell"}]' if "list" in command else b'{}'
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr=b'')

    def test_app_server_keeps_stdio_and_never_falls_back_native(self):
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute, \
             mock.patch.dict(os.environ, {"OPENSHELL_GATEWAY": "attacker", "OPENSHELL_POLICY": "attacker"}):
            launch.main(self.config, ["app-server", "--listen", "stdio://"])
        executable, argv, env = execute.call_args.args
        self.assertEqual(executable, self.config["ssh"])
        self.assertIn("-T", argv)
        self.assertIn("IdentityAgent=none", argv)
        self.assertIn("SetEnv=OPENSHELL_NO_LOGIN_SHELL=1", argv)
        self.assertEqual(argv[1:3], ["-F", "/dev/null"])
        self.assertNotIn("--no-daemon", argv)
        self.assertEqual(shlex.split(argv[-1])[-5:], ["/bin/phoenix-sandbox-init", "/bin/codex", "app-server", "--listen", "stdio://"])
        self.assertEqual(env["OPENSHELL_GATEWAY"], "openshell")
        self.assertNotIn("OPENSHELL_POLICY", env)
        self.assertIn("PHOENIX_CODEX_ACCOUNT_ID=00000000-0000-0000-0000-000000000001", shlex.split(argv[-1]))
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["stdout"], subprocess.PIPE)
            self.assertEqual(call.kwargs["timeout"], 120)

    def test_missing_login_fails_before_starting_app_server(self):
        def missing(command, **kwargs):
            if command[1:4] == ["--color=never", "provider", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=missing), \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute:
            with self.assertRaisesRegex(SystemExit, "codex-sandbox-login"):
                launch.main(self.config, ["app-server"])
        execute.assert_not_called()

    def test_failed_lookup_does_not_start_another_login(self):
        def failed(command, **kwargs):
            if command[1:4] == ["--color=never", "provider", "list"]:
                return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'')
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=failed) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute:
            with self.assertRaisesRegex(SystemExit, "setup failed"):
                launch.main(self.config, [])
        self.assertFalse(any("login" in call.args[0] for call in run.call_args_list))
        execute.assert_not_called()

    def test_saved_login_command_does_not_repeat_oauth(self):
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True):
            self.assertEqual(launch.main(self.config, ["--phoenix-login"]), 0)
        self.assertFalse(any("login" in call.args[0] for call in run.call_args_list))

    def test_missing_account_selector_does_not_repeat_oauth(self):
        (self.root / "state/account-id.json").unlink()
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True):
            with self.assertRaisesRegex(SystemExit, "without repeating sign-in"):
                launch.main(self.config, ["--phoenix-login"])
        self.assertFalse(any("login" in call.args[0] for call in run.call_args_list))

    def test_setup_timeout_fails_closed_without_credential_output(self):
        with mock.patch.object(launch.subprocess, "run", side_effect=subprocess.TimeoutExpired("setup", 120, output=b'secret')), \
             mock.patch.object(launch.os, "execve") as execute:
            with self.assertRaisesRegex(SystemExit, "timed out") as failure:
                launch.main(self.config, [])
        self.assertNotIn("secret", str(failure.exception))
        execute.assert_not_called()

    def test_unavailable_broker_fails_closed(self):
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success), \
             mock.patch.object(launch.Path, "is_socket", return_value=False), \
             mock.patch.object(launch.os, "execve") as execute:
            with self.assertRaisesRegex(SystemExit, "socket is unavailable"):
                launch.main(self.config, [])
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
