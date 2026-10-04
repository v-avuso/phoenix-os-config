{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:
let
  # Pin and guard the upstream simple restore path: layout reconstruction can
  # close splash windows, whereas simple restore only adopts or launches apps.
  package = pkgs.rustPlatform.buildRustPackage {
    pname = "hypr-persist";
    version = "0.1.2";
    src = inputs.hypr-persist;
    cargoLock.lockFile = inputs.hypr-persist + "/Cargo.lock";
    nativeBuildInputs = [
      pkgs.python3
      pkgs.mold
    ];
    postPatch = ''
      cat ${../tests/hypr-persist-resolver.rs} >> src/resolver/mod.rs
    '';
    preCheck = ''
      ${pkgs.python3}/bin/python3 ${../tests/hypr-persist-source.py} .
    '';
    doCheck = true;
    meta = {
      description = "Event-driven Hyprland application and workspace persistence";
      homepage = "https://github.com/ngamber/hypr-persist";
      license = lib.licenses.bsd3;
      mainProgram = "hypr-persist";
      platforms = lib.platforms.linux;
    };
  };
  # Fresh private state; never import or reconcile someone else's executable
  # session data. Upstream appends /sessions and atomically saves last.toml.
  stateDirectory = "${config.xdg.stateHome}/phoenix-hypr-persist";
  settings = {
    general = {
      save_interval = 120;
      session_dir = stateDirectory;
      restore_on_start = true;
      per_window_launch = true;
      restore_geometry = true;
      restore_layout = false;
    };
    rules.exclude = [
      "^xdg-desktop-portal.*$"
      "^org\\.kde\\.polkit.*$"
      "^polkit-gnome-authentication-agent-1$"
      "^org\\.gnome\\.PolicyKit1$"
      "^quickshell$"
      "^caelestia([.-].*)?$"
      "^hyprpicker$"
    ];
    # Both main apps remain restorable. Exact supported overrides prevent the
    # /proc fallback from launching a sandbox's bare Electron executable.
    # Current-system paths keep remembered commands valid across deployments.
    overrides = {
      codex-desktop = "/run/current-system/sw/bin/codex-desktop";
      codex-desktop-sandboxed = "/run/current-system/sw/bin/codex-desktop-sandboxed";
    };
  };
  configuration = (pkgs.formats.toml { }).generate "phoenix-hypr-persist.toml" settings;
in
{
  home.packages = [ package ];
  systemd.user.services.hypr-persist = {
    Unit = {
      Description = "Restore and persist Hyprland applications and workspaces";
      Documentation = [ "https://github.com/ngamber/hypr-persist" ];
      PartOf = [ "hyprland-session.target" ];
      BindsTo = [ "hyprland-session.target" ];
      After = [ "hyprland-session.target" ];
      ConditionEnvironment = "HYPRLAND_INSTANCE_SIGNATURE";
    };
    Service = {
      Type = "simple";
      UMask = "0077";
      ExecStartPre = "${pkgs.coreutils}/bin/install -d -m 0700 ${lib.escapeShellArg stateDirectory}";
      ExecStart = "${package}/bin/hypr-persist --config ${configuration}";
      # Native SIGTERM performs the final save; an independent ExecStop saver
      # would race upstream's shared temporary filename. Avoid restore loops.
      Restart = "no";
      TimeoutStopSec = 30;
    };
    Install.WantedBy = [ "hyprland-session.target" ];
  };
}
