{
  imports = [
    ./metal.nix
    ./audio.nix
    ../../modules
  ];

  phoenix.agent.wakeupDevices = [ "0000:10:00.4" ];
  networking.hostName = "phoenix";
}
