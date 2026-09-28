{ pkgs, user, ... }:

{
  nixpkgs.config.allowUnfreePackages = [
    "obsidian"
  ];

  home-manager.users.${user.name}.home.packages = [
    pkgs.obsidian
  ];
}
