{ lib, ... }:

let
  phoenixShellAliases = {
    insomnia = ''systemd-inhibit --what=sleep --why="Manual insomnia mode" sleep infinity'';
  };

  aliasesFile =
    lib.concatStringsSep "\n" (
      lib.mapAttrsToList (
        name: command: "alias ${name}=${lib.escapeShellArg command}"
      ) phoenixShellAliases
    )
    + "\n";
in
{
  xdg.configFile."phoenix/shell-aliases.sh".text = aliasesFile;
}
