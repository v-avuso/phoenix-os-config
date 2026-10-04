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
in

{
  imports = [
    ../../modules/input/mouse-side-button-debounce.nix
    ./fan-control.nix
  ];

  # Bare-metal desktop options belong here.

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

  services.displayManager.defaultSession = "hyprland";

  # Preserve existing Home Manager backup files, choosing a numbered suffix
  # when the configured backup name is already occupied.
  home-manager.backupFileExtension = lib.mkForce "backup-20260930";
  home-manager.backupCommand = pkgs.writeShellScript "phoenix-home-manager-backup" ''
    target="$1"
    extension="''${HOME_MANAGER_BACKUP_EXT:-backup}"
    backup="$target.$extension"
    suffix=1
    while [ -e "$backup" ] || [ -L "$backup" ]; do
      backup="$target.$extension.$suffix"
      suffix=$((suffix + 1))
    done
    exec ${pkgs.coreutils}/bin/mv -- "$target" "$backup"
  '';

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
  };
}
