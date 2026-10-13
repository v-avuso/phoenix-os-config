{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.phoenix.workspaces;
  hyprPkgs = inputs.nixpkgs-unstable.legacyPackages.${pkgs.stdenv.hostPlatform.system};
  overview = import ./overview.nix { pkgs = hyprPkgs; };
  ranges = lib.mapAttrsToList (monitor: range: {
    inherit monitor;
    inherit (range) first;
    count = cfg.count;
  }) cfg.monitors;
  ids = lib.concatMap (r: lib.range r.first (r.first + r.count - 1)) ranges;
  lua = ''
    hl.plugin.load("${overview}/lib/libhyprexpo.so")
    hl.config({ plugin = { hyprexpo = {
      dynamic_grid = 1, fill_gaps = 0, mru_sort = 0, skip_empty = 0,
      workspace_method = "${
        lib.concatMapStringsSep ", " (r: "${r.monitor} first ${toString r.first}") ranges
      }",
      drag_drop_enable = 1, show_workspace_numbers = 1,
    } } })
    ${lib.concatMapStringsSep "\n" (
      r:
      lib.concatMapStringsSep "\n" (id: ''
        hl.workspace_rule({ workspace = "${toString id}", monitor = "${r.monitor}",
          persistent = true${lib.optionalString (id == r.first) ", default = true"} })
      '') (lib.range r.first (r.first + r.count - 1))
    ) ranges}
    local configureWorkspaceNavigation = dofile("${./navigation.lua}")
    configureWorkspaceNavigation({
      ${lib.concatMapStringsSep "\n" (
        r: ''["${r.monitor}"] = { first = ${toString r.first}, count = ${toString r.count} },''
      ) ranges}
    })
  '';
in
{
  options.phoenix.workspaces = {
    count = lib.mkOption {
      type = lib.types.ints.between 1 7;
      default = 5;
      description = "Overview slots per monitor.";
    };
    monitors = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            first = lib.mkOption { type = lib.types.ints.positive; };
          };
        }
      );
      default = { };
      description = "Monitor names and their dedicated workspace ranges.";
    };
  };
  config = {
    assertions = [
      {
        assertion = hyprPkgs.hyprland.version == "0.56.2";
        message = "Recheck pinned HyprExpo compatibility before upgrading Hyprland.";
      }
      {
        assertion = builtins.length ids == builtins.length (lib.unique ids);
        message = "Monitor workspace ranges must not overlap.";
      }
    ];
    _module.args.phoenixWorkspacesHyprLua = lua;
    home.packages = [ overview ];
  };
}
