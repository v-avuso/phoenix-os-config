{ pkgs, ... }:
let
  policy = builtins.fromJSON (builtins.readFile ../../../config/updates.json);
  base = pkgs.callPackage ./codex-package.nix { };
  hold = policy.holds.codex-cli or null;
  package = if hold == null then base else base.overrideAttrs (_: {
    version = hold.pin.version;
    src = pkgs.fetchurl {
      url = "https://github.com/openai/codex/releases/download/rust-v${hold.pin.version}/codex-package-x86_64-unknown-linux-musl.tar.gz";
      hash = hold.pin.hash;
    };
  });
in {
  # Both launch modes and the protected reviewer consume this same package.
  _module.args.codexCliPackage = package;
}
