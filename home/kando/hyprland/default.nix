# Concrete Hyprland adapter for Phoenix Kando; no other desktop is implied.
{ config, inputs, pkgs }:
let
  cfg = config.phoenix.kando;
  hypr = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system}.hyprland;
in
{
  sessionTarget = "hyprland-session.target";
  commands = {
    overview = ''${hypr}/bin/hyprctl eval 'hl.plugin.hyprexpo.expo("on all")' '';
    nextWorkspace = "${hypr}/bin/hyprctl eval 'phoenix_workspace_step(1)'";
    previousWorkspace = "${hypr}/bin/hyprctl eval 'phoenix_workspace_step(-1)'";
    closeWindow = "${hypr}/bin/hyprctl dispatch 'hl.dsp.window.close()'";
  };
  lua = ''
    ${if cfg.gameBypass or true then ''
    local configureKandoShortcuts = dofile("${./shortcuts.lua}")
    configureKandoShortcuts(phoenixIsGameWindow, ${builtins.toJSON (cfg.gameButtons or "mouse")})
    '' else ''
    hl.bind("F23", hl.dsp.global("menu.kando.Kando:global-menu"), { transparent = true })
    hl.bind("F24", hl.dsp.global("menu.kando.Kando:contextual-menu"), { transparent = true })
    ''}
    hl.window_rule({
      name = "phoenix-kando",
      match = { class = "^menu[.]kando[.]Kando$", title = "^Kando Menu$" },
      no_blur = true, opaque = true, move = {0, 0}, size = {"100%", "100%"},
      rounding = 0, border_size = 0, no_anim = true, float = true, pin = true, stay_focused = true,
    })
  '';
}
