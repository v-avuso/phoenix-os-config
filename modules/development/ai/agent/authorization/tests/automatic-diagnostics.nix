# Evaluate actual authorization options without services or activation.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../../..);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  lib = pkgs.lib;
  evaluate = extra: (lib.evalModules {
    specialArgs = { inherit pkgs; user = { name = "operator"; }; };
    modules = [ ../default.nix {
      options.assertions = lib.mkOption { type = lib.types.listOf lib.types.anything; default = [ ]; };
      config._module.freeformType = lib.types.attrsOf lib.types.anything;
      config.users.users.operator.uid = 1000;
      config.phoenix.agent.identity.enable = false;
      config.phoenix.agent.wakeupDevices = [ ];
      config.networking.hostName = "fixture";
    } extra ];
  }).config;
  normal = evaluate { };
  on = evaluate { phoenix.authorization.automaticDiagnostics.enable = true; };
  off = evaluate { phoenix.authorization.automaticDiagnostics.enable = false; };
  denied = evaluate {
    phoenix.authorization.automaticDiagnostics.enable = false;
    phoenix.authorization.diagnostics.dmesg = "denied";
  };
  contradiction = evaluate {
    phoenix.authorization.automaticDiagnostics.enable = false;
    phoenix.authorization.diagnostics.dmesg = "automatic";
  };
  reviewOn = evaluate {
    phoenix.authorization.automaticDiagnostics.enable = false;
    services.phoenixDeployment.securityReview.enable = true;
  };
  decisions = cfg: builtins.attrValues cfg.phoenix.authorization.diagnostics;
in
assert builtins.all (x: x == "automatic") (decisions normal);
assert decisions normal == decisions on;
assert builtins.all (x: x == "human") (decisions off);
assert denied.phoenix.authorization.diagnostics.dmesg == "denied";
assert builtins.all (x: x.assertion) denied.assertions;
assert !(builtins.all (x: x.assertion) contradiction.assertions);
assert !off.services.phoenixDeployment.securityReview.enable;
assert reviewOn.services.phoenixDeployment.securityReview.enable;
assert decisions reviewOn == decisions off;
{ passed = true; }
