{
  config,
  lib,
  pkgs,
  user,
  ...
}:
let
  addonDir = "${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns";
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
    ];
    text = ''
      mkdir -p "''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow"
      exec 9>"''${XDG_STATE_HOME:-$HOME/.local/state}/phoenix-wow/lock"
      flock -w 3600 9
      if [[ "''${1:-}" == sync ]]; then
        while IFS= read -r addon; do
          installed=$(instawow -v -p phoenix-retail list --format json "$addon")
          if [[ $(jq length <<< "$installed") == 0 ]]; then
            instawow -v -p phoenix-retail install "$addon"
          fi
        done < <(jq -r '.[]' ${./wow-addons.json})
      else
        exec instawow -v -p phoenix-retail "$@"
      fi
    '';
  };
in
lib.mkIf (config.phoenix.target == "metal-4tb") {
  environment.systemPackages = [
    instawow
    wowAddons
  ];
  home-manager.users.${user.name} = { lib, ... }: {
    # Native OAuth configuration also rewrites the selected profile. Reuse the
    # existing writer to migrate the old store symlink without touching its DB.
    home.activation.wowProfile = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      ${settingsWriter} reassert ${profileBaseline} "${user.homeDirectory}/.config/instawow/profiles/phoenix-retail/config.json" object
    '';
    systemd.user.services.wow-addons-update = {
      Unit.Description = "Update managed WoW Retail add-ons";
      Service = {
        Type = "oneshot";
        ExecStartPre = "${wowAddons}/bin/wow-addons sync";
        ExecStart = "${wowAddons}/bin/wow-addons update";
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
    systemd.user.timers.wow-addons-update = {
      Unit.Description = "Daily WoW add-on updates at 09:00 Berlin time";
      Timer = {
        OnCalendar = "*-*-* 09:00:00 Europe/Berlin";
        Persistent = true;
        AccuracySec = "1min";
      };
      Install.WantedBy = [ "timers.target" ];
    };
  };
}
