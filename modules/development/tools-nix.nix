{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Formatter for .nix files; keeps config diffs clean.
    nixfmt-rfc-style
  ];

  # direnv: auto-loads project-local environments from .envrc.
  programs.direnv.enable = true;

  # nix-direnv: faster Nix/flake integration for direnv.
  programs.direnv.nix-direnv.enable = true;
}
