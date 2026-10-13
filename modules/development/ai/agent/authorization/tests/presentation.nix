# Packaging/evaluation only; do not run the resulting GUI client.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  off = flake.nixosConfigurations.metal.config;
  on = (flake.nixosConfigurations.metal.extendModules {
    modules = [ { phoenix.authorization.explanation.enable = true; } ];
  }).config;
  settings = cfg: builtins.fromJSON (builtins.unsafeDiscardStringContext cfg.system.build.phoenixAuthorizationPresentation.text);
  user = import ../../../../../../config/user.nix { inherit lib; };
  packages = on.home-manager.users.${user.name}.home.packages;
  broker = builtins.head (builtins.filter (package: (package.name or "") == "ai-broker") packages);
in
assert !off.phoenix.authorization.explanation.enable;
assert settings off == null;
assert on.phoenix.authorization.explanation.enable;
assert lib.hasInfix "zenity" (settings on).program;
assert lib.hasInfix "phoenix-authorization-presentation.py" (settings on).module;
assert !on.services.phoenixDeployment.securityReview.enable;
{ passed = true; nativeBroker = broker; nativeClient = on.system.build.phoenixDeploymentClient;
  adminClient = on.system.build.phoenixAdminClient;
  presentationConfig = on.system.build.phoenixAuthorizationPresentation; }
