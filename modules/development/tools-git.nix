{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Baseline version-control CLI.
    git
  ];
}
