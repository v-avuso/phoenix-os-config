{
  config,
  pkgs,
  inputs,
  user,
  codexCliPackage,
  phoenixAgentLauncherConfig,
  ...
}:
let
  cfg = config.phoenix.agent;
  # Reuse the pinned upstream desktop and Flatpak's namespace/portal tools.
  # No private host profiles, credentials, Podman sockets or control bus enter
  # the GUI. The separate host relay has one immutable app-server command.
  desktop = inputs.codex-desktop-linux.packages.${pkgs.stdenv.hostPlatform.system}.codex-desktop;
  python = "${pkgs.python3}/bin/python3";
  runtime = "/run/user/${toString config.users.users.${user.name}.uid}";
  toolPath = pkgs.lib.makeBinPath [
    pkgs.bash
    pkgs.coreutils
    pkgs.python3
  ];
  client = pkgs.writeShellScriptBin "phoenix-gui-codex" ''
    exec ${python} -I ${./gui-client.py} ${runtime}/phoenix-agent-gui.sock ${pkgs.lib.removePrefix "codex-" codexCliPackage.name} "$@"
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
  guiConfig = pkgs.writeText "phoenix-agent-gui.json" (
    builtins.toJSON {
      home = user.homeDirectory;
      user = user.name;
      profile = "${user.homeDirectory}/.local/state/phoenix-agent-gui";
      workdir = user.repoDirectory;
      workspaces = cfg.workspaces;
      ca_file = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      bwrap = "${pkgs.bubblewrap}/bin/bwrap";
      proxy = "${pkgs.xdg-dbus-proxy}/bin/xdg-dbus-proxy";
      systemctl = "${pkgs.systemd}/bin/systemctl";
      desktop = "${desktop}/bin/codex-desktop";
      client = "${client}/bin/phoenix-gui-codex";
      path = toolPath;
    }
  );
  launcher = pkgs.writeShellScriptBin "codex-desktop-sandboxed" ''
    exec ${python} -I ${./gui-launch.py} ${guiConfig} "$@"
  '';
in
{
  environment.systemPackages = [ launcher ];
  home-manager.users.${user.name} = {
    systemd.user.sockets.phoenix-agent-gui = {
      Unit.Description = "Fixed sandbox app-server relay for ChatGPT Community";
      Socket = {
        ListenStream = "%t/phoenix-agent-gui.sock";
        SocketMode = "0600";
        Accept = true;
        MaxConnections = 8;
        RemoveOnStop = true;
      };
    };
    systemd.user.services."phoenix-agent-gui@" = {
      Unit.Description = "OpenShell app-server stdio relay";
      Service = {
        ExecStart = "${python} -I ${./gui-relay.py} ${relayConfig}";
        StandardInput = "socket";
        StandardOutput = "inherit";
        StandardError = "journal";
        UMask = "0077";
        KillMode = "control-group";
        TimeoutStopSec = "10s";
      };
    };
    xdg.desktopEntries.codex-desktop-sandboxed = {
      name = "ChatGPT Community (Sandboxed)";
      comment = "Private GUI home and OpenShell agents; separate sign-in, declared workspaces only";
      exec = "${launcher}/bin/codex-desktop-sandboxed %u";
      icon = "codex-desktop";
      terminal = false;
      type = "Application";
      categories = [ "Development" ];
      startupNotify = true;
      settings = {
        Keywords = "codex;openai;ai;coding;sandbox;";
        StartupWMClass = "codex-desktop-sandboxed";
      };
    };
  };
}
