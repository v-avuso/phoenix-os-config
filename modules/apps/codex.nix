{ pkgs, inputs, ... }:

let
  system = pkgs.stdenv.hostPlatform.system;

  unstable = import inputs.nixpkgs-unstable {
    inherit system;
  };
in
{
  environment.systemPackages = [
    inputs.codex-desktop-linux.packages.${system}.codex-desktop
    unstable.codex
  ];
}
