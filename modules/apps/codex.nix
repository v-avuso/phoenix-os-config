{ pkgs, inputs, ... }:

let
  system = pkgs.stdenv.hostPlatform.system;
in
{
  environment.systemPackages = [
    pkgs.codex
    inputs.codex-desktop-linux.packages.${system}.codex-desktop
  ];
}
