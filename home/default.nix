{ user, ... }:

{
  imports = [
    ./caelestia.nix
    ./firefox
    ./input.nix
    ./mimeapps.nix
    ./plasma.nix
    ./security
    ./shell-aliases.nix
    ./vscodium.nix
  ];

  home = {
    username = user.name;
    homeDirectory = user.homeDirectory;
    stateVersion = "25.11";
  };

  programs.git = {
    enable = true;
    settings = {
      user = {
        name = "V";
        email = "12031173+v-avuso@users.noreply.github.com";
      };

      credential = {
        helper = "manager";
        credentialStore = "secretservice";
        gitHubAuthModes = "browser";
      };
    };
  };
}
