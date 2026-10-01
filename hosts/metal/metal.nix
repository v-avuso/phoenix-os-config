{
  config,
  inputs,
  lib,
  pkgs,
  user,
  ...
}:

let
  hyprlandPackages = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system};
  filterHyprlandSession =
    package:
    (pkgs.symlinkJoin {
      name = "hyprland-phoenix";
      paths = [ package ];
      postBuild = ''
        rm -f "$out/share/wayland-sessions/hyprland-uwsm.desktop"
      '';
    })
    // {
      inherit (package) version;
      meta = package.meta // {
        outputsToInstall = [ "out" ];
      };
      providedSessions = builtins.filter (session: session != "hyprland-uwsm") package.providedSessions;
      override =
        {
          enableXWayland ? true,
        }:
        filterHyprlandSession (package.override { inherit enableXWayland; });
    };
  hyprlandPhoenix = filterHyprlandSession hyprlandPackages.hyprland;

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

  caelestiaShellBaseline =
    config.home-manager.users.${user.name}.xdg.dataFile."caelestia/shell.json.nix-baseline".source;
  reassertCaelestiaShell = pkgs.writeShellScript "phoenix-reassert-caelestia-shell" ''
    set -euo pipefail

    target=${user.homeDirectory}/.config/caelestia/shell.json
    baseline=${caelestiaShellBaseline}

    if [ -L "$target" ] || [ ! -f "$target" ]; then
      echo "Caelestia shell settings must be a regular runtime file: $target" >&2
      exit 1
    fi
    if [ ! -O "$target" ]; then
      echo "Caelestia shell settings are not owned by ${user.name}: $target" >&2
      exit 1
    fi
    if [ ! -w "$target" ]; then
      ${pkgs.coreutils}/bin/chmod u+rw "$target"
    fi

    runtime_json="$(${pkgs.coreutils}/bin/mktemp)"
    baseline_json="$(${pkgs.coreutils}/bin/mktemp)"
    trap '${pkgs.coreutils}/bin/rm -f "$runtime_json" "$baseline_json"' EXIT
    if ${pkgs.jq}/bin/jq -S . "$target" > "$runtime_json" 2>/dev/null \
      && ${pkgs.jq}/bin/jq -S . "$baseline" > "$baseline_json" \
      && ${pkgs.diffutils}/bin/cmp -s "$runtime_json" "$baseline_json"; then
      exit 0
    fi

    # Write as user ${user.name} to the existing inode so Caelestia's watcher
    # reloads the baseline without losing its writable runtime-file semantics.
    ${pkgs.coreutils}/bin/cat "$baseline" > "$target"
  '';
in

{
  imports = [
    ./fan-control.nix
  ];

  # Bare-metal desktop options belong here.

  # Reassert only Caelestia's writable runtime file on active system switch/test.
  # Boot skips this hook so runtime experiments survive logout and reboot.
  system.activationScripts.caelestiaShellBaseline = {
    deps = [ "users" ];
    text = ''
      case "''${NIXOS_ACTION:-}" in
        switch|test)
          ${pkgs.util-linux}/bin/runuser -u ${user.name} -- ${reassertCaelestiaShell}
          ;;
      esac
    '';
  };

  # The NixOS-managed HM oneshot runs during boot. It must not erase writable
  # Caelestia experiments there; NixOS switch/test has its own explicit hook.
  systemd.services."home-manager-${user.name}".environment.PHOENIX_SKIP_CAELESTIA_BASELINE = "1";

  services.xserver.videoDrivers = [ "nvidia" ];

  # AusweisApp discovers a paired smartphone card reader through UDP broadcast
  # on port 24727. Its eID activation endpoint is localhost-only.
  networking.firewall.allowedUDPPorts = [ 24727 ];

  programs.hyprland = {
    enable = true;
    # Upstream ships both desktop entries. Phoenix deliberately does not use
    # UWSM yet, so filter only its unsupported login choice. Remove this when
    # Phoenix adopts UWSM.
    package = hyprlandPhoenix;
    portalPackage = hyprlandPackages.xdg-desktop-portal-hyprland;
    xwayland.enable = true;
    withUWSM = false;
  };

  xdg.portal = {
    extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
    config.common.default = [
      "hyprland"
      "gtk"
    ];
  };

  hardware.bluetooth.enable = true;
  programs.dconf.enable = true;
  programs.ydotool.enable = true;
  services.geoclue2.enable = true;

  users.users.${user.name}.extraGroups = [ "ydotool" ];

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
    noto-fonts
    noto-fonts-cjk-sans
    noto-fonts-color-emoji
  ];

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
    powerManagement = {
      enable = true;
      kernelSuspendNotifier = true;
    };
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

  # Preserve the existing gtk.css.backup file instead of letting this
  # generation's Home Manager backup collide with it.
  home-manager.backupFileExtension = lib.mkForce "backup-20260930";

  # hyprshutdown --vt 1 needs a privileged VT return for NVIDIA + SDDM; keep
  # authorization to this user's chvt 1 command only. Remove if display-manager
  # or upstream logout behavior makes the VT handoff unnecessary.
  security.sudo-rs.extraRules = [
    {
      users = [ user.name ];
      runAs = "root";
      commands = [
        {
          command = "${pkgs.util-linux}/bin/chvt 1";
          options = [ "NOPASSWD" ];
        }
      ];
    }
  ];

  home-manager.users.${user.name} = {
    imports = [ ../../home/caelestia.nix ];

    programs.plasma.powerdevil.AC = {
      autoSuspend.idleTimeout = 1800;

      dimDisplay = {
        enable = true;
        idleTimeout = 180;
      };

      turnOffDisplay.idleTimeout = "never";
    };

    # Plasma Manager's typed option has no "never" value for the locked
    # timeout, so set PowerDevil's documented -1 sentinel in powerdevilrc.
    programs.plasma.configFile.powerdevilrc."AC/Display".TurnOffDisplayIdleTimeoutWhenLockedSec = -1;

    programs.plasma.kscreenlocker = {
      autoLock = false;
    };

    systemd.user.services.phoenix-monitor-layout-enable = {
      Unit = {
        Description = "Enable phoenix monitor reflow in KWin";
        After = [ "plasma-workspace.target" ];
        PartOf = [ "plasma-workspace.target" ];
      };

      Service = {
        Type = "oneshot";
        ExecStart = "${pkgs.kdePackages.kconfig}/bin/kwriteconfig6 --file kwinrc --group Plugins --key phoenix-monitor-layoutEnabled true";
        ExecStartPost = "${pkgs.systemd}/bin/busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure";
      };

      Install.WantedBy = [ "plasma-workspace.target" ];
    };

    systemd.user.services.phoenix-monitor-layout = {
      Unit = {
        Description = "Reflow available phoenix monitors in physical order";
        After = [
          "plasma-workspace.target"
          "phoenix-monitor-layout-enable.service"
        ];
        Requires = [ "phoenix-monitor-layout-enable.service" ];
        PartOf = [ "plasma-workspace.target" ];
      };

      Service = {
        Type = "oneshot";
        ExecStart = "${monitorLayoutReflow}/bin/phoenix-monitor-layout";
      };

      Install.WantedBy = [ "plasma-workspace.target" ];
    };
  };
}
