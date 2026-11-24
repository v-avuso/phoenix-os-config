{ pkgs }:
let
  # Initial install only. Subsequent releases are installed by TSM's updater.
  appImage = pkgs.fetchurl {
    url = "https://tsm-desktop-app-builds-production.nyc3.cdn.digitaloceanspaces.com/versions/1.0.15/TradeSkillMaster.AppImage";
    name = "TradeSkillMaster-1.0.15.AppImage";
    sha256 = "1v2y2mlq7wmrpn85kdrjgqn4kn4x3fbgs328ih3w18si7s0ik2yj";
  };
in
pkgs.writeShellApplication {
  name = "tsm-app";
  runtimeInputs = [ pkgs.appimage-run pkgs.coreutils pkgs.util-linux ];
  text = ''
    installDir="''${XDG_DATA_HOME:-$HOME/.local/share}/tradeskillmaster-appimage"
    executable="$installDir/TradeSkillMaster.AppImage"
    if [[ ! -e "$executable" ]]; then
      (umask 077; mkdir -p -- "$installDir")
      staging=$(mktemp -- "$installDir/.install.XXXXXXXX")
      trap 'rm -f -- "$staging"' EXIT
      install -m 700 -- ${appImage} "$staging"
      # Publish only a complete copy and preserve any existing installation.
      ln -T -- "$staging" "$executable" || [[ -x "$executable" ]]
      rm -f -- "$staging"
      trap - EXIT
    fi
    export APPIMAGE_EXTRACT_AND_RUN=1
    # The launcher holds the lock only while the app runs. Keep the lock FD
    # out of Electron's descendants so they cannot leave a stale lock.
    exec flock --nonblock --close --conflict-exit-code 75 \
      "$XDG_RUNTIME_DIR/phoenix-tsm.lock" appimage-run "$executable" "$@"
  '';
}
