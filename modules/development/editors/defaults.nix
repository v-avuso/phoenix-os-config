{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # Lightweight GUI editor for quick scripts/config edits.
    kdePackages.kate
  ];
}
