{ ... }:

{
  imports =
    (if builtins.pathExists ./hardware-configuration.nix then
      [ ./hardware-configuration.nix ]
    else
      [ ])
    ++ [
      ./vm.nix
      ../../modules
    ];

  networking.hostName = "phoenix-vm";
}
