{ lib }:

let
  name = "v";
in
{
  inherit name;
  homeDirectory = "/home/${name}";
  description = lib.toUpper name;
}
