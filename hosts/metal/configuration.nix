{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./metal.nix
    ../../modules
  ];

  networking.hostName = "phoenix";
}
