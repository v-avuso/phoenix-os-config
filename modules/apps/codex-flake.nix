{
  # Codex Desktop is not available from the standard NixOS package set here.
  # This upstream Linux port exposes a Nix flake package for the desktop app;
  # keep the input app-local so hosts can opt in through modules/apps.nix.
  codex-desktop-linux = {
    url = "github:ilysenko/codex-desktop-linux";
    inputs.nixpkgs.follows = "nixpkgs";
  };
}
