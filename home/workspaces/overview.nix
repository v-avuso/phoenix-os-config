{ pkgs }:
let
  source = pkgs.fetchFromGitHub {
    owner = "sandwichfarm";
    repo = "hyprexpo";
    rev = "19288abbe00ef02dc8d5af2e381b8a0f18e184d8";
    hash = "sha256-UTCAy+nfVxGTxi+POMI0kdpwaImP1sgoohSeIEMZtpA=";
  };
in
# Use the compositor's package set and builder, including its dependency ABI.
(pkgs.callPackage (source + "/default.nix") { }).overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./persistent-previews.patch ];
  doCheck = true;
})
