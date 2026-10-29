{
  config,
  lib,
  pkgs,
  user,
  ...
}:
let
  addonDir = "${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns";
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
  profileBaseline = pkgs.writeText "instawow-retail-profile.json" (
    builtins.toJSON {
      profile = "phoenix-retail";
      addon_dir = addonDir;
    }
  );
  settingsWriter = import ../../../../home/mutable-json-settings { inherit pkgs; };
  click = pkgs.python3.pkgs.click.overridePythonAttrs {
    version = "8.4.1";
    src = pkgs.fetchPypi {
      pname = "click";
      version = "8.4.1";
      sha256 = "15iyipl8nbs5wn7byz9z9v3na041vvq4niag5p1l2syzxlrmd2wi";
    };
  };
  # Keep the system lock unchanged; use unpatched upstream until Nixpkgs catches up.
  instawow = pkgs.instawow.overrideAttrs (old: {
    version = "7.3.0";
    src = pkgs.fetchFromGitHub {
      owner = "layday";
      repo = "instawow";
      tag = "v7.3.0";
      hash = "sha256-NJDx1eUj+0Vq61lmR0y8R+H6sV8ajUFIpBrWzw2vATA=";
    };
    nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.python3.pkgs.versioningit ];
    # GitHub archives omit Git metadata; versioningit supports an explicit fallback.
    postPatch = ''
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
      if [[ "''${1:-}" == sync ]]; then
        wow_sync
      elif [[ "''${1:-}" == scheduled-update ]]; then
        ${builtins.readFile ./scheduled-update.sh}
      else
        exec instawow -v -p phoenix-retail "$@"
      fi
    '';
  };
in
lib.mkIf (config.phoenix.target == "metal-4tb") {
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
    # Preserve the existing Lutris entry and its ID; HM backs up the old file.
    xdg.desktopEntries."net.lutris.battlenet-1" = {
      name = "Battle.net";
      icon = "lutris_battlenet";
      exec = "${battleNet}/bin/wow-battlenet";
      categories = [ "Game" ];
      terminal = false;
    };
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
    '';
    systemd.user.services.wow-addons-update = {
      Unit = {
        Description = "Update managed WoW Retail add-ons";
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
          "%h/.config/instawow"
          "%h/.cache/instawow"
          "%h/.local/state/instawow"
          "%h/.local/state/phoenix-wow"
        ];
        ReadWritePaths = [
          "\"${addonDir}\""
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
}
