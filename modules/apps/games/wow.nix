{ config, lib, pkgs, user, ... }:
let
  addonDir = "${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns";
  # Backport the enum-only metadata fix from instawow v7.2.0. WindTools
  # includes Forever metadata alongside Retail; 7.0 rejects the entire release.
  instawow = pkgs.instawow.overrideAttrs (old: {
    postPatch = (old.postPatch or "") + ''
      substituteInPlace src/instawow/_sources/github.py \
        --replace-fail "    VanillaClassic = 'classic'" "    ForeverClassic = 'forever'"$'\n'"    VanillaClassic = 'classic'"
    '';
  });
  wowAddons = pkgs.writeShellApplication {
    name = "wow-addons";
    runtimeInputs = [ instawow pkgs.util-linux pkgs.jq ];
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
  environment.systemPackages = [ instawow wowAddons ];
  home-manager.users.${user.name} = {
    xdg.configFile."instawow/profiles/phoenix-retail/config.json".text = builtins.toJSON {
      profile = "phoenix-retail";
      addon_dir = addonDir;
    };
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
        ReadWritePaths = [ "\"${addonDir}\"" "%h/.config/instawow" "%h/.cache" "%h/.local/state" ];
        ReadOnlyPaths = [ "\"${user.homeDirectory}/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF\"" ];
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
