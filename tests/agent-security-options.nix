# Pure declaration checks; never starts a service or enables live review.
{ flake ? builtins.getFlake ("git+file://" + toString ../.) }:
let
  lib = flake.inputs.nixpkgs.lib;
  repository = flake.nixosConfigurations.metal.config;
  off = (flake.nixosConfigurations.metal.extendModules {
    modules = [ { services.phoenixDeployment.securityReview.enable = lib.mkForce false; } ];
  }).config;
  on =
    (flake.nixosConfigurations.metal.extendModules {
      modules = [ { services.phoenixDeployment.securityReview.enable = true; } ];
    }).config;
  alias =
    (flake.nixosConfigurations.metal.extendModules {
      modules = [ { services.phoenixDeployment.modelReview.enable = true; } ];
    }).config;
  ordering =
    (flake.nixosConfigurations.metal.extendModules {
      modules = [ { phoenix.agent.shutdownOrdering.enable = true; } ];
    }).config;
  user = import ../config/user.nix { inherit lib; };
  env =
    c:
    c.home-manager.users.${user.name}.systemd.user.services.phoenix-openshell-podman.Service.Environment
      or [ ];
  policy = "polkit-1/actions/org.phoenix.security-review.policy";
in
assert lib.hasInfix ''host_gateway_ip = "127.0.0.1"'' (
  builtins.readFile off.environment.etc."phoenix-openshell/gateway.toml".source
);
assert repository.services.phoenixDeployment.securityReview.enable;
assert !off.services.phoenixDeployment.securityReview.enable;
assert repository.phoenix.agent.gui.sharedState.enable;
assert !repository.phoenix.agent.identity.enable;
assert !repository.phoenix.agent.reservations.enable;
assert !repository.phoenix.agent.shutdownOrdering.enable;
assert !repository.services.phoenixDeployment.disruptionGuard.enable;
assert !repository.phoenix.authorization.explanation.enable;
assert !off.phoenix.agent.shutdownOrdering.enable;
assert !(off.environment.etc ? ${policy});
assert on.services.phoenixDeployment.securityReview.enable;
assert alias.services.phoenixDeployment.securityReview.enable;
assert on.environment.etc ? ${policy};
assert lib.hasInfix "<allow_active>auth_admin</allow_active>" on.environment.etc.${policy}.text;
assert !(lib.hasInfix "auth_admin_keep" on.environment.etc.${policy}.text);
assert env off == [ ];
assert builtins.length (env ordering) == 1;
assert lib.hasPrefix "CONTAINERS_CONF_OVERRIDE=" (builtins.head (env ordering));
true
