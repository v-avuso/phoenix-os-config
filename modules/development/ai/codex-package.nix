{ lib, stdenvNoCC, fetchurl, gnutar, gzip }:

# Fresh stable upstream CLI releases help this deeply used daily tool. Keep the
# official prebuilt until ordinary packaging builds with its Btrfs fix.
# nix-update owns only this recipe's version and source checksum.
stdenvNoCC.mkDerivation rec {
  pname = "codex";
  version = "0.159.0";
  src = fetchurl {
    url = "https://github.com/openai/codex/releases/download/rust-v${version}/codex-package-x86_64-unknown-linux-musl.tar.gz";
    hash = "sha256-Ndpl1+hkTijqCk1OPYwVtAxrSSNW1M8hmGx+NB+Dok4=";
  };
  nativeBuildInputs = [ gnutar gzip ];
  dontUnpack = true;
  installPhase = ''
    mkdir -p "$out"
    tar -xzf "$src" -C "$out"
    chmod +x "$out/bin/codex" "$out/bin/codex-code-mode-host" "$out/codex-path/rg"
    if [ -f "$out/codex-resources/bwrap" ]; then
      chmod +x "$out/codex-resources/bwrap"
    fi
  '';
  meta = {
    description = "Official Codex CLI prebuilt with Phoenix's required executable layout";
    homepage = "https://github.com/openai/codex";
    mainProgram = "codex";
    platforms = [ "x86_64-linux" ];
    license = lib.licenses.asl20;
  };
}
