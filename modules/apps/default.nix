{ pkgs, ... }:

{
  imports = [
    # ./codex.nix  # Commented out due to hash mismatch. Try again later.
  ];

  programs.firefox.enable = true;

  environment.systemPackages = with pkgs; [
    git
    kdePackages.kate
  ];
}
