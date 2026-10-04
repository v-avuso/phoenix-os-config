# Evaluate the adapter without a system build or copying the checkout into store.
{ nixpkgsPath }:
let
  upstreamLib = import (nixpkgsPath + "/lib");
  lib = upstreamLib // {
    hm.dag.entryAfter = _: text: text;
  };
  package = name: { outPath = "/nix/store/fixture-${name}"; };
  pkgs = {
    stdenv.hostPlatform.system = "x86_64-linux";
    kando = (package "kando") // {
      version = "2.3.0";
      overrideAttrs = f: (package "kando-held") // (f { patches = [ ]; });
    };
    foot = package "foot";
    xdg-utils = package "xdg-utils";
    pwvucontrol = package "pwvucontrol";
    python3 = package "python3";
    coreutils = package "coreutils";
    systemd = package "systemd";
    makeWrapper = package "makeWrapper";
    writeText = name: text: (package name) // { inherit text; };
    writeShellScript = name: text: (package name) // { inherit text; };
    symlinkJoin = args: (package args.name) // args;
  };
  module = import ../home/kando.nix {
    inherit lib pkgs;
    config = {
      phoenix.kando.enable = true;
      xdg.configHome = "/home/fixture/.config";
      home.homeDirectory = "/home/fixture";
    };
    inputs.nixpkgs-unstable.legacyPackages.x86_64-linux.hyprland = package "hyprland";
  };
  c = module.config.content;
in
{
  settings = builtins.fromJSON c.xdg.dataFile."kando/config.json.nix-baseline".source.text;
  menus = builtins.fromJSON c.xdg.dataFile."kando/menus.json.nix-baseline".source.text;
  wrapper = (builtins.head c.home.packages).postBuild;
  lua = c._module.args.phoenixKandoHyprLua;
  service = c.systemd.user.services.kando;
  activation = c.home.activation.kandoSettings;
}
