{ ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./metal.nix
    ./audio.nix
    ../../modules
  ];

  networking.hostName = "phoenix";
}
