{ inputs, pkgs, user, ... }:

let
  system = pkgs.stdenv.hostPlatform.system;
in
{
  imports = [
    inputs.codex-desktop-linux.nixosModules.default
  ];

  nixpkgs.config.allowUnfreePackages = [
    "codex-desktop"
  ];

  programs.codexDesktopLinux = {
    enable = true;
    cliPackage = inputs.codex.packages.${system}.default;
  };

  home-manager.users.${user.name}.xdg.configFile."codex-desktop/electron-flags.conf".text = ''
    --blink-settings=middleClickPasteAllowed=false
  '';

  environment.sessionVariables.CODEX_LINUX_DISABLE_USAGE_REPORTING = "1";
}
