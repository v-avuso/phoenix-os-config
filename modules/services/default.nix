{
  imports = [
    ./dji-hibernate-wakeup.nix
    ./music.nix
    ./syncthing.nix
    ./updates/module.nix
  ];
  # The integrated updater stages reviewed generations; it never reboots.
  services.phoenixUpdates.enable = true;
}
