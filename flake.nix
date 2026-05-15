{
  description = "PhoeNix OS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

    # Codex Desktop is not available from the standard NixOS package set here.
    # This upstream Linux port exposes a Nix flake package for the desktop app.
    codex-desktop-linux = {
      url = "github:ilysenko/codex-desktop-linux";
    };
  };

  outputs = inputs@{ nixpkgs, ... }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      mkHost = hostPath:
        lib.nixosSystem {
          inherit system;
          specialArgs = { inherit inputs; };
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
