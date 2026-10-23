{
  pkgs,
  user,
  nixosRebuild ? pkgs.nixos-rebuild-ng,
  includeDesktopCommands ? true,
  hyprlandPackage ? pkgs.hyprland,
  defaultTarget ? null,
  targetProbe ? "${pkgs.util-linux}/bin/findmnt",
}:

let
  phoenixTarget = import ./target.nix { inherit pkgs defaultTarget; rootProbe = targetProbe; };

  phoenixSource = pkgs.writeScriptBin "phoenix-source" (
    builtins.replaceStrings [ "#!/usr/bin/env python3" ]
      [ "#!${pkgs.python3}/bin/python3" ] (builtins.readFile ./phoenix-source)
  );

  phoenixRebuild = pkgs.writeShellApplication {
    name = "phoenix-rebuild";
    runtimeInputs = [
      pkgs.git
      phoenixSource
      pkgs.bash
      pkgs.nix
      pkgs.coreutils
      nixosRebuild
      phoenixTarget
    ];
    text = ''
      if [ -z "''${PHOENIX_REPO_ROOT:-}" ]; then
        export PHOENIX_REPO_ROOT=${pkgs.lib.escapeShellArg user.repoDirectory}
      fi
    '' + builtins.readFile ./phoenix-rebuild;
  };

  phoenixGc = pkgs.writeShellApplication {
    name = "phoenix-gc";
    runtimeInputs = [ pkgs.nix pkgs.sudo ];
    text = builtins.readFile ./phoenix-gc;
  };

  rebuildAction =
    name: action:
    pkgs.writeShellApplication {
      inherit name;
      runtimeInputs = [ phoenixRebuild ];
      text = ''exec phoenix-rebuild ${action} "$@"'';
    };

  insomnia = pkgs.writeShellApplication {
    name = "insomnia";
    runtimeInputs = [ pkgs.systemd ];
    text = builtins.readFile ./insomnia;
  };

  phoenixLogout = pkgs.writeShellApplication {
    name = "phoenix-logout";
    runtimeInputs = [
      hyprlandPackage
      pkgs.hyprshutdown
      pkgs.kdePackages.qttools
    ];
    text = ''
      phoenix_hyprshutdown=${pkgs.lib.escapeShellArg "${pkgs.hyprshutdown}/bin/hyprshutdown"}
    '' + builtins.readFile ./phoenix-logout;
  };
in
pkgs.symlinkJoin {
  name = "phoenix-user-commands";
  paths = [
    phoenixTarget
    phoenixRebuild
    phoenixGc
    (rebuildAction "phoenix-switch" "switch")
    (rebuildAction "phoenix-test" "test")
    (rebuildAction "phoenix-boot" "boot")
    (rebuildAction "phoenix-build" "build")
    (rebuildAction "phoenix-dry-build" "dry-build")
  ] ++ pkgs.lib.optionals includeDesktopCommands [ insomnia phoenixLogout ];
}
