{
  codexCliPackage,
  inputs,
  user,
  ...
}:

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

  home-manager.users.${user.name} = {
    xdg.configFile."codex-desktop/electron-flags.conf".text = ''
      --blink-settings=middleClickPasteAllowed=false
    '';

    # Keep the NixOS Ozone opt-in local to ChatGPT Community. Its pinned launcher
    # otherwise defaults CODEX_OZONE_PLATFORM to x11, then lets this variable
    # select Wayland before that fallback is appended.
    xdg.desktopEntries.codex-desktop = {
      name = "ChatGPT Community (Native)";
      comment = "Direct host access; use ChatGPT Community (Sandboxed) for contained engineering";
      exec = "env NIXOS_OZONE_WL=1 BAMF_DESKTOP_FILE_HINT=/run/current-system/sw/share/applications/codex-desktop.desktop CHROME_DESKTOP=codex-desktop.desktop codex-desktop %u";
      icon = "codex-desktop";
      terminal = false;
      type = "Application";
      categories = [ "Development" ];
      mimeType = [
        "x-scheme-handler/codex"
        "x-scheme-handler/codex-browser-sidebar"
      ];
      startupNotify = true;
      settings = {
        Keywords = "codex;openai;ai;coding;";
        StartupWMClass = "codex-desktop";
      };
      actions."new-window" = {
        name = "New Window";
        exec = "env NIXOS_OZONE_WL=1 BAMF_DESKTOP_FILE_HINT=/run/current-system/sw/share/applications/codex-desktop.desktop CHROME_DESKTOP=codex-desktop.desktop CODEX_MULTI_LAUNCH=1 codex-desktop --new-instance";
      };
    };
  };

  environment.sessionVariables.CODEX_LINUX_DISABLE_USAGE_REPORTING = "1";
}
