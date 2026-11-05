let
  flake = builtins.getFlake ("git+file://" + toString ../../../..);
  lib = flake.inputs.nixpkgs.lib;
  check =
    name:
    let
      c = flake.nixosConfigurations.${name}.config;
      kernel = c.boot.kernelPackages.kernel;
      flags = kernel.configfile.moduleStructuredConfig.settings;
      service = c.systemd.services.phoenix-wifi-diagnostics.serviceConfig;
    in
    assert kernel.version == "7.3";
    assert c.programs.hyprland.package.version == "0.56.2";
    assert c.hardware.nvidia.package.version == "595.99.02";
    assert c.networking.networkmanager.wifi.powersave == false;
    assert builtins.all (flag: flags.${flag}.tristate == "y") [
      "ATH12K_DEBUG"
      "ATH12K_DEBUGFS"
      "ATH12K_TRACING"
      "ATH12K_COREDUMP"
    ];
    assert service.RuntimeMaxSec == "24h";
    assert service.User == "root" && service.Group == "phoenix-wifi-diagnostics";
    assert lib.elem "phoenix-wifi-diagnostics" c.users.users.v.extraGroups;
    {
      inherit name;
      kernelConfig = toString kernel.configfile;
    };
in
map check [
  "metal"
  "metal-4tb"
]
