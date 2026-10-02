{
  config,
  inputs,
  lib,
  pkgs,
  user,
  ...
}:

let
  home = config.home-manager.users.${user.name};
  writer = import ../home/mutable-json-settings.nix { inherit pkgs; };
  # Only declared preferences participate; browser/editor session data and
  # hardware-control runtime state keep their own lifecycle and ownership.
  baselines =
    lib.optionals home.programs.vscodium.enable [
      {
        source = home.xdg.dataFile."vscodium/settings.json.nix-baseline".source;
        target = "${home.xdg.configHome}/VSCodium/User/settings.json";
        type = "object";
      }
      {
        source = home.xdg.dataFile."vscodium/keybindings.json.nix-baseline".source;
        target = "${home.xdg.configHome}/VSCodium/User/keybindings.json";
        type = "array";
      }
    ]
    ++ lib.optionals (home.programs ? caelestia && home.programs.caelestia.enable) [
      {
        source = home.xdg.dataFile."caelestia/shell.json.nix-baseline".source;
        target = "${home.xdg.configHome}/caelestia/shell.json";
        type = "object";
      }
    ];
  reassertBaselines = lib.concatMapStringsSep "\n" (
    entry:
    "${pkgs.util-linux}/bin/runuser -u ${lib.escapeShellArg user.name} -- ${writer} reassert ${entry.source} ${lib.escapeShellArg entry.target} ${entry.type}"
  ) baselines;
in
{
  imports = [
    inputs.home-manager.nixosModules.home-manager
  ];

  # NixOS activation reasserts the new generation's baseline. At boot the HM
  # service only initializes absent files, preserving writable experiments.
  system.activationScripts.mutableApplicationSettings = lib.mkIf (baselines != [ ]) {
    deps = [ "users" ];
    text = ''
      case "''${NIXOS_ACTION:-}" in
        switch|test)
          # Activation snippets share a shell; isolate errexit so an earlier
          # writer failure cannot be hidden by a later successful write.
          (
            set -e
            ${reassertBaselines}
          )
          ;;
      esac
    '';
  };
  systemd.services."home-manager-${user.name}".environment.PHOENIX_PRESERVE_MUTABLE_BASELINES = "1";

  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    backupFileExtension = "backup";
    extraSpecialArgs = {
      inherit inputs user;
    };
    sharedModules = [
      inputs.arkenfox-nixos.hmModules.arkenfox
      inputs.plasma-manager.homeModules.plasma-manager
    ];

    users.${user.name} = import ../home;
  };
}
