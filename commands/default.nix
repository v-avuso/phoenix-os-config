{
  pkgs,
  user,
  nixosRebuild ? pkgs.nixos-rebuild-ng,
  hyprlandPackage ? pkgs.hyprland,
}:

let
  phoenixTarget = pkgs.writeShellApplication {
    name = "phoenix-target";
    runtimeInputs = [ pkgs.systemd ];
    text = builtins.readFile ./phoenix-target;
  };

  phoenixRebuild = pkgs.writeShellApplication {
    name = "phoenix-rebuild";
    runtimeInputs = [
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
    (rebuildAction "phoenix-switch" "switch")
    (rebuildAction "phoenix-test" "test")
    (rebuildAction "phoenix-boot" "boot")
    (rebuildAction "phoenix-build" "build")
    (rebuildAction "phoenix-dry-build" "dry-build")
    insomnia
    phoenixLogout
  ];
}
