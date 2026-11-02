{ pkgs }:
let
  versions = {
    "0.56.2" = {
      rev = "19288abbe00ef02dc8d5af2e381b8a0f18e184d8";
      hash = "sha256-UTCAy+nfVxGTxi+POMI0kdpwaImP1sgoohSeIEMZtpA=";
      patch = ./persistent-previews.patch;
    };
    "0.57.0" = {
      rev = "3ec4d82e52f0d4765b87f6ef14f1883a44e85e27";
      hash = "sha256-xhu3Un8dUIJSYv/gqQUlP74SkbQgewhv1tgllBcheAQ=";
      patch = ./persistent-previews-057.patch;
    };
  };
  selected = versions.${pkgs.hyprland.version} or
    (throw "Recheck pinned HyprExpo compatibility before upgrading Hyprland.");
  source = pkgs.fetchFromGitHub {
    owner = "sandwichfarm";
    repo = "hyprexpo";
    inherit (selected) rev hash;
  };
in
# Use the compositor's package set and builder, including its dependency ABI.
(pkgs.callPackage (source + "/default.nix") { }).overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ selected.patch ];
  doCheck = true;
})
