# Run with: nix eval --impure --file tests/opensnitch-observation.nix
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  config = flake.nixosConfigurations.metal.config;
  rules = config.services.opensnitch.rules;
in
assert config.services.opensnitch.settings.DefaultAction == "allow";
assert config.services.opensnitch.settings.InterceptUnknown == false;
assert builtins.attrNames rules == [ "999-allow-outbound-observation" ];
assert rules."999-allow-outbound-observation".action == "allow";
assert config.networking.firewall.enable;
assert !config.networking.firewall.allowPing;
true
