{ pkgs }:
pkgs.writeShellScript "phoenix-mutable-json-settings" ''
  exec ${pkgs.python3}/bin/python3 ${./mutable-json-settings.py} "$@"
''
