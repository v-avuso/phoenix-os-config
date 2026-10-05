{ lib, stdenvNoCC, fetchurl, gnutar, gzip }:

# Deliberate control-plane pin: update separately after reviewing exact upstream
# isolation/configuration/compaction authority. User CLI updates do not change it.
# Keep the reviewed prebuilt independently of the user's unstable CLI package.
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
    description = "Protected Codex CLI for deployment review";
    homepage = "https://github.com/openai/codex";
    mainProgram = "codex";
    platforms = [ "x86_64-linux" ];
    license = lib.licenses.asl20;
  };
}
