{ pkgs, user, nixosConfig, ... }:
let
  deploymentHelper = nixosConfig.system.build.phoenixDeploymentClient or null;
  phoenixCommands = import ../commands {
    inherit pkgs user deploymentHelper;
    nixosRebuild = nixosConfig.system.build.nixos-rebuild;
    hyprlandPackage = if nixosConfig.programs.hyprland.enable then
      nixosConfig.programs.hyprland.package else pkgs.hyprland;
  };
  brokerAvailable = nixosConfig.system.build ? phoenixAuthorizationLibrary
    && nixosConfig.system.build ? phoenixAuthorizationPolicy;
  aiBroker = import ../modules/development/ai/agent/authorization/adapter.nix {
    inherit pkgs;
    authorizationLibrary = nixosConfig.system.build.phoenixAuthorizationLibrary;
    authorizationPolicy = nixosConfig.system.build.phoenixAuthorizationPolicy;
    adminClient = nixosConfig.system.build.phoenixAdminClient or null;
    deploymentCommands = pkgs.lib.optionalAttrs (deploymentHelper != null)
      (pkgs.lib.genAttrs [ "phoenix-test" "phoenix-switch" "phoenix-boot" ]
        (name: "${phoenixCommands}/bin/${name}"));
  };
in {
  home.packages = [ phoenixCommands ] ++ pkgs.lib.optional brokerAvailable aiBroker;
}
