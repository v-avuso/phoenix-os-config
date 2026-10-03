"""Validate declared paths and launch the upstream Nix-Bwrapper package."""
import json
import fcntl
import os
from pathlib import Path
import subprocess
import sys


def environment(config, env):
    runtime = env.get("XDG_RUNTIME_DIR")
    wayland = env.get("WAYLAND_DISPLAY")
    if runtime != "/run/user/" + str(os.getuid()) or not wayland or "/" in wayland:
        raise ValueError("Sandbox GUI requires the current user's local Wayland session")
    result = {"HOME": config["home"], "PATH": config["path"],
              "XDG_RUNTIME_DIR": runtime, "WAYLAND_DISPLAY": wayland,
              "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + runtime + "/bus",
              "LANG": env.get("LANG", "C.UTF-8"),
              "XDG_CURRENT_DESKTOP": env.get("XDG_CURRENT_DESKTOP", "")}
    return result


def validate(config):
    for workspace in config["workspaces"]:
        path = Path(workspace)
        if not path.is_dir() or str(path.resolve()) != workspace:
            raise ValueError("Missing or aliased declared workspace: " + workspace)
    profile = Path(config["profile"])
    # Check before creation, including an existing dangling symlink.
    if profile.resolve() != profile or (profile / "home").resolve() != profile / "home":
        raise ValueError("Sandbox GUI profile must not be an aliased directory")
    (profile / "home").mkdir(parents=True, mode=0o700, exist_ok=True)
    profile.chmod(0o700)
    (profile / "home").chmod(0o700)


def main(config, args):
    os.umask(0o077)
    env = environment(config, os.environ)
    validate(config)
    # Chromium's singleton socket lives in private /tmp, and namespace-local
    # PIDs cannot identify peers in another wrapper. Serialize on the host for
    # the wrapper's entire lifetime instead of resetting any private profile.
    fd = os.open(Path(config["profile"]) / "desktop.lock",
                 os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Sandboxed ChatGPT is already running; use its existing window.", file=sys.stderr)
            return 0
        subprocess.run([config["systemctl"], "--user", "start", "phoenix-agent-gui.socket",
                        "phoenix-agent-gui-http.socket"], env=env, check=True)
        return subprocess.call([config["wrapper"], *args], cwd=config["workdir"], env=env)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        try:
            raise SystemExit(main(json.load(stream), sys.argv[2:]))
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(str(error)) from None
