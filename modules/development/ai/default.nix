{ pkgs, ... }:

{
  imports = [
    ./codex.nix
    ./agent/codex-sandbox.nix
    ./agent
  ];
}
