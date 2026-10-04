# Run with: nix eval --impure --file tests/desktop-services.nix
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  metal = flake.nixosConfigurations.metal.config;
  vm = flake.nixosConfigurations.vm.config;
  user = import ../config/user.nix { inherit (flake.inputs.nixpkgs) lib; };
  sharedServices =
    config:
    config.services.displayManager.sddm.enable
    && config.services.pipewire.enable
    && config.services.upower.enable
    && config.services.power-profiles-daemon.enable;
  metalUserServices = metal.home-manager.users.${user.name}.systemd.user.services;
in
assert sharedServices metal;
assert sharedServices vm;
assert metal.programs.hyprland.enable;
assert !metal.services.desktopManager.plasma6.enable;
assert !metal.home-manager.users.${user.name}.programs.plasma.enable;
assert metal.services.displayManager.defaultSession == "hyprland";
assert vm.services.desktopManager.plasma6.enable;
assert vm.home-manager.users.${user.name}.programs.plasma.enable;
assert vm.services.displayManager.defaultSession == "plasmax11";
assert !(metalUserServices ? phoenix-monitor-layout);
assert !(metalUserServices ? phoenix-monitor-layout-enable);
true
