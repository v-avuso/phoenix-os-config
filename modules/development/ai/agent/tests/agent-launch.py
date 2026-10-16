#!/usr/bin/env python3
"""Host launcher protocol and fail-closed fixtures; no real gateway or login."""
import importlib.util
import fcntl
import multiprocessing
import pty
import json
import os
import shlex
import signal
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[5]
SPEC = importlib.util.spec_from_file_location("agent_launch", ROOT / "modules/development/ai/agent/launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)
REAL_TRANSPORT = launch.locked_transport


class LauncherFixture(unittest.TestCase):
    def setUp(self):
        # Protocol fixtures capture the final transport while closing its owned FDs.
        def transport(command, env, locks):
            try:
                return launch.os.execve(command[0], command, env)
            finally:
                for fd in locks:
                    os.close(fd)
        patched = mock.patch.object(launch, "locked_transport", side_effect=transport)
        patched.start()
        self.addCleanup(patched.stop)
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

    def test_busy_revision_refuses_before_stop_or_image_load(self):
        (self.root / "state/instance").write_text("phx-old")
        with open(self.root / "state/instance-use.lock", "a") as active:
            fcntl.flock(active, fcntl.LOCK_SH)
            with mock.patch.object(launch.subprocess, "run", side_effect=self.success) as run, \
                 mock.patch.object(launch.Path, "is_socket", return_value=True):
                with self.assertRaisesRegex(SystemExit, "replacement is busy"):
                    launch.main(self.config, ["--phoenix-exec", "/bin/true"])
        self.assertFalse(any("stop" in c.args[0] or "load" in c.args[0] for c in run.call_args_list))
        self.assertEqual((self.root / "state/instance").read_text(), "phx-old")

    def test_same_revision_joins_and_native_history_lock_is_independent(self):
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success), \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve"):
            launch.main(self.config, [])
            with open(self.root / "state/instance-use.lock", "a") as active, \
                 open(self.root / "native-history.lock", "a") as history:
                fcntl.flock(active, fcntl.LOCK_SH)
                fcntl.flock(history, fcntl.LOCK_SH)
                self.config["historyLock"] = str(self.root / "native-history.lock")
                launch.main(self.config, ["app-server"])
            # Independent Native history SH also permits a replacement.
            with open(self.root / "native-history.lock", "a") as history:
                fcntl.flock(history, fcntl.LOCK_SH)
                launch.main(self.config | {"image": "/fixed/new-image"}, [])
        with open(self.root / "state/instance-use.lock", "a") as released:
            fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_serialized_launchers_cannot_replace_between_setup_and_transport(self):
        context = multiprocessing.get_context("fork")
        setup, proceed, transported, finish = [context.Event() for _ in range(4)]
        events = context.Queue()
        def client(config, first):
            def run(command, **kwargs):
                if first and "get" in command:
                    setup.set()
                    if not proceed.wait(5): raise RuntimeError("fixture setup timeout")
                if "stop" in command: events.put("stopped")
                return self.success(command, **kwargs)
            def transport(command, env, locks):
                transported.set()
                try:
                    if not finish.wait(5): raise RuntimeError("fixture transport timeout")
                finally:
                    for fd in locks: os.close(fd)
            try:
                with mock.patch.object(launch.subprocess, "run", side_effect=run), \
                     mock.patch.object(launch.Path, "is_socket", return_value=True), \
                     mock.patch.object(launch, "locked_transport", side_effect=transport):
                    launch.main(config, ["--phoenix-exec", "/bin/true"])
                events.put("finished")
            except SystemExit as error:
                events.put(str(error))
        first = context.Process(target=client, args=(self.config, True))
        second = context.Process(target=client, args=(self.config | {"image": "/fixed/new-image"}, False))
        first.start()
        try:
            self.assertTrue(setup.wait(5))
            second.start()  # It must wait behind the first setup lock.
            proceed.set()
            self.assertTrue(transported.wait(5))
            second.join(5)
            self.assertFalse(second.is_alive())
            self.assertIn("replacement is busy", events.get(timeout=2))
            finish.set()
            first.join(5)
            self.assertEqual(events.get(timeout=2), "finished")
            self.assertEqual(first.exitcode, 0)
            with open(self.root / "state/instance-use.lock", "a") as released:
                fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            proceed.set(); finish.set()
            for process in (first, second):
                if process.pid is not None:
                    if process.is_alive(): process.kill()
                    process.join(5)

    def test_managed_worktree_cwd_reaches_contained_transport(self):
        managed = self.root / "home/.codex/worktrees"
        checkout = managed / "task/repo"
        checkout.mkdir(parents=True)
        self.config["workspaces"] = [str(managed)]
        with mock.patch.object(launch.subprocess, "run", side_effect=self.success), \
             mock.patch.object(launch.Path, "is_socket", return_value=True), \
             mock.patch.object(launch.os, "execve") as execute, \
             mock.patch.object(launch.Path, "cwd", return_value=checkout):
            launch.main(self.config, ["--phoenix-exec", "/bin/true"])
        execution = execute.call_args.args[1]
        self.assertEqual(execution[execution.index("--workdir") + 1], str(checkout))

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

    def test_ready_history_selects_shared_mounts_and_both_transport_environments(self):
        self.config.update(historyCommand=["/fixed/history"], sharedPolicy="/fixed/shared-policy", sharedMounts=str(self.root / "shared-mounts"))
        (self.root / "shared-mounts").write_text('{"shared":true}')
        def shared(command, **kwargs):
            if command == self.config["historyCommand"]:
                return subprocess.CompletedProcess(command, 0, stdout=b'{"active":true,"codexHome":"/home/v/.codex","sqliteHome":"/shared/sqlite"}', stderr=b'')
            if command[1:4] == ["--color=never", "sandbox", "get"]:
                return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'')
            return self.success(command, **kwargs)
        for args in (["app-server"], []):
            with mock.patch.object(launch.subprocess, "run", side_effect=shared) as run, \
                 mock.patch.object(launch.Path, "is_socket", return_value=True), \
                 mock.patch.object(launch.os, "execve") as execute:
                launch.main(self.config, args)
            argv = execute.call_args.args[1]
            effective = shlex.split(argv[-1]) if args else argv
            self.assertIn("CODEX_HOME=/home/v/.codex", effective)
            self.assertIn("CODEX_SQLITE_HOME=/shared/sqlite", effective)
            creation = next(call.args[0] for call in run.call_args_list if "create" in call.args[0])
            self.assertIn("/fixed/shared-policy", creation)
            self.assertIn('{"shared":true}', creation)

    def test_history_failure_precedes_gateway_or_instance_changes(self):
        self.config["historyCommand"] = ["/fixed/history"]
        with mock.patch.object(launch.subprocess, "run", return_value=subprocess.CompletedProcess(["/fixed/history"], 1, stdout=b'', stderr=b'')) as run:
            with self.assertRaises(SystemExit):
                launch.main(self.config, [])
        self.assertEqual(run.call_count, 1)

    def test_real_transport_holds_instance_lock_until_child_exit(self):
        path = self.root / "transport.lock"
        script = ("import importlib.util,os,sys; "
                  "s=importlib.util.spec_from_file_location('l',sys.argv[1]); "
                  "l=importlib.util.module_from_spec(s);s.loader.exec_module(l); "
                  "f=os.open(sys.argv[2],os.O_RDWR|os.O_CREAT,0o600); "
                  "l.fcntl.flock(f,l.fcntl.LOCK_SH); "
                  "sys.exit(l.locked_transport([sys.executable,'-c',"
                  "\"print('ready',flush=True);input()\"],dict(os.environ),(f,)))")
        process = subprocess.Popen([sys.executable, "-c", script, str(Path(launch.__file__)), str(path)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "ready")
            with open(path, "a") as contender:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
                output, errors = process.communicate("exit\n", timeout=5)
                self.assertEqual((process.returncode, output, errors), (0, "", ""))
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            if process.poll() is None:
                process.kill(); process.communicate(timeout=5)

    def test_real_transport_preserves_terminal_descriptors(self):
        master, slave = pty.openpty()
        try:
            script = ("import importlib.util,os,sys; "
                      "s=importlib.util.spec_from_file_location('l',sys.argv[1]); "
                      "l=importlib.util.module_from_spec(s);s.loader.exec_module(l); "
                      "sys.exit(l.locked_transport([sys.executable,'-c',"
                      "'import os; assert all(os.isatty(fd) for fd in (0,1,2))'],dict(os.environ),()))")
            result = subprocess.run([sys.executable, "-c", script, str(Path(launch.__file__))],
                                    stdin=slave, stdout=slave, stderr=slave, timeout=5)
            self.assertEqual(result.returncode, 0)
        finally:
            os.close(master); os.close(slave)

    def test_real_transport_forwards_signals_and_preserves_exit_status(self):
        for number in (None, signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=number):
                path = self.root / "signal.lock"
                child = ("import signal,sys; "
                         "signal.signal(signal.SIGINT,lambda *_:sys.exit(130)); "
                         "print('ready',flush=True); " + ("sys.exit(7)" if number is None else "signal.pause()"))
                script = ("import importlib.util,os,sys; "
                          "s=importlib.util.spec_from_file_location('l',sys.argv[1]); "
                          "l=importlib.util.module_from_spec(s);s.loader.exec_module(l); "
                          "f=os.open(sys.argv[2],os.O_RDWR|os.O_CREAT,0o600); "
                          "l.fcntl.flock(f,l.fcntl.LOCK_SH); "
                          "sys.exit(l.locked_transport([sys.executable,'-c',sys.argv[3]],dict(os.environ),(f,)))")
                process = subprocess.Popen([sys.executable, "-c", script, str(Path(launch.__file__)), str(path), child],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    self.assertEqual(process.stdout.readline().strip(), "ready")
                    if number is not None: process.send_signal(number)
                    output, errors = process.communicate(timeout=5)
                    self.assertEqual(process.returncode, 7 if number is None else 128 + number)
                    self.assertEqual((output, errors), ("", ""))
                    with open(path, "a") as released:
                        fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    if process.poll() is None:
                        process.kill(); process.communicate(timeout=5)

    def test_supervised_transport_dies_when_test_parent_is_killed(self):
        script = ('import importlib.util,os,sys; '
                  'spec=importlib.util.spec_from_file_location("l",sys.argv[1]); '
                  'l=importlib.util.module_from_spec(spec); spec.loader.exec_module(l); '
                  'fd=os.open(sys.argv[2],os.O_RDWR|os.O_CREAT,0o600); '
                  'l.fcntl.flock(fd,l.fcntl.LOCK_SH); '
                  'child="import signal,sys; signal.signal(signal.SIGTERM,lambda *_:(print(\\\"stopped\\\",flush=True),sys.exit(0))); print(\\\"ready\\\",flush=True); signal.pause()"; '
                  'l.locked_transport([sys.executable,"-c",child],dict(os.environ),fd)')
        process = subprocess.Popen([sys.executable, "-c", script, str(ROOT / "modules/development/ai/agent/launch.py"), str(self.root / "history.lock")],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "ready")
            process.kill()  # Only this synthetic parent; no desktop process.
            output, errors = process.communicate(timeout=5)
            self.assertIn("stopped", output)
            self.assertEqual(errors, "")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)

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
