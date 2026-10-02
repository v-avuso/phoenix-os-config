{ pkgs, user, nixosConfig, ... }:

{
  home.packages = [
    (import ../commands {
      inherit pkgs user;
      nixosRebuild = nixosConfig.system.build.nixos-rebuild;
      hyprlandPackage =
        if nixosConfig.programs.hyprland.enable then
          nixosConfig.programs.hyprland.package
        else
          pkgs.hyprland;
    })
  ];
}
