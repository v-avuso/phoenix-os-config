{ ... }:

{
  phoenix.agent.wakeupDevices = [ "0000:10:00.4" ];
  imports = [
    ./hardware-configuration.nix
    ./metal.nix
    ./audio.nix
    ../../modules
  ];

  networking.hostName = "phoenix";
}
