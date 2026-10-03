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
        (self.root / "state/profile.path").write_text(self.config["profile"])

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

    def test_app_server_applies_only_selected_host_preferences(self):
        self.config["appServerPreferences"] = ["/fixed/preferences", "--worker", "/fixed/native-config"]
        def selected(command, **kwargs):
            if command == self.config["appServerPreferences"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'{"model":"gpt-6.1-sol","desktop.conversationDetailMode":"STEPS_COMMANDS"}', stderr=b'')
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=selected), \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute:
            launch.main(self.config, ["app-server"])
        remote = shlex.split(execute.call_args.args[1][-1])
        index = remote.index("/bin/codex")
        self.assertEqual(remote[index+1:], ["-c", 'model="gpt-6.1-sol"', "-c", 'desktop.conversationDetailMode="STEPS_COMMANDS"', "app-server"])
        def forbidden(command, **kwargs):
            if command == self.config["appServerPreferences"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'{"sandbox_mode":"danger-full-access"}', stderr=b'')
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=forbidden), \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute:
            with self.assertRaisesRegex(SystemExit, "Invalid selected"):
                launch.main(self.config, ["app-server"])
        execute.assert_not_called()

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

    def test_changed_profile_updates_retained_provider_with_export_version(self):
        profile = self.root / "codex-profile.yaml"
        profile.write_text('id: codex\nbinaries: [/fixed/python3.13]\n')
        self.config["profile"] = str(profile)
        updates = []
        def existing(command, **kwargs):
            if command[1:5] == ["--color=never", "provider", "profile", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'[{"id":"codex"}]', stderr=b'')
            if command[1:5] == ["--color=never", "provider", "profile", "export"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'{"resource_version":7}', stderr=b'')
            if command[1:5] == ["--color=never", "provider", "profile", "update"]:
                updates.append(Path(command[-1]).read_text())
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=existing) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True):
            self.assertEqual(launch.main(self.config, ["--phoenix-login"]), 0)
            self.assertEqual(launch.main(self.config, ["--phoenix-login"]), 0)
        self.assertEqual(updates, ['resource_version: 7\nid: codex\nbinaries: [/fixed/python3.13]\n'])
        self.assertEqual((self.root / "state/profile.path").read_text(), str(profile))
        self.assertFalse(list((self.root / "state").glob('profile-*.yaml')))
        self.assertFalse(any('login' in call.args[0] or 'delete' in call.args[0] or 'create' in call.args[0] for call in run.call_args_list))

    def test_failed_profile_update_preserves_login_and_retries_next_launch(self):
        profile = self.root / "codex-profile.yaml"
        profile.write_text('id: codex\n')
        self.config["profile"] = str(profile)
        def failing(command, **kwargs):
            if command[1:5] == ["--color=never", "provider", "profile", "list"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'[{"id":"codex"}]', stderr=b'')
            if command[1:5] == ["--color=never", "provider", "profile", "export"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'{"resource_version":7}', stderr=b'')
            if command[1:5] == ["--color=never", "provider", "profile", "update"]:
                return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'')
            return self.success(command, **kwargs)
        with mock.patch.object(launch.subprocess, "run", side_effect=failing) as run, \
             mock.patch.object(launch.Path, "is_socket", return_value=True):
            with self.assertRaisesRegex(SystemExit, "setup failed"):
                launch.main(self.config, ["--phoenix-login"])
        self.assertNotEqual((self.root / "state/profile.path").read_text(), str(profile))
        self.assertTrue((self.root / "state/account-id.json").exists())
        self.assertFalse(any('login' in call.args[0] or 'delete' in call.args[0] for call in run.call_args_list))


if __name__ == "__main__":
    unittest.main()
