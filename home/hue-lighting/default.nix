{
  osConfig,
  pkgs,
  ...
}:
let
  huenicorn = import ./package.nix { inherit pkgs; };
  sources = pkgs.runCommand "phoenix-hue-control-sources" { } ''
    mkdir -p $out
    cp ${./control.py} $out/control.py
    cp ${./panel.html} $out/panel.html
    cp ${./edge-test.html} $out/edge-test.html
    cp ${./sources.py} $out/sources.py
    cp ${./portal-picker.py} $out/portal-picker.py
  '';
  picker = pkgs.writeShellScript "phoenix-hue-source-picker" ''
    exec ${pkgs.python3}/bin/python3 -B ${sources}/portal-picker.py \
      --picker ${osConfig.programs.hyprland.portalPackage}/bin/hyprland-share-picker "$@"
  '';
  server = pkgs.writeShellApplication {
    name = "phoenix-hue-server";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 -B ${sources}/control.py --huenicorn ${huenicorn}/bin/huenicorn \
        --systemd-run ${pkgs.systemd}/bin/systemd-run
    '';
  };
  launcher = pkgs.writeShellApplication {
    name = "phoenix-hue-control";
    runtimeInputs = [
      pkgs.python3
      pkgs.xdg-utils
      pkgs.coreutils
    ];
    text = ''
      # The login service owns the panel; reopening never toggles sync.
      ${pkgs.systemd}/bin/systemctl --user start phoenix-hue-control.service
      for ((attempt = 0; attempt < 30; attempt++)); do
        if python3 -c 'import urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:8217/api/state", timeout=1)' 2>/dev/null; then
          exec xdg-open http://127.0.0.1:8217/
        fi
        sleep 0.1
      done
      echo "Hue control panel did not become ready; inspect phoenix-hue-control.service" >&2
      exit 1
    '';
  };
in
{
  config = {
    home.packages = [ launcher ];
    systemd.user.services.phoenix-hue-control = {
      Unit = {
        Description = "Phoenix Hue control panel";
        PartOf = [ "hyprland-session.target" ];
        After = [ "graphical-session-pre.target" ];
      };
      Service = {
        ExecStart = "${server}/bin/phoenix-hue-server";
        Restart = "on-failure";
        RestartSec = 3;
        TimeoutStopSec = 15;
        UMask = "0077";
      };
      Install.WantedBy = [ "hyprland-session.target" ];
    };
    xdg.configFile."hypr/xdph.conf".text = ''
      screencopy {
        custom_picker_binary = ${picker}
      }
    '';
    xdg.desktopEntries.phoenix-hue-control = {
      name = "Hue Sync";
      comment = "Sync on/off and one glow control for both Hue lamps";
      exec = "${launcher}/bin/phoenix-hue-control";
      terminal = false;
      icon = "preferences-color";
      categories = [ "Utility" ];
    };
  };
}
