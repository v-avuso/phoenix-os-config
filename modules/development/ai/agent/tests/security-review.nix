# Run: nix eval --impure --file modules/development/ai/agent/tests/security-review.nix
# Declaration/packaging evidence only; never invokes a model, Polkit or activation.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  off = flake.nixosConfigurations.metal.config;
  on = (flake.nixosConfigurations.metal.extendModules {
    modules = [ { services.phoenixDeployment.securityReview.enable = true; } ];
  }).config;
  custom = (flake.nixosConfigurations.metal.extendModules {
    modules = [ {
      services.phoenixDeployment.securityReview = {
        enable = true;
        model = "gpt-6.1-sol";
        effort = "medium";
      };
    } ];
  }).config;
  baselinePolicy = "polkit-1/actions/org.phoenix.security-review-baseline.policy";
  helper = packages: builtins.filter (package: (package.name or "") == "phoenix-review-trust-active") packages;
  source = builtins.readFile ../deployment.nix;
in
assert (builtins.fromJSON (builtins.unsafeDiscardStringContext on.environment.etc."phoenix-agent/active-provenance.json".text)) == {
  version = 1;
  target = (builtins.fromJSON (builtins.unsafeDiscardStringContext on.system.build.phoenixAuthorizationPolicy.text)).target;
  source = toString on.environment.etc."phoenix-agent/activated-source".source;
};
assert !off.services.phoenixDeployment.securityReview.enable;
assert !(off.environment.etc ? ${baselinePolicy});
assert helper off.environment.systemPackages == [ ];
assert builtins.length (helper on.environment.systemPackages) == 1;
assert on.services.phoenixDeployment.securityReview.adapter == "codex";
assert !(lib.hasInfix (builtins.unsafeDiscardStringContext (toString flake.outPath)) (toString on.system.build.phoenixAuthorizationLibrary));
assert !(lib.hasInfix (builtins.unsafeDiscardStringContext (toString flake.outPath)) (toString on.system.build.phoenixDeploymentTransportPolicy));
assert on.system.build.phoenixAuthorizationLibrary.text == builtins.readFile ../authorization/request.py;
assert on.system.build.phoenixDeploymentTransportPolicy.text == builtins.readFile ../transport.json;
assert on.services.phoenixDeployment.securityReview.model == "gpt-6-luna";
assert on.services.phoenixDeployment.securityReview.effort == "high";
assert custom.services.phoenixDeployment.securityReview.model == "gpt-6.1-sol";
assert custom.services.phoenixDeployment.securityReview.effort == "medium";
assert lib.hasInfix "<allow_active>auth_admin</allow_active>" on.environment.etc.${baselinePolicy}.text;
assert !(lib.hasInfix "auth_admin_keep" on.environment.etc.${baselinePolicy}.text);
assert lib.hasInfix ''if [ "$#" -ne 0 ]; then exit 2; fi'' source;
assert lib.hasInfix ("$" + "{deploymentConfig} trust-active") source;
{ passed = true; }
