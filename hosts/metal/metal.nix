{ ... }:

{
  imports = [
    ./fan-control.nix
  ];

  # Bare-metal desktop options belong here.

  services.displayManager.defaultSession = "hyprland";
}
