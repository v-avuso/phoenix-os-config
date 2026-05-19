{
  description = "PhoeNix OS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";

    home-manager = {
      url = "github:nix-community/home-manager/release-25.11";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hyprland = {
      url = "github:hyprwm/Hyprland";
      inputs.nixpkgs.follows = "nixpkgs-unstable";
    };

    caelestianix.url = "github:v-avuso/caelestia-nixos";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";

    # Codex Desktop is not available from the standard NixOS package set here.
    # This upstream Linux port exposes a Nix flake package for the desktop app.
    codex-desktop-linux.url = "github:ilysenko/codex-desktop-linux";
  };

  outputs = inputs@{ nixpkgs, ... }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      user = import ./config/user.nix { inherit lib; };
      mkHost = hostPath:
        lib.nixosSystem {
          inherit system;
          specialArgs = { inherit inputs user; };
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
