{ pkgs, defaultTarget ? null, rootProbe ? "${pkgs.util-linux}/bin/findmnt" }:
pkgs.writeShellApplication {
  name = "phoenix-target";
  runtimeInputs = [ pkgs.systemd pkgs.util-linux ];
  text = ''
    phoenix_root_probe=${pkgs.lib.escapeShellArg rootProbe}
  '' + pkgs.lib.optionalString (defaultTarget != null) ''
    phoenix_configured_target=${pkgs.lib.escapeShellArg defaultTarget}
  '' + builtins.readFile ./phoenix-target;
}
