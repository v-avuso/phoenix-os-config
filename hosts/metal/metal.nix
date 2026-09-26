{
  config,
  pkgs,
  user,
  ...
}:

let
  # Physical left-to-right facts, also suitable for reuse by Hyprland later.
  monitorLayout = [
    {
      connector = "DP-1";
      edid = "GSM 23450 479236 10 2020 0";
      preferredMode = {
        width = 3840;
        height = 2160;
        refreshRate = 144;
      };
      scale = 1.7;
    }
    {
      connector = "HDMI-A-2";
      edid = "DEL 41607 809583187 29 2025 0";
      preferredMode = {
        width = 3840;
        height = 2160;
        refreshRate = 240;
      };
      scale = 1.7;
    }
    {
      connector = "DP-2";
      edid = "GSM 23639 372162 9 2023 0";
      preferredMode = {
        width = 3840;
        height = 2160;
        refreshRate = 144.05;
      };
      scale = 1.7;
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

  services.xserver.videoDrivers = [ "nvidia" ];

  hardware.graphics.enable = true;

  hardware.nvidia = {
    # NVIDIA 595.99.02 production from the locked nixpkgs-unstable input.
    # Build its kernel module through the selected 7.2.7 kernel package set.
    package = config.boot.kernelPackages.nvidiaPackages.mkDriver {
      version = "595.99.02";
      sha256_64bit = "sha256-6HR3lYv3YwcFSTJL1a1slI66btIQ5EAFs+/4SUD24ew=";
      sha256_aarch64 = "sha256-CCqHZTN2KNOZ4yZp2rDcuRJp9pHfRw47k4m4dWnS/2w=";
      openSha256 = "sha256-T36x/jx8yQ8l3LFp1rZIrTfcSwbGy8YSAvXOUSptpb4=";
      settingsSha256 = "sha256-GYCcnxfKPrTCrsmd25sMyzfC5cqJQJx0c31haooyTYM=";
      persistencedSha256 = "sha256-VyKtF/HdHPQrHHK6opSO69M72LmnGZtauuchj9uuje8=";
    };
    open = true;
    modesetting.enable = true;
  };

  nixpkgs.config.allowUnfreePackages = [
    "nvidia-x11"
    "nvidia-settings"
  ];

  environment.systemPackages = [
    monitorLayoutReflow
    kwinMonitorLayoutScript
  ];

  services.displayManager.defaultSession = "hyprland";

  home-manager.users.${user.name} = {
    programs.plasma.powerdevil.AC = {
      dimDisplay = {
        enable = true;
        idleTimeout = 180;
      };

      turnOffDisplay.idleTimeout = "never";
    };

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
