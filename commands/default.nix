{
  pkgs,
  user,
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
      phoenixTarget
    ];
    text = ''
      export PHOENIX_REPO_ROOT="''${PHOENIX_REPO_ROOT:-${user.repoDirectory}}"
      exec bash "$PHOENIX_REPO_ROOT/commands/phoenix-rebuild" "$@"
    '';
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
      pkgs.hyprland
      pkgs.kdePackages.qttools
    ];
    text = builtins.readFile ./phoenix-logout;
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
