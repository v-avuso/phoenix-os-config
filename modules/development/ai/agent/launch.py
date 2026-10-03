"""Trusted host launcher. None of its state/control sockets enters the sandbox."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main(config, args):
    app_server = args[:1] == ["app-server"]
    state = Path(config["state"])
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
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
        if login_requested:
            print("One-time Codex sandbox sign-in; Native Codex keeps its separate login.", file=sys.stderr)
            profiles = run(cli + ["provider", "profile", "list", "--output", "json"])
            if not any(item["id"] == "codex" for item in json.loads(profiles.stdout)):
                run(cli + ["provider", "profile", "import", "--file", config["profile"]])
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
            if login_requested:
                return 0

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
                       "--", "/bin/phoenix-sandbox-init", "/bin/sleep", "infinity"])
        else:
            # start is idempotent for a Ready instance; fails closed otherwise.
            run(cli + ["sandbox", "start", name])
        instance_marker.write_text(name)
        fcntl.flock(lock, fcntl.LOCK_UN)

    workdir = str(Path.cwd().resolve())
    if not any(Path(workdir).is_relative_to(Path(path)) for path in config["workspaces"]):
        workdir = config["default_workdir"]
    execution = cli + ["sandbox", "exec", "--name", name, "--no-login-shell"]
    if app_server:
        execution += ["--no-tty"]
    execution += ["--workdir", workdir, "--"]
    if args[:1] == ["--phoenix-exec"]:
        if not args[1:]:
            raise SystemExit("expected sandbox command")
        command = args[1:]
    else:
        # The TUI daemon flag does not belong to the app-server subcommand.
        command = ["/bin/phoenix-sandbox-init", "/bin/codex"]
        if not app_server:
            command += ["--no-daemon"]
        command += args
    os.execve(config["openshell"], execution + command, env)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        config = json.load(stream)
    raise SystemExit(main(config, sys.argv[2:]))
