{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.phoenix.kando;
  hypr = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system}.hyprland;
  directory = "${config.xdg.configHome}/phoenix-kando/kando";
  writer = import ./mutable-json-settings.nix { inherit pkgs; };
  # Exact 2.3 schemas: top-level settings; --config-dir is silently ignored.
  settings = {
    version = "2.3.0";
    showIntroductionDialog = false;
    enableVersionCheck = false;
    enableDarkModeForMenuThemes = true;
    enableMarkingMode = true;
    enableTurboMode = true;
    fixedStrokeLength = 0;
    keepInputFocus = false;
    warpMouse = true;
    enableAchievements = false;
    enableAchievementNotifications = false;
  };
  item = name: icon: angle: type: data: {
    inherit
      name
      icon
      angle
      type
      data
      ;
    iconTheme = "material-symbols-rounded";
  };
  command =
    name: icon: angle: text:
    item name icon angle "command" {
      # Kando's private XDG config must not become a launched app's profile.
      # Upstream isolation uses a separate user unit so restarting Kando also
      # does not kill applications launched through its menu.
      command = "${pkgs.coreutils}/bin/env XDG_CONFIG_HOME=${lib.escapeShellArg config.xdg.configHome} ${text}";
      detached = true;
      isolated = true;
      delayed = true;
    };
  hotkey =
    name: icon: angle: key:
    item name icon angle "hotkey" {
      hotkey = key;
      delayed = true;
      inhibitShortcuts = false;
    };
  copy = hotkey "Copy" "content_copy" 0 "Control+c";
  paste = hotkey "Paste" "content_paste" 180 "Control+v";
  menu =
    name: id: conditions: children:
    {
      shortcutID = id;
      shortcut = "";
      centered = false;
      anchored = false;
      hoverMode = false;
      root = {
        inherit name children;
        type = "submenu";
        icon = "apps";
        iconTheme = "material-symbols-rounded";
      };
    }
    // lib.optionalAttrs (conditions != null) { inherit conditions; };
  menus = {
    version = "2.3.0";
    collections = [ ];
    menus = [
      (menu "Global" "global-menu" null [
        (command "Launcher" "search" 0
          "${hypr}/bin/hyprctl dispatch \"hl.dsp.global('caelestia:launcher')\""
        )
        (command "Terminal" "terminal" 45 "${pkgs.foot}/bin/foot")
        (command "Next workspace" "arrow_forward" 90
          "${hypr}/bin/hyprctl dispatch \"hl.dsp.focus({workspace='+1'})\""
        )
        (command "Files" "folder" 180 "${pkgs.xdg-utils}/bin/xdg-open \"${config.home.homeDirectory}\"")
        (command "Audio" "volume_up" 225 "${pkgs.pwvucontrol}/bin/pwvucontrol")
        (command "Previous workspace" "arrow_back" 270
          "${hypr}/bin/hyprctl dispatch \"hl.dsp.focus({workspace='-1'})\""
        )
      ])
      (menu "Context" "contextual-menu" null [
        copy
        paste
      ])
      (menu "Firefox" "contextual-menu" { appName = "/^firefox$/i"; } [
        copy
        (hotkey "New tab" "add" 45 "Control+t")
        (hotkey "Forward" "arrow_forward" 90 "Alt+Right")
        paste
        (hotkey "Reload" "refresh" 225 "Control+r")
        (hotkey "Back" "arrow_back" 270 "Alt+Left")
      ])
      (menu "Codex" "contextual-menu" { appName = "/^codex-desktop(-sandboxed)?$/"; } [
        copy
        (hotkey "Select all" "select_all" 90 "Control+a")
        paste
      ])
    ];
  };
  configBaseline = pkgs.writeText "kando-config-baseline.json" (builtins.toJSON settings);
  menusBaseline = pkgs.writeText "kando-menus-baseline.json" (builtins.toJSON menus);
  wrapped = pkgs.symlinkJoin {
    name = "kando-phoenix-${pkgs.kando.version}";
    paths = [ pkgs.kando ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      rm "$out/bin/kando"
      makeWrapper ${pkgs.kando}/bin/kando "$out/bin/kando" \
        --set XDG_CONFIG_HOME ${lib.escapeShellArg "${config.xdg.configHome}/phoenix-kando"} \
        --prefix PATH : ${lib.makeBinPath [ pkgs.systemd ]} \
        --add-flags --ozone-platform=wayland
      rm "$out/share/applications/kando.desktop"
      cp ${pkgs.kando}/share/applications/kando.desktop "$out/share/applications/kando.desktop"
      chmod u+w "$out/share/applications/kando.desktop"
      substituteInPlace "$out/share/applications/kando.desktop" \
        --replace-fail 'Exec=kando %U' "Exec=$out/bin/kando %U"
    '';
  };
  lua = ''
    hl.bind("mouse:275", hl.dsp.global("menu.kando.Kando:global-menu"))
    hl.bind("mouse:276", hl.dsp.global("menu.kando.Kando:contextual-menu"))
    hl.window_rule({
      name = "phoenix-kando",
      match = { class = "^menu[.]kando[.]Kando$", title = "^Kando Menu$" },
      no_blur = true, opaque = true, move = {0, 0}, size = {"100%", "100%"},
      rounding = 0, border_size = 0, no_anim = true, float = true, pin = true,
    })
  '';
in
{
  options.phoenix.kando.enable = lib.mkEnableOption "Phoenix's contextual Kando menus";
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = pkgs.kando.version == "2.3.0";
        message = "Review Kando schemas and adapter before upgrading Phoenix's pinned 2.3 integration.";
      }
    ];
    _module.args.phoenixKandoHyprLua = lua;
    home.packages = [ wrapped ];
    xdg.dataFile."kando/config.json.nix-baseline".source = configBaseline;
    xdg.dataFile."kando/menus.json.nix-baseline".source = menusBaseline;
    home.activation.kandoSettings = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      mode=reassert
      if [ "''${PHOENIX_PRESERVE_MUTABLE_BASELINES:-0}" = 1 ]; then mode=preserve; fi
      run ${writer} "$mode" ${configBaseline} ${lib.escapeShellArg "${directory}/config.json"} object
      run ${writer} "$mode" ${menusBaseline} ${lib.escapeShellArg "${directory}/menus.json"} object
    '';
    # Requested restart semantics: only these two declarations reset at every
    # start, including login. Promote GUI experiments before restarting Kando.
    # Chromium caches, achievements and other app state are never reconciled.
    systemd.user.services.kando = {
      Unit = {
        Description = "Phoenix contextual radial menus";
        PartOf = [ "hyprland-session.target" ];
        After = [ "hyprland-session.target" ];
      };
      Service = {
        ExecStartPre = [
          "${writer} reassert ${configBaseline} ${directory}/config.json object"
          "${writer} reassert ${menusBaseline} ${directory}/menus.json object"
        ];
        ExecStart = "${wrapped}/bin/kando";
        Restart = "on-failure";
        RestartSec = 2;
      };
      Install.WantedBy = [ "hyprland-session.target" ];
    };
  };
}
