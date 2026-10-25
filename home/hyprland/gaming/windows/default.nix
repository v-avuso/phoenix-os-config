{ config, lib, ... }:
let
  cfg = config.phoenix.gameWindows;
  json = builtins.toJSON;
  luaList = xs: "{ " + lib.concatMapStringsSep ", " json xs + " }";
in
{
  options.phoenix.gameWindows = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Keep classified games tiled without changing desktop navigation.";
    };
    extraClasses = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Exact game window classes lacking Caelestia's game tag or native content hint.";
    };
    excludedClasses = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Exact classes exempt from Phoenix game handling, including game dialogs.";
    };
  };
  config._module.args.phoenixGameWindowsHyprLua = ''
    local gameWindowOptions = {
      enable = ${if cfg.enable then "true" else "false"},
      extra_classes = ${luaList cfg.extraClasses},
      excluded_classes = ${luaList cfg.excludedClasses},
      excluded_regex = ${json ("negative:(" + lib.concatMapStringsSep "|" lib.escapeRegex cfg.excludedClasses + ")")},
    }
    local phoenixIsGameWindow = dofile("${./classification.lua}")(gameWindowOptions)
    dofile("${./game-windows.lua}")(gameWindowOptions, phoenixIsGameWindow)
  '';
}
