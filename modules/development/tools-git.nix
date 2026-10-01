{ pkgs, ... }:

let
  desktopScale = import ../../config/desktop-scale.nix;
  sourcegit = pkgs.symlinkJoin {
    name = "sourcegit-phoenix";
    paths = [ pkgs.sourcegit ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram "$out/bin/SourceGit" \
        --set AVALONIA_SCREEN_SCALE_FACTORS \
        "HDMI-A-2=${toString desktopScale};DP-1=${toString desktopScale};DP-2=${toString desktopScale}"
    '';
  };
in

{
  environment.systemPackages = with pkgs; [
    # Baseline version-control CLI.
    git

    # HTTPS credential helper with GitHub OAuth and Secret Service support.
    (git-credential-manager.override { withGpgSupport = false; })

    # Visual Git client for history, staging, diffs, branches.
    sourcegit
  ];
}
