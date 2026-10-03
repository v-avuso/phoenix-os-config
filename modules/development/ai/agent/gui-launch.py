"""Private-home graphical sandbox with a fixed OpenShell app-server bridge."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def command(config, env, profile, proxy):
    home = config["home"]
    runtime = env["XDG_RUNTIME_DIR"]
    wayland = env.get("WAYLAND_DISPLAY", "wayland-1")
    if "/" in wayland:
        raise ValueError("Expected a local Wayland socket name")
    args = [config["bwrap"], "--die-with-parent", "--new-session", "--unshare-user",
            "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--cap-drop", "ALL",
            "--ro-bind", "/nix/store", "/nix/store", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", runtime, "--bind", str(profile / "home"), home,
            "--ro-bind", runtime + "/phoenix-agent-gui.sock", runtime + "/phoenix-agent-gui.sock",
            "--ro-bind", runtime + "/" + wayland, runtime + "/" + wayland,
            "--bind", str(proxy), runtime + "/bus", "--ro-bind", str(profile / "flatpak-info"), "/.flatpak-info"]
    for path in config["workspaces"]:
        if not Path(path).is_dir() or str(Path(path).resolve()) != path:
            raise ValueError("Missing or aliased declared workspace: " + path)
        args += ["--bind", path, path]
    # NixOS /etc/ssl contains symlinks through /etc/static. Mount the
    # immutable CA bundle directly rather than exposing that whole tree.
    for destination in ["/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/certs/ca-bundle.crt"]:
        args += ["--ro-bind", config["ca_file"], destination]
    for path in ["/etc/fonts", "/etc/resolv.conf", "/etc/hosts", "/etc/passwd",
                 "/etc/group", "/etc/nsswitch.conf", "/etc/os-release", "/etc/NIXOS", "/run/opengl-driver"]:
        if Path(path).exists():
            args += ["--ro-bind", path, path]
    if Path("/dev/dri").exists():
        args += ["--dev-bind", "/dev/dri", "/dev/dri"]
    # Mount only documents already granted to this app, never the user's whole
    # document portal. The proxy provides interactive portal access.
    documents = Path(runtime) / "doc/by-app/io.phoenix.Codex"
    if documents.is_dir():
        args += ["--bind", str(documents), runtime + "/doc"]
    args += ["--clearenv"]
    # A plain command override makes the pinned desktop skip its absolute-path
    # existence check and bundled-CLI fallback. Controlled PATH resolves only
    # our bridge; a missing bridge fails to spawn instead of launching Native.
    values = {"HOME": home, "USER": config["user"], "PATH": str(Path(config["client"]).parent) + ":" + config["path"],
              "XDG_RUNTIME_DIR": runtime, "WAYLAND_DISPLAY": wayland,
              "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
              "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + runtime + "/bus",
              "XDG_CONFIG_HOME": home + "/.config", "XDG_STATE_HOME": home + "/.local/state",
              "XDG_CACHE_HOME": home + "/.cache", "XDG_DATA_HOME": home + "/.local/share",
              "CODEX_HOME": home + "/.codex", "CODEX_ELECTRON_USER_DATA_PATH": home + "/.config/codex-sandboxed",
              "CODEX_CLI_PATH": Path(config["client"]).name, "CODEX_APP_SERVER_FORCE_CLI": "1",
              "CODEX_LINUX_APP_ID": "codex-desktop-sandboxed",
              "CODEX_LINUX_APP_DISPLAY_NAME": "ChatGPT Community (Sandboxed)",
              "CODEX_LINUX_DISABLE_USAGE_REPORTING": "1", "NIXOS_OZONE_WL": "1",
              "CODEX_OZONE_PLATFORM": "wayland", "CHROME_DESKTOP": "codex-desktop-sandboxed.desktop"}
    for key in ["LANG", "LC_ALL", "XDG_CURRENT_DESKTOP"]:
        if env.get(key):
            values[key] = env[key]
    for key, value in values.items():
        args += ["--setenv", key, value]
    return args + ["--chdir", config["workdir"], config["desktop"]]


def main(config, args):
    env = dict(os.environ)
    if not env.get("XDG_RUNTIME_DIR") or not env.get("WAYLAND_DISPLAY"):
        raise SystemExit("Sandbox GUI requires a Wayland session; Native launch remains available.")
    subprocess.run([config["systemctl"], "--user", "start", "phoenix-agent-gui.socket"], check=True)
    profile = Path(config["profile"])
    (profile / "home").mkdir(parents=True, mode=0o700, exist_ok=True)
    if profile.resolve() != profile or (profile / "home").resolve() != profile / "home":
        raise SystemExit("Sandbox GUI profile must not be a symlink or an aliased directory")
    profile.chmod(0o700)
    if (profile / "flatpak-info").is_symlink():
        raise SystemExit("Sandbox GUI portal identity must not be a symlink")
    (profile / "flatpak-info").write_text("[Application]\nname=io.phoenix.Codex\n[Context]\nshared=network;\nsockets=wayland;\n")
    with tempfile.TemporaryDirectory(prefix="phoenix-gui-", dir=env["XDG_RUNTIME_DIR"]) as directory:
        proxy = Path(directory) / "bus"
        # Portals identify the bus peer (the proxy), so its namespace must
        # carry the same Flatpak identity as the GUI; a host-side proxy with
        # only the GUI shim would be misidentified as an unrestricted app.
        runtime = env["XDG_RUNTIME_DIR"]
        bus = runtime + "/bus"
        if not Path(bus).is_socket():
            raise SystemExit("Sandbox GUI requires the standard user-session bus socket")
        process = subprocess.Popen([config["bwrap"], "--die-with-parent", "--unshare-user", "--unshare-pid",
            "--unshare-ipc", "--unshare-uts", "--cap-drop", "ALL",
            "--ro-bind", "/nix/store", "/nix/store", "--proc", "/proc", "--dev", "/dev",
            "--ro-bind", bus, bus, "--bind", directory, directory,
            "--ro-bind", str(profile / "flatpak-info"), "/.flatpak-info",
            "--", config["proxy"], "unix:path=" + bus, str(proxy),
            "--filter", "--talk=org.freedesktop.portal.*", "--own=io.phoenix.Codex.*"])
        try:
            # The proxy creates its listening socket after connecting upstream.
            # Keep readiness bounded and fail before launching the GUI.
            deadline = time.monotonic() + 10
            while not proxy.is_socket():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise SystemExit("Sandbox desktop portal proxy did not become ready")
                time.sleep(0.05)
            return subprocess.call(command(config, env, profile, proxy) + args)
        finally:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    with open(sys.argv[1]) as stream:
        raise SystemExit(main(json.load(stream), sys.argv[2:]))
