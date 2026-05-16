{ inputs, ... }:

{
  imports = [
    inputs.caelestianix.homeManagerModules.default
  ];

  # CaelestiaNix's Hypr module asserts that Home Manager Hyprland is enabled.
  wayland.windowManager.hyprland.enable = true;

  programs.caelestia-dots = {
    enable = true;
    hypr.enable = true;
    term.enable = true;
    btop.enable = true;
    foot.enable = true;
    caelestia.enable = true;
  };
}
