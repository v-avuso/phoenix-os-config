# Keep the compositor/plugin ABI and recovery kernel on accepted package sets.
# Ordinary application sources continue advancing through the normal updater.
{ inputs, pkgs, policy ? builtins.fromJSON (builtins.readFile ./updates.json) }:
let
  system = pkgs.stdenv.hostPlatform.system;
  held = name: fallback:
    if !(policy.holds ? ${name}) then fallback else
    import (builtins.getFlake "github:NixOS/nixpkgs/${policy.holds.${name}.pin}") {
      inherit system;
      config = pkgs.config or { };
    };
in {
  hyprland = held "hyprland" inputs.nixpkgs-unstable.legacyPackages.${system};
  kernel = held "linux_latest" pkgs;
}
