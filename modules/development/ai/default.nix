{ pkgs, ... }:

{
  imports = [
    ./codex.nix
    ./agent/codex-sandbox.nix
    ./agent/deployment.nix
    ./agent
    ./agent/gui.nix
  ];
}
