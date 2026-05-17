{ inputs, pkgs, ... }:

let
  hyprlandPackages = inputs.hyprland.packages.${pkgs.stdenv.hostPlatform.system};
in

{
  imports = [
    inputs.caelestianix.homeManagerModules.default
  ];

  # CaelestiaNix's Hypr module asserts that Home Manager Hyprland is enabled.
  wayland.windowManager.hyprland = {
    enable = true;
    package = hyprlandPackages.hyprland;
  };

  programs.caelestia-dots = {
    enable = true;
    hypr.enable = true;
    term.enable = true;
    btop.enable = true;
    foot.enable = true;
    caelestia.enable = true;
  };
}
