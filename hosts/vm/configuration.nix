{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./vm.nix
    ../../modules
  ];

  networking.hostName = "phoenix-vm";
}
