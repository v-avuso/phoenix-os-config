{ pkgs, ... }:

{
  imports = [
    ./codex.nix
  ];

  programs.firefox.enable = true;

  environment.systemPackages = with pkgs; [
    git
    kdePackages.kate
  ];
}
