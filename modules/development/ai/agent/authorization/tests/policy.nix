# Run: nix eval --impure --file modules/development/ai/agent/authorization/tests/policy.nix
# Real module composition and runner/policy seam; no service start or live change.
let
  flake = builtins.getFlake ("git+file://" + toString ../../../../../..);
  lib = flake.inputs.nixpkgs.lib;
  user = import ../../../../../../config/user.nix { inherit lib; };
  evaluate = modules:
    let
      config = (flake.nixosConfigurations.metal.extendModules {
        modules = [ { services.phoenixUpdates.enable = lib.mkForce true; } ] ++ modules;
      }).config;
    in {
      members = config.users.groups.phoenix-authorization.members;
      policy = builtins.fromJSON config.system.build.phoenixAuthorizationPolicy.text;
      serviceUser = config.systemd.services.phoenix-updates.serviceConfig.User;
      # Force actual runnerConfig packaging, which formerly completed the cycle.
      execStart = toString config.systemd.services.phoenix-updates.serviceConfig.ExecStart;
      assertions = map (item: item.assertion) config.assertions;
    };
  shared = evaluate [ ];
  distinct = evaluate [ {
    phoenix.authorization.updaterUser = "phoenix-update-fixture";
    users.users.phoenix-update-fixture = {
      isSystemUser = true;
      uid = 3000;
      group = "users";
    };
  } ];
  conflict = evaluate [ {
    systemd.services.phoenix-updates.serviceConfig.User = lib.mkForce "root";
  } ];
in
assert shared.members == [ user.name ];
assert shared.policy.updaterUid == shared.policy.operatorUid;
assert shared.serviceUser == user.name;
assert builtins.stringLength shared.execStart > 0;
assert builtins.all (value: value) shared.assertions;
assert distinct.members == [ user.name "phoenix-update-fixture" ];
assert distinct.policy.updaterUid == 3000;
assert distinct.policy.clientUid == shared.policy.clientUid;
assert distinct.policy.operatorUid == shared.policy.operatorUid;
assert distinct.serviceUser == "phoenix-update-fixture";
assert builtins.stringLength distinct.execStart > 0;
assert builtins.all (value: value) distinct.assertions;
assert !(builtins.all (value: value) conflict.assertions);
{ passed = true; }
