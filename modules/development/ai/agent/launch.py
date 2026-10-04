"""Trusted host launcher. None of its state/control sockets enters the sandbox."""
import fcntl
import ctypes
import hashlib
import json
import os
import re
import shlex
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


def locked_transport(command, env, lock):
    """Hold the host lifecycle lock; transport dies if the relay kills us."""
    parent = os.getpid()

    def attach_to_parent():
        # Linux PR_SET_PDEATHSIG needs no privilege. Close the fork/parent-exit
        # race before executing SSH, which may close inherited lock descriptors.
        if ctypes.CDLL(None).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
            os._exit(126)
        if os.getppid() != parent:
            os.kill(os.getpid(), signal.SIGTERM)

    child = subprocess.Popen(command, env=env, preexec_fn=attach_to_parent)
    previous = signal.signal(signal.SIGTERM, lambda *_: child.terminate())
    try:
        return child.wait()
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        signal.signal(signal.SIGTERM, previous)
        os.close(lock)


def main(config, args):
    gui_http = args == ["--phoenix-gui-http"]
    app_server = args[:1] == ["app-server"] or gui_http
    state = Path(config["state"])
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    state.chmod(0o700)
    env = dict(os.environ)
    # Ignore inherited OpenShell endpoint/policy/provider overrides. All
    # effective control inputs are the reviewed immutable launcher config.
    for key in list(env):
        if key.startswith("OPENSHELL_"):
            del env[key]
    env["OPENSHELL_GATEWAY"] = "openshell"
    cli = [config["openshell"], "--color=never"]

    def run(command, *, capture=True, extra_env=None, check=True, timeout=120):
        try:
            result = subprocess.run(command, env=env | (extra_env or {}),
                                    stdout=subprocess.PIPE if capture else sys.stderr,
                                    stderr=subprocess.PIPE if capture else sys.stderr,
                                    timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            raise SystemExit("Phoenix sandbox setup unavailable or timed out; inspect the gateway journal.") from None
        if check and result.returncode:
            # Credential-bearing operations only print a generic failure;
            # never echo their environment or potentially reflective output.
            raise SystemExit("Phoenix sandbox setup failed (" + command[1] + "). "
                             "Inspect the gateway journal using Native Codex.")
        return result

    history = {"active": False}
    history_lock = None
    if config.get("historyLock"):
        history_lock = os.open(config["historyLock"], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(history_lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(history_lock)
            raise SystemExit("Cold history handoff is in progress; retry after it completes.") from None
    if config.get("historyCommand"):
        selected = run(config["historyCommand"], check=False)
        if selected.returncode:
            raise SystemExit("Phoenix history readiness failed; repair the cold handoff through Native administration before launching.")
        history = json.loads(selected.stdout)
        if history.get("active"):
            config = config | {"policy": config["sharedPolicy"], "mounts": config["sharedMounts"]}
            if any(value.split("=", 1)[0].strip().split(".")[-1] == "sqlite_home"
                   and index and args[index - 1] in ("-c", "--config")
                   or value.startswith("--config=") and value.removeprefix("--config=").split("=", 1)[0].strip().split(".")[-1] == "sqlite_home"
                   for index, value in enumerate(args)):
                raise SystemExit("Shared history does not accept sqlite_home overrides.")

    with open(state / "launch.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run([config["systemctl"], "--user", "start", "phoenix-openshell-gateway.service"])
        # First registration follows upstream's supported local mTLS path. Do not
        # mistake a transient gateway failure for a missing registration or retry
        # blindly; errors remain actionable in the user-service journal.
        registrations = run(cli + ["gateway", "list", "--output", "json"])
        if not any(item["name"] == "openshell" for item in json.loads(registrations.stdout)):
            run(cli + ["gateway", "add", "--local", "--name", "openshell", "https://127.0.0.1:17670"])
        run(cli + ["status"])

        for workspace in config["workspaces"]:
            path = Path(workspace)
            if not path.is_dir() or str(path.resolve()) != workspace:
                raise SystemExit("Missing or aliased declared workspace: " + workspace)
        if not Path("/run/phoenix-admin/socket").is_socket():
            raise SystemExit("Phoenix diagnostic socket is unavailable; Native Codex remains usable.")

        # Pinned provider get has no --output flag. Query names instead, and
        # distinguish lookup failure from an absent login before any OAuth flow.
        providers = run(cli + ["provider", "list", "--names"])
        provider_exists = "phoenix-codex" in providers.stdout.decode().splitlines()
        login_requested = args == ["--phoenix-login"]
        if not provider_exists and not login_requested:
            raise SystemExit("Sandbox login is required; run codex-sandbox-login explicitly.")

        # Provider definitions are a separate control-plane resource from saved
        # credentials. Upstream import is create-only; export+versioned update
        # changes a retained provider's policy without deleting it or signing in.
        # The reviewed store path is the revision, not a worker-supplied file.
        profile_marker = state / "profile.path"
        if not profile_marker.exists() or profile_marker.read_text() != config["profile"]:
            profiles = run(cli + ["provider", "profile", "list", "--output", "json"])
            if any(item["id"] == "codex" for item in json.loads(profiles.stdout)):
                exported = run(cli + ["provider", "profile", "export", "codex", "--output", "json"])
                version = json.loads(exported.stdout).get("resource_version")
                if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
                    raise SystemExit("Saved provider profile has no update version; retained authentication was preserved.")
                declaration = Path(config["profile"]).read_text()
                if re.search(r"^resource_version\s*:", declaration, re.MULTILINE):
                    raise SystemExit("Declared provider profile must not pin mutable resource_version.")
                with tempfile.NamedTemporaryFile(mode="w", prefix="profile-", suffix=".yaml", dir=state) as update:
                    update.write("resource_version: " + str(version) + "\n" + declaration)
                    update.flush()
                    run(cli + ["provider", "profile", "update", "codex", "--file", update.name])
            else:
                run(cli + ["provider", "profile", "import", "--file", config["profile"]])
            profile_marker.write_text(config["profile"])
            profile_marker.chmod(0o600)

        if login_requested and provider_exists:
            try:
                uuid.UUID(json.loads((state / "account-id.json").read_text()))
            except (OSError, ValueError, TypeError):
                raise SystemExit("Saved sandbox login exists; repair its account metadata without repeating sign-in.") from None
            print("Reusing the saved sandbox login; no browser authentication needed.", file=sys.stderr)
            return 0
        if login_requested:
            print("One-time Codex sandbox sign-in; Native Codex keeps its separate login.", file=sys.stderr)
            # A separate OAuth session avoids two refresh owners invalidating the
            # existing Native login. The temporary host login is migrated exactly
            # once to OpenShell, then removed. It is never used as a second client.
            with tempfile.TemporaryDirectory(prefix="login-", dir=state) as login_home:
                run([config["native"], "login"], capture=False, extra_env={"CODEX_HOME": login_home}, timeout=600)
                with open(Path(login_home) / "auth.json") as stream:
                    tokens = json.load(stream)["tokens"]
                required = ("access_token", "refresh_token", "account_id")
                if not all(isinstance(tokens.get(key), str) and tokens[key] for key in required):
                    raise SystemExit("Sandbox sign-in did not return the required ChatGPT credentials.")
                if provider_exists:
                    run(cli + ["provider", "delete", "phoenix-codex"])
                run(cli + ["provider", "create", "--name", "phoenix-codex", "--type", "codex",
                           "--credential", "CODEX_AUTH_ACCESS_TOKEN", "--credential", "CODEX_AUTH_ACCOUNT_ID"],
                    extra_env={"CODEX_AUTH_ACCESS_TOKEN": tokens["access_token"],
                               "CODEX_AUTH_ACCOUNT_ID": tokens["account_id"]})
                run(cli + ["provider", "refresh", "configure", "phoenix-codex",
                           "--credential-key", "CODEX_AUTH_ACCESS_TOKEN", "--strategy", "oauth2-refresh-token",
                           "--material", "client_id=app_EMoamEEZ73f0CkXaXp7hrann",
                           "--secret-material-env", "refresh_token=CODEX_AUTH_REFRESH_TOKEN"],
                    extra_env={"CODEX_AUTH_REFRESH_TOKEN": tokens["refresh_token"]})
                # Workspace discovery compares this public selector locally;
                # only bearer/refresh credentials belong behind opaque handles.
                account_file = state / "account-id.json"
                account_file.write_text(json.dumps(str(uuid.UUID(tokens["account_id"]))))
                account_file.chmod(0o600)
            if login_requested:
                return 0

        try:
            account_id = str(uuid.UUID(json.loads((state / "account-id.json").read_text())))
        except (OSError, ValueError, TypeError):
            raise SystemExit("Sandbox account selector is missing or invalid; repair saved metadata through Native Codex, without repeating sign-in.") from None

        archive = Path(config["image"])
        image_marker = state / "image.path"
        if not image_marker.exists() or image_marker.read_text() != str(archive):
            run([config["podman"], "load", "--input", str(archive)])
            image_marker.write_text(str(archive))
        # Filesystem policy is static: a new declaration gets a new sandbox. Stop
        # the previous managed instance, retaining its workspace/sessions for
        # deliberate recovery instead of silently deleting user state.
        revision = hashlib.sha256((config["image"] + config["policy"] + config["mounts"]).encode()).hexdigest()[:12]
        # OpenShell v0.1.2 limits sandbox names to 19 characters.
        name = "phx-" + revision
        instance_marker = state / "instance"
        if instance_marker.exists() and instance_marker.read_text() != name:
            run(cli + ["sandbox", "stop", instance_marker.read_text()], check=False)
        sandbox = run(cli + ["sandbox", "get", name, "--output", "json"], check=False)
        if sandbox.returncode:
            mounts = Path(config["mounts"]).read_text()
            run(cli + ["sandbox", "create", "--name", name, "--from", "localhost/phoenix-codex:0.1.2",
                       "--policy", config["policy"], "--driver-config-json", mounts,
                       "--provider", "phoenix-codex", "--no-auto-providers", "--detach", "--no-tty",
                       "--cpu", "8", "--memory", "8Gi", "--output", "json",
                       "--", "/bin/sleep", "infinity"])
        else:
            # start is idempotent for a Ready instance; fails closed otherwise.
            run(cli + ["sandbox", "start", name])
        instance_marker.write_text(name)
        fcntl.flock(lock, fcntl.LOCK_UN)

    workdir = str(Path.cwd().resolve())
    if not any(Path(workdir).is_relative_to(Path(path)) for path in config["workspaces"]):
        workdir = config["default_workdir"]
    execution = cli + ["sandbox", "exec", "--name", name, "--no-login-shell",
                       "--env", "PHOENIX_CODEX_ACCOUNT_ID=" + account_id]
    history_env = (["CODEX_HOME=" + history["codexHome"], "CODEX_SQLITE_HOME=" + history["sqliteHome"]]
                   if history["active"] else [])
    for assignment in history_env:
        execution += ["--env", assignment]
    if app_server:
        execution += ["--no-tty"]
    execution += ["--workdir", workdir, "--"]
    if gui_http:
        command = ["/bin/phoenix-gui-http"]
    elif args[:1] == ["--phoenix-exec"]:
        if not args[1:]:
            raise SystemExit("expected sandbox command")
        command = args[1:]
    else:
        # The TUI daemon flag does not belong to the app-server subcommand.
        command = ["/bin/phoenix-sandbox-init", "/bin/codex"]
        if not app_server:
            command += ["--no-daemon"]
        if app_server and config.get("appServerPreferences"):
            # Immutable host adapter selects only public scalar preferences.
            # Caller flags cannot choose the source or add host capabilities.
            preferences = run(config["appServerPreferences"]).stdout
            if len(preferences) > 4096:
                raise SystemExit("Selected app-server preferences exceed bounded output")
            preferences = json.loads(preferences)
            allowed = {"model", "model_reasoning_effort", "service_tier", "desktop.followUpQueueMode",
                       "desktop.conversationDetailMode", "desktop.appearanceTheme", "desktop.ambient-suggestions-enabled"}
            if not isinstance(preferences, dict) or not preferences.keys() <= allowed or any(type(v) not in (str, bool) for v in preferences.values()):
                raise SystemExit("Invalid selected app-server preferences")
            for key, value in preferences.items():
                command += ["-c", key + "=" + json.dumps(value)]
        command += args
    if app_server:
        # OpenShell 0.1.2 gRPC exec buffers nonterminal stdin until EOF;
        # an app-server needs full duplex. Use upstream's mTLS SSH proxy,
        # with no host SSH configuration, keys, agent, or terminal involved.
        proxy = shlex.join(cli + ["ssh-proxy", "--gateway-name", "openshell", "--name", name])
        remote = "cd " + shlex.quote(workdir) + " && exec " + shlex.join(
            ["/bin/env", "PHOENIX_CODEX_ACCOUNT_ID=" + account_id] + history_env + command)
        ssh = [config["ssh"], "-F", "/dev/null", "-T", "-o", "BatchMode=yes",
               "-o", "IdentityAgent=none", "-o", "IdentityFile=none", "-o", "IdentitiesOnly=yes",
               "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
               "-o", "GlobalKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
               "-o", "SetEnv=OPENSHELL_NO_LOGIN_SHELL=1",
               "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
               "-o", "ProxyCommand=" + proxy, "sandbox", remote]
        if history_lock is not None:
            # SSH may close inherited descriptors. Keep the private lifecycle
            # lock in this host parent for the full duplex transport lifetime.
            return locked_transport(ssh, env, history_lock)
        os.execve(config["ssh"], ssh, env)
    else:
        if history_lock is not None:
            return locked_transport(execution + command, env, history_lock)
        os.execve(config["openshell"], execution + command, env)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        config = json.load(stream)
    raise SystemExit(main(config, sys.argv[2:]))
