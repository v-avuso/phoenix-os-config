{ callPackage, fetchurl }:

# Deliberate control-plane pin: update separately after reviewing exact upstream
# isolation/configuration/compaction authority. User CLI updates do not change it.
# Reuses the same executable layout; complete source review covers recipe edits.
(callPackage ../codex-package.nix { }).overrideAttrs (_old: rec {
  version = "0.159.0";
  src = fetchurl {
    url = "https://github.com/openai/codex/releases/download/rust-v${version}/codex-package-x86_64-unknown-linux-musl.tar.gz";
    hash = "sha256-Ndpl1+hkTijqCk1OPYwVtAxrSSNW1M8hmGx+NB+Dok4=";
  };
})
