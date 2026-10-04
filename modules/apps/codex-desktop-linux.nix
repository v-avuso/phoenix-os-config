{
  config,
  codexCliPackage,
  phoenixAgentHistoryConfig,
  inputs,
  pkgs,
  user,
  ...
}:

let
  upstream = inputs.codex-desktop-linux;
  cfg = config.programs.codexDesktopLinux;
  linuxFeatures = import (upstream + "/nix/linux-features.nix") { inherit (pkgs) lib; };
  base = upstream.packages.${pkgs.stdenv.hostPlatform.system}.codex-desktop.override {
    enableComputerUseUi = cfg.computerUseUi.enable;
    linuxFeatureIds = linuxFeatures.normalize (
      cfg.linuxFeatures ++ pkgs.lib.optional cfg.remoteMobileControl.enable "remote-mobile-control"
    );
  };
  # Session restoration launches the executable directly, bypassing desktop
  # entry environment. Use upstream's live-Wayland detection for every entry
  # point; explicit user flags/settings still win and X11 sessions still work.
  nativeDesktop = pkgs.symlinkJoin {
    name = "${base.name}-native-wayland";
    paths = [ base ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      rm "$out/bin/codex-desktop"
      makeWrapper "${pkgs.python3}/bin/python3" "$out/bin/codex-desktop" \
        --add-flags "-I ${../development/ai/agent/history-runtime.py} ${phoenixAgentHistoryConfig} -- ${base}/bin/codex-desktop" \
        --set-default CODEX_OZONE_PLATFORM auto
      desktopFile="$out/share/applications/codex-desktop.desktop"
      target="$(readlink -f "$desktopFile")"
      rm "$desktopFile"
      substitute "$target" "$desktopFile" \
        --replace-fail "${base}/bin/codex-desktop" "$out/bin/codex-desktop"
    '';
    inherit (base) meta;
    passthru = base.passthru or { };
  };
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
    package = nativeDesktop;
    cliPackage = codexCliPackage;
  };

  home-manager.users.${user.name} = {
    xdg.configFile."codex-desktop/electron-flags.conf".text = ''
      --blink-settings=middleClickPasteAllowed=false
    '';

    # The package also selects Wayland for direct/session-restoration launches.
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
