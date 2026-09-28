{ pkgs, ... }:

let
  # The upstream Codex Nix package currently fails because Git Cargo
  # dependencies such as appcontainer_common lack required outputHashes.
  # Temporarily use the official 0.159.0-alpha.9 prebuilt, which contains the
  # Btrfs sandbox fix (openai/codex#47968). Remove this when nixpkgs/upstream
  # provides a normally packaged release with the fix that builds correctly.
  version = "0.159.0-alpha.9";

  codexPrebuilt = pkgs.runCommand "codex-${version}" {
    src = pkgs.fetchurl {
      url = "https://github.com/openai/codex/releases/download/rust-v${version}/codex-package-x86_64-unknown-linux-musl.tar.gz";
      hash = "sha256-IbLR5QwEsxFKgAHir+q9VhULaEduZs+7diVc2LXQA50=";
    };

    nativeBuildInputs = [
      pkgs.gnutar
      pkgs.gzip
    ];

    meta.mainProgram = "codex";
  } ''
    mkdir -p "$out"
    tar -xzf "$src" -C "$out"

    chmod +x \
      "$out/bin/codex" \
      "$out/bin/codex-code-mode-host" \
      "$out/codex-path/rg"

    if [ -f "$out/codex-resources/bwrap" ]; then
      chmod +x "$out/codex-resources/bwrap"
    fi
  '';
in
{
  _module.args.codexCliPackage = codexPrebuilt;
  environment.systemPackages = [ codexPrebuilt ];
}
