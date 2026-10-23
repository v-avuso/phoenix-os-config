# Build the real wheel/import checks from a Git-visible or vetted frozen source.
{ flakeSource ? "git+file://${toString ../..}" }:
let
  flake = builtins.getFlake flakeSource;
  user = import ../../config/user.nix { lib = flake.inputs.nixpkgs.lib; };
  cli = flake.nixosConfigurations.metal.config.home-manager.users.${user.name}.programs.caelestia.cli.package;
in cli
