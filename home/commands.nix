{ pkgs, user, ... }:

{
  home.packages = [ (import ../commands { inherit pkgs user; }) ];
}
