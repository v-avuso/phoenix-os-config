{ lib }:

let
  name = "v";
  homeDirectory = "/home/${name}";
  repoDirectory = "${homeDirectory}/repos/code/phoenix-os-config";
in
{
  inherit name;
  inherit homeDirectory;
  downloadsDirectory = "${homeDirectory}/Downloads";
  inherit repoDirectory;
  nixosConfigPath = repoDirectory;
  description = lib.toUpper name;
}
