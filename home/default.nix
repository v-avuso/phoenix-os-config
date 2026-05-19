{ user, ... }:

{
  imports = [
    ./caelestia.nix
    ./mimeapps.nix
    ./vscodium.nix
  ];

  home = {
    username = user.name;
    homeDirectory = user.homeDirectory;
    stateVersion = "25.11";
  };
}
