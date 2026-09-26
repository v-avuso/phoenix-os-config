{ pkgs, user, ... }:

let
  # Physical left-to-right facts, also suitable for reuse by Hyprland later.
  monitorLayout = [
    {
      connector = "DP-1";
      edid = "GSM 23450 479236 10 2020 0";
    }
    {
      connector = "HDMI-A-2";
      edid = "DEL 41607 809583187 29 2025 0";
    }
    {
      connector = "DP-2";
      edid = "GSM 23639 372162 9 2023 0";
    }
  ];

  monitorLayoutData = pkgs.writeText "phoenix-monitor-layout.json" (builtins.toJSON monitorLayout);

  monitorLayoutReflow = pkgs.writeShellScriptBin "phoenix-monitor-layout" ''
    exec ${pkgs.python3}/bin/python3 ${./monitor-layout.py} ${monitorLayoutData} ${pkgs.kdePackages.libkscreen}/bin/kscreen-doctor
  '';

  kwinMonitorLayoutScript = pkgs.runCommand "phoenix-kwin-monitor-layout" { } ''
    install -D ${./kwin-script/metadata.json} $out/share/kwin/scripts/phoenix-monitor-layout/metadata.json
    install -D ${./kwin-script/contents/code/main.js} $out/share/kwin/scripts/phoenix-monitor-layout/contents/code/main.js
  '';
in

{
  imports = [
    ./fan-control.nix
  ];

  # Bare-metal desktop options belong here.

  environment.systemPackages = [
    monitorLayoutReflow
    kwinMonitorLayoutScript
  ];

  services.displayManager.defaultSession = "hyprland";

  home-manager.users.${user.name} = {
    systemd.user.services.phoenix-monitor-layout-enable = {
      Unit = {
        Description = "Enable phoenix monitor reflow in KWin";
        After = [ "plasma-workspace.target" ];
        PartOf = [ "graphical-session.target" ];
      };

      Service = {
        Type = "oneshot";
        ExecStart = "${pkgs.kdePackages.kconfig}/bin/kwriteconfig6 --file kwinrc --group Plugins --key phoenix-monitor-layoutEnabled true";
        ExecStartPost = "${pkgs.systemd}/bin/busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure";
      };

      Install.WantedBy = [ "graphical-session.target" ];
    };

    systemd.user.services.phoenix-monitor-layout = {
      Unit = {
        Description = "Reflow available phoenix monitors in physical order";
        After = [
          "plasma-workspace.target"
          "phoenix-monitor-layout-enable.service"
        ];
        Requires = [ "phoenix-monitor-layout-enable.service" ];
        PartOf = [ "graphical-session.target" ];
      };

      Service = {
        Type = "oneshot";
        ExecStart = "${monitorLayoutReflow}/bin/phoenix-monitor-layout";
      };

      Install.WantedBy = [ "graphical-session.target" ];
    };
  };
}
