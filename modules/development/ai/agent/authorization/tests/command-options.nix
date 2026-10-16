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
  base = evaluate { };
  definition = { executable = "${pkgs.coreutils}/bin/id"; arguments = [ "-u" ]; rationale = "Read exact UID"; };
  automatic = evaluate { phoenix.authorization.commands = { enable = true; entries.identity = definition // { mode = "automatic"; }; }; };
  reviewOff = evaluate { phoenix.authorization.commands = { enable = true; entries.identity = definition // { mode = "review"; }; }; };
  reviewOn = evaluate { phoenix.authorization.commands = { enable = true; entries.identity = definition // { mode = "review"; }; }; services.phoenixDeployment.securityReview.enable = true; };
  disabled = evaluate { phoenix.authorization.commands.entries.identity = definition; };
  disabledReview = evaluate { phoenix.authorization.commands.entries.identity = definition // { mode = "review"; }; };
  blank = evaluate { phoenix.authorization.commands = { enable = true; entries.identity = definition // { rationale = " "; }; }; };
  valid = cfg: builtins.all (a: a.assertion) cfg.assertions;
in
assert !base.phoenix.authorization.commands.enable;
assert base.phoenix.authorization.commands.entries == { };
assert valid automatic;
assert !valid reviewOff;
assert valid reviewOn;
assert valid disabled;
assert valid disabledReview;
assert !disabledReview.services.phoenixDeployment.securityReview.enable;
assert !valid blank;
{ passed = true; }
