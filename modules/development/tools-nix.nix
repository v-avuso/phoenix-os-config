{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Nix language server used by jnoortheen.nix-ide for completions, diagnostics, and navigation.
    nixd

    # Standard Nix formatter; provides the `nixfmt` binary used by nixd formatting.
    nixfmt-rfc-style

    # TOML formatter/linter/LSP CLI; useful for shell checks even though Even Better TOML also provides editor support.
    taplo
  ];

  # direnv: auto-loads project-local environments from .envrc.
  programs.direnv.enable = true;

  # nix-direnv: faster Nix/flake integration for direnv.
  programs.direnv.nix-direnv.enable = true;
}
