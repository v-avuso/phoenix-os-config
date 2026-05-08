{ lib, ... }:

{
  imports =
    lib.optionals (builtins.pathExists ./hardware-configuration.nix) [
      ./hardware-configuration.nix
    ]
    ++ [
      ./metal.nix
      ../../modules/base.nix
      ../../modules/desktop.nix
    ];

  networking.hostName = "phoenix";
}
