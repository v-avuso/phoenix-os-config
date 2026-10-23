{ config, lib, pkgs, ... }:
{
  options.phoenix.target = lib.mkOption {
    type = lib.types.enum [ "metal" "metal-4tb" "vm" ];
    default = if config.networking.hostName == "phoenix-vm" then "vm" else "metal";
    description = "Installed flake target shared by commands, updater and deployment authorization.";
  };
  config.system.build.phoenixTarget = import ../commands/target.nix {
    inherit pkgs;
    defaultTarget = config.phoenix.target;
  };
}
