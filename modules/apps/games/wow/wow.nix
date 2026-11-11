{
  config,
  lib,
  pkgs,
  user,
  ...
}:
let
  addonDir = config.phoenix.wow.retailAddonDirectory;
  foreverAddonDir = config.phoenix.wow.foreverAddonDirectory;
  toolkit = pkgs.runCommand "phoenix-wow-toolkit" { } ''
    mkdir -p "$out"
    cp -r ${./AddOns/PhoenixWoWToolkit} "$out/PhoenixWoWToolkit"
  '';
  toolkitDeploy = pkgs.writeShellApplication {
    name = "phoenix-wow-toolkit-deploy";
    runtimeInputs = [
      pkgs.python3
      pkgs.util-linux
      pkgs.coreutils
    ];
    text = ''
      mkdir -p "''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow"
      exec 9>"''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow/lock"
      flock -w 60 9
      exec python3 ${./deploy-toolkit.py} "$@"
    '';
  };
  tsmApp = import ./tsm-app.nix { inherit pkgs; };
  tsmForeground = pkgs.writeShellApplication {
    name = "wow-tsm";
    runtimeInputs = [
      tsmApp
      pkgs.util-linux
      pkgs.libnotify
    ];
    text = ''
      exec 8>"$XDG_RUNTIME_DIR/phoenix-tsm.lock"
      if ! flock -n 8; then
        notify-send --app-name="TSM" "TSM is already running" "Open TSM from its system tray icon."
        exit 0
      fi
      export PHOENIX_TSM_START_MINIMIZED=0
      exec tsm-app "$@"
    '';
  };
  tsmSession = pkgs.writeShellApplication {
    name = "wow-tsm-session";
    runtimeInputs = [
      tsmApp
      pkgs.util-linux
      pkgs.procps
      pkgs.coreutils
    ];
    text = builtins.readFile ./tsm-session.sh;
  };
  battleNet = pkgs.writeShellApplication {
    name = "wow-battlenet";
    runtimeInputs = [
      pkgs.systemd
      pkgs.lutris-free
    ];
    text = ''
      systemctl --user start --no-block wow-tsm-session.service
      exec env LUTRIS_SKIP_INIT=1 lutris lutris:rungameid/1
    '';
  };
  battleNetDesktop = pkgs.makeDesktopItem {
    name = "net.lutris.battlenet-1";
    desktopName = "Battle.net";
    icon = "lutris_battlenet";
    exec = "${battleNet}/bin/wow-battlenet";
    categories = [ "Game" ];
    terminal = false;
  };
  profileBaseline = pkgs.writeText "instawow-retail-profile.json" (
    builtins.toJSON {
      profile = "phoenix-retail";
      addon_dir = addonDir;
    }
  );
  foreverProfileBaseline = pkgs.writeText "instawow-forever-profile.json" (builtins.toJSON {
    profile = "phoenix-forever";
    addon_dir = foreverAddonDir;
    flavour_override = "forever_classic";
  });
  # Preserve upstream metadata while selecting the verified native backend.
  wowUpDesktop = pkgs.runCommand "wowup-cf-wayland-desktop" { } ''
    mkdir -p "$out"
    cp ${pkgs.wowup-cf}/share/applications/wowup-cf.desktop "$out/wowup-cf.desktop"
    substituteInPlace "$out/wowup-cf.desktop" \
      --replace-fail 'Exec=wowup-cf --no-sandbox %U' \
      'Exec=${pkgs.wowup-cf}/bin/wowup-cf --no-sandbox --ozone-platform=wayland %U'
  '';
  settingsWriter = import ../../../../home/mutable-json-settings { inherit pkgs; };
  click = pkgs.python3.pkgs.click.overridePythonAttrs {
    version = "8.4.1";
    src = pkgs.fetchPypi {
      pname = "click";
      version = "8.4.1";
      sha256 = "15iyipl8nbs5wn7byz9z9v3na041vvq4niag5p1l2syzxlrmd2wi";
    };
  };
  # Keep the system lock unchanged; patch bounded ZIP probes in the pinned release.
  instawow = pkgs.instawow.overrideAttrs (old: {
    version = "7.3.0";
    src = pkgs.fetchFromGitHub {
      owner = "layday";
      repo = "instawow";
      tag = "v7.3.0";
      hash = "sha256-NJDx1eUj+0Vq61lmR0y8R+H6sV8ajUFIpBrWzw2vATA=";
    };
    patches = (old.patches or [ ]) ++ [ ./instawow-bounded-ranges.patch ];
    nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.python3.pkgs.versioningit ];
    # GitHub archives omit Git metadata; versioningit supports an explicit fallback.
    postPatch = ''
      cp ${./tests/test_instawow_ranges.py} tests/phoenix_ranges_fixture.py
      cat > tests/test_phoenix_ranges.py <<'EOF'
      def test_phoenix_regressions():
          import unittest
          from . import phoenix_ranges_fixture
          suite = unittest.defaultTestLoader.loadTestsFromModule(phoenix_ranges_fixture)
          assert unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
      EOF
      cat >> pyproject.toml <<'EOF'
      [tool.versioningit]
      default-version = "7.3.0"
      EOF
    '';
    # Upstream raises lower bounds beyond the locked packages. Exercise the
    # unchanged dependencies with upstream and real catalogue/release checks.
    pythonRelaxDeps = [
      "aiohttp"
      "rapidfuzz"
      "yarl"
    ];
    propagatedBuildInputs =
      builtins.filter (p: (p.pname or "") != "click") old.propagatedBuildInputs
      ++ [
        click
        pkgs.python3.pkgs.wcwidth
      ];
    nativeCheckInputs = [
      pkgs.python3.pkgs.pytestCheckHook
      pkgs.python3.pkgs.anyio
    ];
    doCheck = true;
    pytestFlags = [
      "tests/test_catalogue_search.py"
      "tests/test_source__github.py"
      "tests/test_phoenix_ranges.py"
      "tests/test_config.py"
      "tests/test_wow_installations.py"
    ];
  });
  wowAddons = pkgs.writeShellApplication {
    name = "wow-addons";
    runtimeInputs = [
      instawow
      pkgs.util-linux
      pkgs.jq
      pkgs.procps
      pkgs.coreutils
    ];
    text = ''
      mkdir -p "''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow"
      exec 9>"''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow/lock"
      flock -w 3600 9
      wow_sync() {
        while IFS= read -r addon; do
          installed=$(instawow -v -p phoenix-retail list --format json "$addon") || return "$?"
          if [[ $(jq length <<< "$installed") == 0 ]]; then
            instawow -v -p phoenix-retail install "$addon" || return "$?"
          fi
        done < <(jq -r '.[]' ${./wow-addons.json})
      }
      ${builtins.readFile ./forever-sync.sh}
      if [[ "''${1:-}" == sync ]]; then
        wow_sync
      elif [[ "''${1:-}" == sync-forever ]]; then
        wow_sync_forever ${./wow-addons.json}
      elif [[ "''${1:-}" == scheduled-update ]]; then
        wow_manifest=${./wow-addons.json}
        ${builtins.readFile ./scheduled-update.sh}
      else
        exec instawow -v -p phoenix-retail "$@"
      fi
    '';
  };
