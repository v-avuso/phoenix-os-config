{ pkgs, user, nixosConfig, ... }:

{
  home.packages = [
    (import ../commands {
      inherit pkgs user;
      deploymentHelper = nixosConfig.system.build.phoenixDeploymentClient or null;
      nixosRebuild = nixosConfig.system.build.nixos-rebuild;
      hyprlandPackage =
        if nixosConfig.programs.hyprland.enable then
          nixosConfig.programs.hyprland.package
        else
          pkgs.hyprland;
    })
  ];
}
