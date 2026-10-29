{ pkgs, user, ... }:

{
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.networkmanager.enable = true;

  time.timeZone = "Europe/Berlin";

  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS = "de_DE.UTF-8";
    LC_IDENTIFICATION = "de_DE.UTF-8";
    LC_MEASUREMENT = "de_DE.UTF-8";
    LC_MONETARY = "de_DE.UTF-8";
    LC_NAME = "de_DE.UTF-8";
    LC_NUMERIC = "de_DE.UTF-8";
    LC_PAPER = "de_DE.UTF-8";
    LC_TELEPHONE = "de_DE.UTF-8";
    LC_TIME = "de_DE.UTF-8";
  };

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  # Apply at the daemon: untrusted deployment builders cannot override these
  # settings. Resume transient cache failures without five-minute idle waits on
  # every attempt; a persistent outage must fail visibly instead of hanging.
  nix.settings.stalled-download-timeout = 30;
  nix.settings.download-attempts = 3;

  users.users.${user.name} = {
    isNormalUser = true;
    description = user.description;
    extraGroups = [ "networkmanager" "wheel" ];
  };

  system.stateVersion = "25.11";
}
