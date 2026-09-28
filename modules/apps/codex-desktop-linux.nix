{ codexCliPackage, inputs, user, ... }:

{
  imports = [
    inputs.codex-desktop-linux.nixosModules.default
  ];

  nixpkgs.config.allowUnfreePackages = [
    "codex-desktop"
  ];

  programs.codexDesktopLinux = {
    enable = true;
    cliPackage = codexCliPackage;
  };

  home-manager.users.${user.name}.xdg.configFile."codex-desktop/electron-flags.conf".text = ''
    --blink-settings=middleClickPasteAllowed=false
  '';

  environment.sessionVariables.CODEX_LINUX_DISABLE_USAGE_REPORTING = "1";
}
