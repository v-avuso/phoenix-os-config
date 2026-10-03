"""Validate declared paths and launch the upstream Nix-Bwrapper package."""
import json
import fcntl
import os
import re
from pathlib import Path
import subprocess
import sys
import time


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


def reactivate(config, env):
    """Use upstream tray activation only for this exact sandbox bus proxy."""
    if not config.get("busctl"):
        return False
    deadline = time.monotonic() + 8
    def bus(*args):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Tray activation timed out")
        result = subprocess.run([config["busctl"], "--user", "--json=short", *args],
                                env=env, capture_output=True, check=True, timeout=min(2, remaining))
        if len(result.stdout) > 65536:
            raise ValueError("Tray response exceeds bounded output")
        return json.loads(result.stdout) if result.stdout else {}
    try:
        items = bus("get-property", "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                    "org.kde.StatusNotifierWatcher", "RegisteredStatusNotifierItems")
        if items.get("type") != "as" or not isinstance(items.get("data"), list) or len(items["data"]) > 64:
            return False
        matches = set()
        for item in items["data"]:
            if not isinstance(item, str) or "/" not in item:
                continue
            service, suffix = item.split("/", 1)
            if suffix != "StatusNotifierItem" or not re.fullmatch(r":[0-9]+\.[0-9]+|org\.(?:freedesktop|kde)\.StatusNotifierItem-[0-9]+-[0-9]+", service):
                continue
            owner = bus("call", "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetNameOwner", "s", service)["data"][0]
            if not isinstance(owner, str) or not re.fullmatch(r":[0-9]+\.[0-9]+", owner):
                continue
            pid = bus("call", "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetConnectionUnixProcessID", "s", owner)["data"][0]
            if type(pid) is not int or pid <= 0:
                continue
            peer = Path("/proc") / str(pid)
            if peer.stat().st_uid != os.getuid() or (peer / "exe").resolve() != Path(config["proxyExecutable"]):
                continue
            args = (peer / "cmdline").read_bytes().split(b"\0")
            if config["proxySocket"].encode() in args and b"--filter" in args:
                matches.add(owner)
        if len(matches) != 1:
            return False
        bus("call", matches.pop(), "/StatusNotifierItem", "org.kde.StatusNotifierItem", "Activate", "ii", "0", "0")
        return True
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError):
        return False


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
            if reactivate(config, env):
                return 0
            print("Sandboxed ChatGPT is already running; use its existing window.", file=sys.stderr)
            return 0
        if config.get("profileSeed"):
            subprocess.run(config["profileSeed"], env=env, check=True)
        subprocess.run([config["systemctl"], "--user", "start", "phoenix-agent-gui.socket",
                        "phoenix-agent-gui-http.socket"], env=env, check=True)
        return subprocess.call([config["wrapper"], *args], cwd=config["workdir"], env=env)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        try:
            raise SystemExit(main(json.load(stream), sys.argv[2:]))
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(str(error)) from None
