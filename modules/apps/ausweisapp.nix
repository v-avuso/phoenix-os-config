{ pkgs, user, ... }:

{
  home-manager.users.${user.name}.home.packages = [
    pkgs.ausweisapp
  ];
}
