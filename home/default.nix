{ user, ... }:

{
  imports = [
    ./caelestia.nix
  ];

  home = {
    username = user.name;
    homeDirectory = user.homeDirectory;
    stateVersion = "25.11";
  };
}
