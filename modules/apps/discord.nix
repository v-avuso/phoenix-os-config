{ pkgs, user, ... }:

{
  nixpkgs.config.allowUnfreePackages = [ "discord" ];

  home-manager.users.${user.name}.home.packages = [ pkgs.discord ];
}
