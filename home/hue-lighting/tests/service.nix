# Non-activating integration checks for the generated login service.
let
  flake = builtins.getFlake ("git+file://" + toString ../../..);
  config = flake.nixosConfigurations.metal-4tb.config.home-manager.users.v;
  unit = config.systemd.user.services.phoenix-hue-control;
in
assert unit.Install.WantedBy == [ "hyprland-session.target" ];
assert unit.Unit.PartOf == [ "hyprland-session.target" ];
assert unit.Service.Restart == "on-failure";
assert unit.Service.UMask == "0077";
assert builtins.length unit.Service.ExecStart == 1;
assert flake.inputs.nixpkgs.lib.hasSuffix "/bin/phoenix-hue-server" (builtins.head unit.Service.ExecStart);
true
