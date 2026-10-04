# Run with `nix build --impure --file tests/idle-command.nix --no-link`.
let
  flake = builtins.getFlake ("git+file://" + toString ../.);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../config/user.nix { inherit (pkgs) lib; };
  home = flake.nixosConfigurations.metal.config.home-manager.users.${user.name};
  shellPackage = home.programs.caelestia.package;
  baselineFile = home.xdg.dataFile."caelestia/shell.json.nix-baseline".source;
  shellSource = flake.inputs.caelestia-shell.outPath;
  quickshellSource = flake.inputs.caelestia-shell.inputs.quickshell.outPath;
  cliSource = flake.inputs.caelestia-shell.inputs.caelestia-cli.outPath;
in
assert pkgs.lib.any (package: (package.name or "") == "blank") home.home.packages;
pkgs.runCommand "phoenix-idle-command-check"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.nodejs
      pkgs.patch
    ];
  }
  ''
    python3 ${./idle-command.py} ${shellSource} ${quickshellSource} ${cliSource} ${../patches/caelestia-idle-command.patch} ${baselineFile} ${shellPackage}
    touch "$out"
  ''
