{
  description = "PhoeNix OS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    plasma-manager = {
      url = "github:nix-community/plasma-manager";
      inputs.home-manager.follows = "home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    caelestia-shell = {
      url = "github:caelestia-dots/shell";
      inputs.nixpkgs.follows = "nixpkgs-unstable";
    };

    caelestia-dots = {
      url = "github:caelestia-dots/caelestia";
      flake = false;
    };

    # Audited non-destructive simple restore; layout reconstruction stays disabled.
    hypr-persist = {
      url = "github:ngamber/hypr-persist/31836057e09b46d8d32645dbb75035f31164dd5f";
      flake = false;
    };

    firefox-addons = {
      url = "gitlab:rycee/nur-expressions?dir=pkgs/firefox-addons";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    arkenfox-nixos = {
      url = "github:dwarfmaster/arkenfox-nixos";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";

    # The upstream Linux port wraps OpenAI's signed Linux desktop payload.
    codex-desktop-linux.url = "github:ilysenko/codex-desktop-linux";

    # Keep Native's known-good module/package while the contained GUI needs a
    # newer desktop protocol. Advance Native through its own reviewed upgrade.
    codex-desktop-sandbox = {
      url = "github:ilysenko/codex-desktop-linux/664436c7d0f3f7919a626c25999424f92bf4a044";
      inputs.nixpkgs.follows = "codex-desktop-linux/nixpkgs";
      inputs.flake-utils.follows = "codex-desktop-linux/flake-utils";
    };

    # Upstream GUI containment; the lock pins framework and manifest translation.
    nix-bwrapper = {
      url = "github:Naxdy/nix-bwrapper/d170b06fafc0703fff36ec422a64516594b39bd9";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Stable Psysonic channel; flake.lock pins the release branch revision.
    psysonic.url = "github:Psysonic/psysonic?ref=release";

    timewall = {
      url = "github:bcyran/timewall/19897aee9fee4f4ebd5cbd37b0fc4e3271cb6480";
      inputs.nixpkgs.follows = "nixpkgs-unstable";
    };
  };

  outputs =
    inputs@{ nixpkgs, ... }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      user = import ./config/user.nix { inherit lib; };
      mkHost =
        hostPath:
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
