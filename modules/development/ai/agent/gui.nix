{
  config,
  lib,
  pkgs,
  inputs,
  user,
  codexCliPackage,
  phoenixAgentLauncherConfig,
  ...
}:
let
  cfg = config.phoenix.agent;
  python = "${pkgs.python3}/bin/python3";
  runtime = "/run/user/${toString config.users.users.${user.name}.uid}";
  profile = "${user.homeDirectory}/.local/state/phoenix-agent-gui";
  toolPath = lib.makeBinPath [
    pkgs.bash
    pkgs.coreutils
    pkgs.python3
  ];
  upstreamDesktop =
    inputs.codex-desktop-sandbox.packages.${pkgs.stdenv.hostPlatform.system}.codex-desktop;
  # Only this immutable sandbox copy mediates desktop backend fetches. Neither
  # the native app nor its private account/profile is patched or mounted.
  desktop = upstreamDesktop.overrideAttrs (old: {
    nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.asar ];
    postInstall = (old.postInstall or "") + ''
      asar extract "$out/opt/codex-desktop/resources/app.asar" phoenix-app
      bootstrap=phoenix-app/.vite/build/early-bootstrap.js
      test -f "$bootstrap"
      { printf '%s\n' 'require(${builtins.toJSON (toString ./gui-http-hook.cjs)});'; cat "$bootstrap"; } > phoenix-bootstrap.js
      mv phoenix-bootstrap.js "$bootstrap"
      # A failed tray registration and hidden service windows can retain the
      # private profile after its last primary window closes. Reuse upstream
      # confirmation, bounds persistence and normal quit cleanup. Remove this
      # adapter when upstream close/reopen works under the same filtered bus.
      ${python} -I ${./gui-lifecycle.py} phoenix-app
      # Electron native modules must retain their original unpacked layout.
      asar pack phoenix-app "$out/opt/codex-desktop/resources/app.asar" --unpack '*.node'
    '';
  });
  manifest = pkgs.fetchurl {
    url = "https://raw.githubusercontent.com/kk-daniel/chatgpt-desktop-flatpak/521efae965529d2bda3e7d59eaa83173dc89357d/com.openai.ChatGPT/com.openai.ChatGPT.yaml";
    hash = "sha256-ZdMLF8g0RqVsKORHQ/z0tlFjWd3H6rotAfchOjsW/rc=";
  };
  client = pkgs.writeShellScriptBin "phoenix-gui-codex" ''
    exec ${python} -I ${./gui-client.py} ${runtime}/phoenix-agent-gui.sock ${lib.removePrefix "codex-" codexCliPackage.name} "$@"
  '';
  relayConfig = pkgs.writeText "phoenix-agent-gui-relay.json" (
    builtins.toJSON {
      inherit python;
      launcher = toString ./launch.py;
      launcher_config = toString phoenixAgentLauncherConfig;
      home = user.homeDirectory;
      workdir = user.repoDirectory;
      path = toolPath;
    }
  );
  entry = pkgs.writeShellScript "phoenix-sandbox-desktop" ''
    cd ${lib.escapeShellArg user.repoDirectory}
    exec ${desktop}/bin/codex-desktop "$@"
  '';
  bwrapper = inputs.nix-bwrapper.lib.mkNixBwrapper pkgs;
  wrapperModule = {
    imports = [ bwrapper.bwrapperPresets.desktop ];
    app = {
      package = desktop;
      id = lib.mkForce "io.phoenix.Codex";
      bwrapPath = "phoenix-codex";
      runScript = toString entry;
      renameDesktopFile = false;
      overwriteExec = false;
      addPkgs = [
        client
        pkgs.python3
        pkgs.bash
        pkgs.coreutils
      ];
      env = {
        HOME = user.homeDirectory;
        USER = user.name;
        PATH = "${client}/bin:${toolPath}";
        XDG_RUNTIME_DIR = runtime;
        XDG_CONFIG_HOME = "$HOME/.config";
        XDG_STATE_HOME = "$HOME/.local/state";
        XDG_CACHE_HOME = "$HOME/.cache";
        XDG_DATA_HOME = "$HOME/.local/share";
        CODEX_HOME = "$HOME/.codex";
        CODEX_ELECTRON_USER_DATA_PATH = "$HOME/.config/codex-sandboxed";
        # A basename prevents the pinned GUI's absolute-path fallback to its
        # bundled unrestricted CLI; controlled PATH resolves only the bridge.
        CODEX_CLI_PATH = "phoenix-gui-codex";
        CODEX_APP_SERVER_FORCE_CLI = "1";
        PHOENIX_GUI_HTTP_SOCKET = "${runtime}/phoenix-agent-gui-http.sock";
        CODEX_LINUX_APP_ID = "codex-desktop-sandboxed";
        CODEX_LINUX_APP_DISPLAY_NAME = "ChatGPT Community (Sandboxed)";
        CODEX_LINUX_DISABLE_USAGE_REPORTING = "1";
        NIXOS_OZONE_WL = "1";
        CODEX_OZONE_PLATFORM = "wayland";
        CHROME_DESKTOP = "codex-desktop-sandboxed.desktop";
        SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        XCURSOR_PATH = lib.mkForce "/usr/share/icons";
        LANG = "$LANG";
        XDG_CURRENT_DESKTOP = "$XDG_CURRENT_DESKTOP";
      };
    };
    flatpak.manifestFile = manifest;
    sockets.x11 = false;
    fhsenv = {
      performDesktopPostInstall = false;
      opts = {
        unshareUser = true;
        unshareUts = true;
        unshareCgroup = true;
        unshareIpc = lib.mkForce true;
        allowNestedUserNamespaces = true;
      };
      bwrap.baseArgs = lib.mkBefore [ "--clearenv" ];
      # The upstream FHS layer exposes host /etc and /dev by default. Mask
      # those broad mounts, then admit public runtime files and GPU devices.
      bwrap.additionalArgs = lib.mkAfter [
        "--tmpfs /.host-etc"
        "--dir /.host-etc/fonts"
        "--dev /dev"
        "--tmpfs /tmp"
        "--cap-drop ALL"
        "--ro-bind-try /etc/fonts/fonts.conf /.host-etc/fonts/fonts.conf"
        "--ro-bind-try /etc/fonts/conf.d /.host-etc/fonts/conf.d"
        "--ro-bind-try /etc/resolv.conf /.host-etc/resolv.conf"
        "--ro-bind-try /etc/hosts /.host-etc/hosts"
        "--ro-bind-try /etc/passwd /.host-etc/passwd"
        "--ro-bind-try /etc/group /.host-etc/group"
        "--ro-bind-try /etc/nsswitch.conf /.host-etc/nsswitch.conf"
        "--ro-bind-try /etc/os-release /.host-etc/os-release"
        "--dev-bind-try /dev/dri /dev/dri"
        "--chdir ${lib.escapeShellArg user.repoDirectory}"
      ];
    };
    mounts = {
      privateTmp = false;
      # Preserve the existing whole private home, including GUI state. Manifest
      # persistence must never mount the native ~/.codex or GTK profiles.
      sandbox = lib.mkForce [ ];
      read = lib.mkForce [
        "/sys"
        "${runtime}/phoenix-agent-gui.sock"
        "${runtime}/phoenix-agent-gui-http.sock"
      ];
      readWrite = lib.mkForce (
        [
          {
            from = "${profile}/home";
            to = user.homeDirectory;
          }
        ]
        ++ cfg.workspaces
      );
    };
    dbus.system.talks = lib.mkForce [ ];
  };
  wrapped = bwrapper.mkBwrapper wrapperModule;
  profileSeedConfig = pkgs.writeText "phoenix-agent-gui-profile.json" (builtins.toJSON {
    source = "${user.homeDirectory}/.codex/.codex-global-state.json";
    destination = "${profile}/home/.codex/.codex-global-state.json";
    marker = "${profile}/preferences-seeded-v1";
    launcherConfig = toString phoenixAgentLauncherConfig;
    workspaces = cfg.workspaces;
  });
  guiConfig = pkgs.writeText "phoenix-agent-gui.json" (
    builtins.toJSON {
      inherit profile;
      profileSeed = [ python "-I" (toString ./gui-profile.py) (toString profileSeedConfig) ];
      busctl = "${pkgs.systemd}/bin/busctl";
      proxyExecutable = "${pkgs.xdg-dbus-proxy}/bin/xdg-dbus-proxy";
      proxySocket = "${runtime}/app/io.phoenix.Codex/bus";
      wrapper = "${wrapped}/bin/${desktop.pname}";
      home = user.homeDirectory;
      workspaces = cfg.workspaces;
      workdir = user.repoDirectory;
      systemctl = "${pkgs.systemd}/bin/systemctl";
      path = toolPath;
    }
  );
  launcher = pkgs.writeShellScriptBin "codex-desktop-sandboxed" ''
    exec ${python} -I ${./gui-launch.py} ${guiConfig} "$@"
  '';
  socket = description: name: {
    Unit.Description = description;
    Socket = {
      ListenStream = "%t/${name}.sock";
      SocketMode = "0600";
      Accept = true;
      MaxConnections = 8;
      RemoveOnStop = true;
    };
  };
  service = description: script: {
    Unit.Description = description;
    Service = {
      ExecStart = "${python} -I ${script} ${relayConfig}";
      StandardInput = "socket";
      StandardOutput = "inherit";
      StandardError = "journal";
      UMask = "0077";
      KillMode = "control-group";
      TimeoutStopSec = "10s";
    };
  };
