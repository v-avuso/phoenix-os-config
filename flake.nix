{
  description = "PhoeNix OS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      mkHost = hostPath:
        lib.nixosSystem {
          inherit system;
          modules = [ hostPath ];
        };
      metal = mkHost ./hosts/metal/configuration.nix;
      vm = mkHost ./hosts/vm/configuration.nix;
    in
    {
      nixosConfigurations = {
        inherit metal vm;

        default = metal;
      };
    };
}
