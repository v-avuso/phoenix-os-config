{
  config,
  codexCliPackage,
  phoenixAgentHistoryConfig,
  phoenixAgentGuiStateConfig,
  inputs,
  pkgs,
  user,
  ...
}:

let
  upstream = inputs.codex-desktop-linux;
  cfg = config.programs.codexDesktopLinux;
  updatePolicy = builtins.fromJSON (builtins.readFile ../../config/updates.json);
  desktopHold = updatePolicy.holds.codex-desktop or null;
  linuxFeatures = import (upstream + "/nix/linux-features.nix") { inherit (pkgs) lib; };
  base = upstream.packages.${pkgs.stdenv.hostPlatform.system}.codex-desktop.override {
    enableComputerUseUi = cfg.computerUseUi.enable;
    linuxFeatureIds = linuxFeatures.normalize (
      cfg.linuxFeatures ++ pkgs.lib.optional cfg.remoteMobileControl.enable "remote-mobile-control"
    );
  };
  sharedDesktop = if config.phoenix.agent.gui.sharedState.enable then base.overrideAttrs (old: {
    nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.asar ];
    postInstall = (old.postInstall or "") + ''
      asar extract "$out/opt/codex-desktop/resources/app.asar" phoenix-shared-app
      ${pkgs.python3}/bin/python3 -I ${../development/ai/agent/gui-control-patch.py} phoenix-shared-app/.vite/build
      bootstrap=phoenix-shared-app/.vite/build/early-bootstrap.js
      test -f "$bootstrap"
      { printf '%s\n' 'require(${builtins.toJSON (toString ../development/ai/agent/gui-control.cjs)});'; cat "$bootstrap"; } > phoenix-control.js
      mv phoenix-control.js "$bootstrap"
      asar pack phoenix-shared-app "$out/opt/codex-desktop/resources/app.asar" --unpack '*.node'
    '';
  }) else base;
  # Session restoration launches the executable directly, bypassing desktop
  # entry environment. Use upstream's live-Wayland detection for every entry
  # point; explicit user flags/settings still win and X11 sessions still work.
  nativeDesktop = pkgs.symlinkJoin {
    name = "${base.name}-native-wayland";
    paths = [ sharedDesktop ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      rm "$out/bin/codex-desktop"
      makeWrapper "${pkgs.python3}/bin/python3" "$out/bin/codex-desktop" \
        --add-flags "-I ${pkgs.lib.optionalString config.phoenix.agent.gui.sharedState.enable "${../development/ai/agent/gui-state.py} ${phoenixAgentGuiStateConfig} native -- ${pkgs.python3}/bin/python3 -I "}${../development/ai/agent/history-runtime.py} ${phoenixAgentHistoryConfig} -- ${sharedDesktop}/bin/codex-desktop" \
        --set-default CODEX_OZONE_PLATFORM auto
      desktopFile="$out/share/applications/codex-desktop.desktop"
      target="$(readlink -f "$desktopFile")"
      rm "$desktopFile"
      substitute "$target" "$desktopFile" \
        --replace-fail "${sharedDesktop}/bin/codex-desktop" "$out/bin/codex-desktop"
    '';
    inherit (base) meta;
    passthru = base.passthru or { };
  };
in
{
  # These independently reviewed sources include NixOS modules and containment
  # adapters. Hold their exact locks; never silently undo a deliberate downgrade.
  assertions = pkgs.lib.optional (desktopHold != null) {
    assertion = inputs.codex-desktop-linux.rev == desktopHold.pin.native
      && inputs.codex-desktop-sandbox.rev == desktopHold.pin.sandbox;
    message = "Community hold requires matching native and sandbox flake.lock revisions; see config/updates.json comments.";
  };
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