in
{
  options.phoenix.wow = {
    retailAddonDirectory = lib.mkOption {
      type = lib.types.strMatching "/.+";
      default = "${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns";
      description = "Existing WoW Retail AddOns directory shared by toolkit deployment and instawow; never created by toolkit activation.";
    };
    foreverAddonDirectory = lib.mkOption {
      type = lib.types.strMatching "/.+";
      default = "${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_forever_/Interface/AddOns";
      description = "Existing WoW Forever AddOns directory for its separate InstaWoW profile.";
    };
    toolkit.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Deploy Phoenix WoW Toolkit; disabling removes only its recognized Nix-store symlink on activation.";
    };
  };
  config = lib.mkIf (config.phoenix.target == "metal-4tb") {
    system.build.phoenixWowToolkit = toolkit;
    nixpkgs.config.allowUnfreePackages = [ "wowup-cf" ];
    environment.systemPackages = [
      pkgs.wowup-cf
      instawow
      wowAddons
      tsmApp
      tsmForeground
      battleNet
    ];
    home-manager.users.${user.name} = { lib, ... }: {
      # Native Wine Wayland windows lack Caelestia's steam_app_default game tag.
      phoenix.gameWindows.extraClasses = [ "wow.exe" ];
      home.activation.wowToolkit = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        run ${toolkitDeploy}/bin/phoenix-wow-toolkit-deploy ${lib.escapeShellArg addonDir} ${lib.optionalString config.phoenix.wow.toolkit.enable "${toolkit}/PhoenixWoWToolkit"}
      '';
      home.activation.tsmNotifications = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        ${pkgs.python3}/bin/python3 ${./disable-tsm-notifications.py} "${user.homeDirectory}/.config/tsm-app/config.toml"
      '';
      # Preserve the existing Lutris entry and its ID; HM backs up the old file.
      xdg.dataFile."applications/net.lutris.battlenet-1.desktop".source =
        "${battleNetDesktop}/share/applications/net.lutris.battlenet-1.desktop";
      xdg.dataFile."applications/wowup-cf.desktop".source = "${wowUpDesktop}/wowup-cf.desktop";
      systemd.user.services.wow-tsm-session = {
        Unit.Description = "TSM companion for the Battle.net / WoW session";
        Service = {
          ExecStart = "${tsmSession}/bin/wow-tsm-session";
          KillMode = "control-group";
          TimeoutStopSec = 15;
        };
      };
      # Native OAuth configuration also rewrites the selected profile. Reuse the
      # existing writer to migrate the old store symlink without touching its DB.
      home.activation.wowProfile = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        ${settingsWriter} reassert ${profileBaseline} "${user.homeDirectory}/.config/instawow/profiles/phoenix-retail/config.json" object
        ${settingsWriter} reassert ${foreverProfileBaseline} "${user.homeDirectory}/.config/instawow/profiles/phoenix-forever/config.json" object
      '';
      systemd.user.services.wow-addons-update = {
        Unit = {
          Description = "Update managed WoW Retail and Forever add-ons";
          OnFailure = [ "wow-addons-update-notify.service" ];
        };
        Service = {
          Type = "oneshot";
          ExecStart = "${wowAddons}/bin/wow-addons scheduled-update";
          TimeoutStartSec = "2h";
          UMask = "0077";
          StandardOutput = "journal";
          StandardError = "journal";
          NoNewPrivileges = true;
          PrivateTmp = true;
          ProtectSystem = "strict";
          ProtectHome = "tmpfs";
          CacheDirectory = "instawow";
          CacheDirectoryMode = "0700";
          StateDirectory = "instawow phoenix-wow";
          StateDirectoryMode = "0700";
          BindPaths = [
            "\"${addonDir}\""
            "\"${foreverAddonDir}\""
            "%h/.config/instawow"
            "%h/.cache/instawow"
            "%h/.local/state/instawow"
            "%h/.local/state/phoenix-wow"
          ];
          ReadWritePaths = [
            "\"${addonDir}\""
            "\"${foreverAddonDir}\""
            "%h/.config/instawow"
            "%h/.cache/instawow"
            "%h/.local/state/instawow"
            "%h/.local/state/phoenix-wow"
          ];
        };
      };
      systemd.user.services.wow-addons-update-notify = {
        Unit.Description = "Notify about a terminal WoW add-on update failure";
        Service = {
          Type = "oneshot";
          ExecStart = ''${pkgs.libnotify}/bin/notify-send --app-name="WoW add-ons" --urgency=normal "WoW add-on update failed" "See journalctl --user -u wow-addons-update.service for details."'';
          NoNewPrivileges = true;
          ProtectSystem = "strict";
        };
      };
      systemd.user.timers.wow-addons-update = {
        Unit.Description = "Daily WoW add-on updates at 05:00 Berlin time";
        Timer = {
          OnCalendar = "*-*-* 05:00:00 Europe/Berlin";
          Persistent = true;
          AccuracySec = "1min";
        };
        Install.WantedBy = [ "timers.target" ];
      };
    };
  };
}
