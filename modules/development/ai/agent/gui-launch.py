"""Validate declared paths and launch the upstream Nix-Bwrapper package."""
import json
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
    subprocess.run([config["systemctl"], "--user", "start", "phoenix-agent-gui.socket",
                    "phoenix-agent-gui-http.socket"], env=env, check=True)
    return subprocess.call([config["wrapper"], *args], cwd=config["workdir"], env=env)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        try:
            raise SystemExit(main(json.load(stream), sys.argv[2:]))
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(str(error)) from None
