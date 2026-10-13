# Thin CLI owner; root authorization remains in the existing clients/controllers.
{ pkgs, authorizationLibrary, authorizationPolicy, deploymentCommands ? { }, adminClient ? null }:
let
  config = pkgs.writeText "phoenix-ai-broker.json" (builtins.toJSON {
    library = toString authorizationLibrary;
    policy = toString authorizationPolicy;
    commands = deploymentCommands // pkgs.lib.optionalAttrs (adminClient != null) {
      phoenix-admin = "${adminClient}/bin/phoenix-admin";
    };
  });
in pkgs.writeShellScriptBin "ai-broker" ''
  exec ${pkgs.python3}/bin/python3 -I ${./ai-broker.py} ${config} "$@"
''
