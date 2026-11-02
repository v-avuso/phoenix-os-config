# Check host, generated overview and IPC commands consume the held package set.
let
  flake = builtins.getFlake ("git+file://" + toString ../..);
  host = flake.nixosConfigurations.metal-4tb;
  config = host.config;
  user = config.home-manager.users.v;
  lua = user.xdg.configFile."caelestia/hypr-user.lua".text;
  packages = import ../../config/desktop-packages.nix { inherit (flake) inputs; pkgs = host.pkgs; };
  kando = import ../../home/kando/hyprland {
    config = user; inherit (flake) inputs; pkgs = host.pkgs;
  };
in
assert config.programs.hyprland.package.version == "0.56.2";
assert config.boot.kernelPackages.kernel.version == "7.3";
assert flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux.hyprland.version != "0.56.2";
assert flake.inputs.nixpkgs.lib.hasInfix ''configureOverview("0.56.2",'' lua;
assert flake.inputs.nixpkgs.lib.hasInfix
  (builtins.unsafeDiscardStringContext (toString packages.hyprland.hyprland)) kando.commands.overview;
{
  compositor = toString config.programs.hyprland.package;
  kernel = toString config.boot.kernelPackages.kernel;
  nvidia = toString config.hardware.nvidia.package;
}
