{ pkgs, ... }:

{
  imports = [
    ./codex.nix
    ./agent/codex-sandbox.nix
    ./agent/review.nix
    ./agent
  ];
}
