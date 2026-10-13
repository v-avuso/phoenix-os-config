# Run with `nix build --impure --file home/idle/tests/idle-command.nix --no-link`.
let
  flake = builtins.getFlake ("git+file://" + toString ../../..);
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  user = import ../../../config/user.nix { inherit (pkgs) lib; };
  home = flake.nixosConfigurations.metal.config.home-manager.users.${user.name};
  shellPackage = home.programs.caelestia.package;
  blankPackage = pkgs.lib.findFirst (
    package: (package.name or "") == "blank"
  ) null home.home.packages;
  baselineFile = home.xdg.dataFile."caelestia/shell.json.nix-baseline".source;
  shellSource = flake.inputs.caelestia-shell.outPath;
  quickshellSource = flake.inputs.caelestia-shell.inputs.quickshell.outPath;
  hyprlandSource = flake.inputs.nixpkgs-unstable.legacyPackages.x86_64-linux.hyprland.src;
  cliSource = flake.inputs.caelestia-shell.inputs.caelestia-cli.outPath;
in
assert home.programs.caelestia.systemd.enable;
assert home.programs.caelestia.systemd.target == "hyprland-session.target";
assert
  pkgs.lib.toList home.systemd.user.services.caelestia.Service.ExecStart
  == [ "${shellPackage}/bin/caelestia-shell" ];
assert pkgs.lib.any (package: (package.name or "") == "blank") home.home.packages;
pkgs.runCommand "phoenix-idle-command-check"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.nodejs
      pkgs.patch
      pkgs.stdenv.cc
    ];
  }
  ''
    python3 ${./idle-command.py} ${shellSource} ${quickshellSource} ${cliSource} ${../../../patches/caelestia-idle-command.patch} ${baselineFile} ${shellPackage} ${blankPackage}/bin/blank ${hyprlandSource}
    touch "$out"
  ''
