{ config, lib, ... }:

{
  options.phoenix.allowUnfreePackages = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    default = [ ];
    description = "Unfree Nixpkgs package names explicitly allowed by Phoenix modules.";
  };

  config.nixpkgs.config.allowUnfreePredicate =
    pkg: builtins.elem (lib.getName pkg) config.phoenix.allowUnfreePackages;
}
