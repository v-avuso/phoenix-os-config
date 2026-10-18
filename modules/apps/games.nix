{ pkgs, ... }:

let
  nmsFrameGenerationFix = import ./nms-frame-generation { inherit pkgs; };
in
{
  nixpkgs.config.allowUnfreePackages = [
    "steam"
    "steam-unwrapped"
  ];

  programs.steam.enable = true;

  # The explicit layer is inert unless a game requests it. No Man's Sky's
  # per-game launch options are documented in modules/apps/README.md.
  environment.systemPackages = [ nmsFrameGenerationFix ];
}
