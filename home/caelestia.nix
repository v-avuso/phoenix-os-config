{
  inputs,
  lib,
  pkgs,
  ...
}:

let
  dots = inputs.caelestia-dots;
  system = pkgs.stdenv.hostPlatform.system;
  hyprlandPackages = inputs.nixpkgs-unstable.legacyPackages.${system};
  desktopScale = import ../config/desktop-scale.nix;
  caelestiaShell = inputs.caelestia-shell.packages.${system}.with-cli.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ../patches/caelestia-u2f-lock.patch ];
    postPatch = (old.postPatch or "") + ''
      substituteInPlace assets/pam.d/u2f \
        --replace-fail '@PAM_U2F_SO@' '${pkgs.pam_u2f}/lib/security/pam_u2f.so'
    '';
  });

  caelestiaSettings = {
    # Caelestia's upstream idle defaults lock after 180 seconds. Phoenix
    # handles display blanking separately; do not lock or power off outputs.
    general.idle = {
      lockBeforeSleep = true;
      timeouts = [ ];
    };

    session.commands.logout = [
      "${hyprlandPackages.hyprland}/bin/hyprctl"
      "dispatch"
      "hl.dsp.exec_cmd('${pkgs.hyprshutdown}/bin/hyprshutdown --vt 1')"
    ];
  };

  caelestiaShellBaseline = pkgs.writeText "caelestia-shell-baseline.json" (
    builtins.toJSON caelestiaSettings + "\n"
  );
  caelestiaShellReassert = pkgs.writeShellScript "phoenix-caelestia-shell-reassert" ''
    set -euo pipefail

    target="$HOME/.config/caelestia/shell.json"
    baseline="${caelestiaShellBaseline}"
    ${pkgs.coreutils}/bin/mkdir -p "$HOME/.config/caelestia"

    if [ -L "$target" ] || [ ! -e "$target" ]; then
      tmp="$(${pkgs.coreutils}/bin/mktemp "$HOME/.config/caelestia/.shell.json.XXXXXXXX")"
      ${pkgs.coreutils}/bin/install -m 0644 "$baseline" "$tmp"
      ${pkgs.coreutils}/bin/mv -f "$tmp" "$target"
    elif [ -f "$target" ]; then
      if [ ! -w "$target" ]; then
        ${pkgs.coreutils}/bin/chmod u+rw "$target"
      fi
      runtime_json="$(${pkgs.coreutils}/bin/mktemp)"
      baseline_json="$(${pkgs.coreutils}/bin/mktemp)"
      trap '${pkgs.coreutils}/bin/rm -f "$runtime_json" "$baseline_json"' EXIT
      if ${pkgs.jq}/bin/jq -S . "$target" > "$runtime_json" 2>/dev/null \
        && ${pkgs.jq}/bin/jq -S . "$baseline" > "$baseline_json" \
        && ${pkgs.diffutils}/bin/cmp -s "$runtime_json" "$baseline_json"; then
        :
      else
        ${pkgs.coreutils}/bin/cat "$baseline" > "$target"
      fi
    else
      echo "Caelestia shell settings path is not a regular file: $target" >&2
      exit 1
    fi
  '';
  # The upstream Arch-oriented autostart uses two FHS executable paths.
  # Substitute only those paths; all ordinary commands are provided on PATH.
  caelestiaDots = pkgs.stdenvNoCC.mkDerivation {
    pname = "caelestia-dots-phoenix";
    version = inputs.caelestia-dots.lastModifiedDate or "locked";
    src = dots;
    dontBuild = true;

    postPatch = ''
      substituteInPlace hypr/hyprland/execs.lua \
        --replace-fail '"/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"' '"${pkgs.polkit_gnome}/libexec/polkit-gnome-authentication-agent-1"' \
        --replace-fail '"/usr/lib/geoclue-2.0/demos/agent"' '"${pkgs.geoclue2-with-demo-agent}/libexec/geoclue-2.0/demos/agent"' \
        --replace-fail 'hl.exec_cmd("caelestia shell -d")' 'hl.exec_cmd("${pkgs.dbus}/bin/dbus-update-activation-environment --systemd DISPLAY HYPRLAND_INSTANCE_SIGNATURE WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE && ${pkgs.systemd}/bin/systemctl --user stop hyprland-session.target && ${pkgs.systemd}/bin/systemctl --user start hyprland-session.target && caelestia shell -d")'
    '';

    installPhase = ''
      mkdir -p "$out"
      cp -r . "$out/"
    '';
  };

  hyprVars = {
    # Nixpkgs' Sweet cursor theme is case-sensitive; upstream's lowercase
    # default otherwise fails to identify the installed theme.
    cursorTheme = "Sweet-cursors";
  };

  toLua =
    value:
    if builtins.isString value then
      builtins.toJSON value
    else if builtins.isBool value then
      (if value then "true" else "false")
    else if builtins.isInt value || builtins.isFloat value then
      toString value
    else if builtins.isList value then
      "{ " + lib.concatStringsSep ", " (map toLua value) + " }"
    else if builtins.isAttrs value then
      "{\n"
      + lib.concatStringsSep "\n" (
        lib.mapAttrsToList (name: item: "  [${builtins.toJSON name}] = ${toLua item},") value
      )
      + "\n}"
    else
      throw "Unsupported value in Phoenix Caelestia Lua variables";

  renderLuaTable = attrs: toLua attrs;

  hyprUser = ''
    hl.monitor({
      output = "DP-1",
      mode = "3840x2160@144",
      position = "0x0",
      scale = ${toString desktopScale},
    })

    hl.monitor({
      output = "HDMI-A-2",
      mode = "3840x2160@240",
      position = "2400x0",
      scale = ${toString desktopScale},
    })

    hl.monitor({
      output = "DP-2",
      mode = "3840x2160@144.05",
      position = "4800x0",
      scale = ${toString desktopScale},
    })

    -- Phoenix-specific SDDM + NVIDIA adaptation for Caelestia issue #1754
    -- (https://github.com/caelestia-dots/shell/issues/1754):
    -- Session.Terminate() tears down start-hyprland with the session scope. Use
    -- Hyprland's graceful shutdown utility and return to SDDM's actual greeter VT1.
    -- Remove if Phoenix changes display manager or upstream logout behavior is fixed.
    hl.config({
      xwayland = {
        force_zero_scaling = true,
      },
    })
  '';

  caelestiaFirefoxChrome = builtins.readFile (dots + "/firefox/userChrome.css");
  phoenixFirefoxChrome = "";
  upstreamStarship = builtins.fromTOML (builtins.readFile (dots + "/starship.toml"));
  gtkTheme = {
    name = "adw-gtk3-dark";
    package = pkgs.adw-gtk3;
  };
in
{
  imports = [ inputs.caelestia-shell.homeManagerModules.default ];

  # Mirror only Home Manager Hyprland's generic session lifecycle: import the
  # compositor environment, then activate the target linked to the graphical
  # session. Caelestia itself remains independently dot-started below.
  systemd.user.targets.hyprland-session.Unit = {
    Description = "Hyprland compositor session";
    Documentation = [ "man:systemd.special(7)" ];
    BindsTo = [ "graphical-session.target" ];
    Wants = [ "graphical-session-pre.target" ];
    After = [ "graphical-session-pre.target" ];
  };

  programs.caelestia = {
    enable = true;
    package = caelestiaShell;
    # Upstream Hyprland dots start the shell with `caelestia shell -d`.
    # Keep lifecycle ownership there so Home Manager config changes can be
    # handled by Caelestia's in-process settings watcher.
    systemd.enable = false;
    cli.enable = true;
  };

  # Keep one Nix-owned baseline while leaving shell.json as a normal writable
  # file so Caelestia's Settings UI and file watcher can operate on it.
  xdg.dataFile."caelestia/shell.json.nix-baseline".source = caelestiaShellBaseline;

  # Direct Home Manager switches reassert the baseline. The systemd Home
  # Manager service skips this at boot so runtime experiments survive reboot;
  # NixOS switch/test invokes this same writer explicitly from the host hook.
  home.activation.caelestiaShellSettings = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    if [ "''${PHOENIX_SKIP_CAELESTIA_BASELINE:-0}" != 1 ]; then
      ${caelestiaShellReassert}
    fi
  '';

  # Deploy upstream dotfiles as static, store-backed files. Home Manager's
  # recursive linking leaves the directories themselves writable, including
  # hypr/scheme for the runtime-generated current.lua.
  xdg.configFile = {
    "hypr" = {
      source = "${caelestiaDots}/hypr";
      recursive = true;
    };

    "caelestia/hypr-vars.lua".text = "return ${renderLuaTable hyprVars}\n";
    "caelestia/hypr-user.lua".text = hyprUser;
    "caelestia/user-config.fish".text = "# Phoenix Fish extension point; managed by Home Manager.\n";

    "fish" = {
      source = dots + "/fish";
      recursive = true;
    };
    "foot/foot.ini".source = dots + "/foot/foot.ini";
    "fastfetch" = {
      source = dots + "/fastfetch";
      recursive = true;
    };
    "btop/btop.conf".source = dots + "/btop/btop.conf";
    "micro/settings.json".source = dots + "/micro/settings.json";
    "Thunar" = {
      source = dots + "/thunar";
      recursive = true;
    };
  };

  xdg.userDirs = {
    enable = true;
    setSessionVariables = true;
  };

  programs.starship = {
    enable = true;
    settings = upstreamStarship;
  };

  home.packages = with pkgs; [
    bat
    bluez
    btop
    cliphist
    coreutils
    curl
    direnv
    eza
    fastfetch
    fish
    foot
    gammastep
    geoclue2-with-demo-agent
    glib
    gnome-keyring
    hyprpicker
    jq
    lazygit
    libnotify
    micro
    procps
    pwvucontrol
    ripgrep
    systemd
    thunar
    trash-cli
    papirus-folders
    xdg-user-dirs
    wl-clipboard
    zoxide
  ];

  # Upstream defaults for GTK/Qt theme components, expressed declaratively.
  gtk = {
    enable = true;
    theme = gtkTheme;
    gtk4.theme = gtkTheme;
    iconTheme = {
      name = "Papirus-Dark";
      package = pkgs.papirus-icon-theme;
    };
  };

  qt = {
    enable = true;
    platformTheme.name = "kde";
    style = {
      name = "Darkly";
      package = pkgs.darkly;
    };
  };

  home.pointerCursor = {
    name = "Sweet-cursors";
    package = pkgs.sweet-nova;
    size = 24;
    gtk.enable = true;
    x11.enable = true;
  };

  # Caelestia supplies the CSS baseline; append any Phoenix chrome CSS after it.
  # Firefox privacy, policy, extensions, and profile settings remain in the
  # existing Phoenix Firefox module and merge with these profile additions.
  programs.firefox.profiles = lib.genAttrs [ "hardened" "compat" "clean" ] (_: {
    userChrome = caelestiaFirefoxChrome + "\n" + phoenixFirefoxChrome;
    settings."toolkit.legacyUserProfileCustomizations.stylesheets" = true;
  });
}
