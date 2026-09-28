{ user, ... }:

{
  imports = [
    ./caelestia.nix
    ./firefox
    ./input.nix
    ./mimeapps.nix
    ./plasma.nix
    ./security
    ./vscodium.nix
  ];

  home = {
    username = user.name;
    homeDirectory = user.homeDirectory;
    stateVersion = "25.11";
  };

  programs.git = {
    enable = true;
    userName = "V";
    userEmail = "12031173+v-avuso@users.noreply.github.com";
  };
}
