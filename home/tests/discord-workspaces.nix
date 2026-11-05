# Exercise the deployed dotfiles and CLI configuration, not a copy of their rules.
{ flakeSource ? "git+file://${toString ../..}" }:
let
  flake = builtins.getFlake flakeSource;
  pkgs = flake.inputs.nixpkgs.legacyPackages.${builtins.currentSystem};
  user = import ../../config/user.nix { lib = pkgs.lib; };
  files = flake.nixosConfigurations.metal.config.home-manager.users.${user.name}.xdg.configFile;
in pkgs.runCommand "discord-workspaces" { nativeBuildInputs = [ pkgs.lua ]; } ''
  mkdir -p config/caelestia
  cp ${files."caelestia/cli.json".source} config/caelestia/cli.json
  export XDG_CONFIG_HOME="$PWD/config"
  lua ${./discord-workspaces.lua} ${files.hypr.source}
  touch "$out"
''
