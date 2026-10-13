{
  config,
  inputs,
  lib,
  pkgs,
  phoenixBlankCommand,
  ...
}:
let
  cfg = config.phoenix.kando;
  hypr = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system}.hyprland;
  directory = "${config.xdg.configHome}/phoenix-kando/kando";
  writer = import ../mutable-json-settings/default.nix { inherit pkgs; };
  # Exact 2.3 schemas: top-level settings; --config-dir is silently ignored.
  settings = {
    version = "2.3.0";
    showIntroductionDialog = false;
    enableVersionCheck = false;
    enableDarkModeForMenuThemes = true;
    enableMarkingMode = true;
    enableTurboMode = true;
    # Select at the default 100px item radius (50px stroke + 50px dead zone).
    fixedStrokeLength = 50;
    hoverModeNeedsConfirmation = false;
    keepInputFocus = false;
    warpMouse = false;
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
  copyAt = angle: hotkey "Copy" "content_copy" angle "ControlLeft+KeyC";
  copy = copyAt 0;
  fullscreen = hotkey "Fullscreen" "fullscreen" 0 "F11";
  sidebar = hotkey "Toggle sidebar" "side_navigation" 315 "ControlLeft+ShiftLeft+KeyS";
  paste = hotkey "Paste" "content_paste" 180 "ControlLeft+KeyV";
  menu =
    name: id: conditions: children:
    {
      shortcutID = id;
      shortcut = "";
      centered = false;
      anchored = false;
      # Hover gestures execute final actions while the side button is held.
      hoverMode = true;
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
        (command "Overview" "view_quilt" 0
          ''${hypr}/bin/hyprctl eval 'hl.plugin.hyprexpo.expo("on all")' ''
        )
        (command "Terminal" "terminal" 45 "${pkgs.foot}/bin/foot")
        (command "Next workspace" "arrow_forward" 90 "${hypr}/bin/hyprctl eval 'phoenix_workspace_step(1)'")
        (command "Blank screen" "bedtime" 135 phoenixBlankCommand)
        (command "Close window" "close" 180 "${hypr}/bin/hyprctl dispatch 'hl.dsp.window.close()'")
        (command "Audio" "volume_up" 225 "${pkgs.pwvucontrol}/bin/pwvucontrol")
        (command "Previous workspace" "arrow_back" 270
          "${hypr}/bin/hyprctl eval 'phoenix_workspace_step(-1)'"
        )
        (command "Files" "folder" 315 "${pkgs.xdg-utils}/bin/xdg-open \"${config.home.homeDirectory}\"")
      ])
      (menu "Context" "contextual-menu" null [
        copy
        paste
      ])
      (menu "Firefox" "contextual-menu" { appName = "/^firefox$/i"; } [
        fullscreen
        (hotkey "New tab" "add" 45 "ControlLeft+KeyT")
        (hotkey "Forward" "arrow_forward" 90 "AltLeft+ArrowRight")
        (copyAt 135)
        paste
        (hotkey "Reload" "refresh" 225 "ControlLeft+KeyR")
        (hotkey "Back" "arrow_back" 270 "AltLeft+ArrowLeft")
        sidebar
      ])
      (menu "ChatGPT" "contextual-menu" { appName = "/^codex-desktop(-sandboxed)?$/"; } [
        fullscreen
        (copyAt 45)
        (hotkey "Select all" "select_all" 90 "ControlLeft+KeyA")
        paste
        sidebar
      ])
    ];
  };
  configBaseline = pkgs.writeText "kando-config-baseline.json" (builtins.toJSON settings);
  menusBaseline = pkgs.writeText "kando-menus-baseline.json" (builtins.toJSON menus);
  # Stock 2.3 discards GlobalShortcuts.Deactivated. Hyprland already sends
  # both edges; this narrow patch feeds that lifetime into Kando's existing
  # PointerInput. Unlike uinput/click adapters, no synthetic input escapes the
  # menu or requires another privileged device owner. Remove when upstream
  # supports portal hold/release; re-review at the version assertion below.
  heldKando = pkgs.kando.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./shortcut-hold.patch ];
  });
  wrapped = pkgs.symlinkJoin {
    name = "kando-phoenix-${pkgs.kando.version}";
    paths = [ heldKando ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      rm "$out/bin/kando"
      makeWrapper ${heldKando}/bin/kando "$out/bin/kando" \
        --set XDG_CONFIG_HOME ${lib.escapeShellArg "${config.xdg.configHome}/phoenix-kando"} \
        --set KANDO_HOLD_SHORTCUT_IDS global-menu,contextual-menu \
        --prefix PATH : ${lib.makeBinPath [ pkgs.systemd ]} \
        --add-flags --ozone-platform=wayland
      rm "$out/share/applications/kando.desktop"
      cp ${heldKando}/share/applications/kando.desktop "$out/share/applications/kando.desktop"
      chmod u+w "$out/share/applications/kando.desktop"
      substituteInPlace "$out/share/applications/kando.desktop" \
        --replace-fail 'Exec=kando %U' "Exec=$out/bin/kando %U"
    '';
  };
  lua = ''
    -- Held keys avoid Hyprland retaining pointer focus on the underlying app.
    -- transparent prevents __lua key-shadowing from suppressing portal release.
    hl.bind("F23", hl.dsp.global("menu.kando.Kando:global-menu"), { transparent = true })
    hl.bind("F24", hl.dsp.global("menu.kando.Kando:contextual-menu"), { transparent = true })
    hl.window_rule({
      name = "phoenix-kando",
      match = { class = "^menu[.]kando[.]Kando$", title = "^Kando Menu$" },
      no_blur = true, opaque = true, move = {0, 0}, size = {"100%", "100%"},
      rounding = 0, border_size = 0, no_anim = true, float = true, pin = true, stay_focused = true,
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
    home.activation.kandoSettings = lib.hm.dag.entryBetween [ "reloadSystemd" ] [ "writeBoundary" ] ''
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
        X-Restart-Triggers = [
          configBaseline
          menusBaseline
        ];
        PartOf = [ "hyprland-session.target" ];
        After = [ "hyprland-session.target" ];
      };
      Service = {
        ExecStartPre = [
          "${writer} reassert ${configBaseline} ${directory}/config.json object"
          "${writer} reassert ${menusBaseline} ${directory}/menus.json object"
        ];
        # A recognized no-op startup action suppresses 2.3's default editor window.
        ExecStart = "${wrapped}/bin/kando --close-menu";
        Restart = "on-failure";
        RestartSec = 2;
      };
      Install.WantedBy = [ "hyprland-session.target" ];
    };
  };
}
