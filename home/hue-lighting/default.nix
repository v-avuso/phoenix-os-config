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
  launcher = pkgs.writeShellApplication {
    name = "phoenix-hue-control";
    runtimeInputs = [
      pkgs.python3
      pkgs.xdg-utils
    ];
    text = ''
      # Reopening the launcher reuses the existing panel, without toggling sync.
      if python3 -c 'import urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:8217/api/state", timeout=1)' 2>/dev/null; then
        exec xdg-open http://127.0.0.1:8217/
      fi
      exec python3 -B ${sources}/control.py --huenicorn ${huenicorn}/bin/huenicorn \
        --systemd-run ${pkgs.systemd}/bin/systemd-run --open-browser
    '';
  };
in
{
  config = {
    home.packages = [ launcher ];
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