in
{
  environment.systemPackages = [ launcher ];
  system.build.phoenixAgentGui = launcher;
  system.build.phoenixAgentGuiWrapper = wrapped;
  home-manager.users.${user.name} = {
    systemd.user.sockets.phoenix-agent-gui = socket "Fixed sandbox app-server relay for ChatGPT Community" "phoenix-agent-gui";
    systemd.user.services."phoenix-agent-gui@" =
      service "OpenShell app-server stdio relay" ./gui-relay.py;
    systemd.user.sockets.phoenix-agent-gui-http = socket "Fixed sandbox desktop HTTP relay" "phoenix-agent-gui-http";
    systemd.user.services."phoenix-agent-gui-http@" =
      service "OpenShell desktop backend HTTP relay" ./gui-http-relay.py;
    xdg.desktopEntries.codex-desktop-sandboxed = {
      name = "ChatGPT Community (Sandboxed)";
      comment = "Private GUI state, OpenShell agents and independently reviewed deployment";
      exec = "${launcher}/bin/codex-desktop-sandboxed %u";
      icon = "codex-desktop";
      terminal = false;
      type = "Application";
      categories = [ "Development" ];
      startupNotify = true;
      settings = {
        Keywords = "chat;codex;openai;ai;coding;sandbox;";
        StartupWMClass = "codex-desktop-sandboxed";
      };
    };
  };
}
