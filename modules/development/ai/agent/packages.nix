{ pkgs }:
let
  version = "0.1.2";
  release =
    name: hash:
    pkgs.fetchurl {
      url = "https://github.com/NVIDIA/OpenShell/releases/download/v${version}/${name}.tar.gz";
      inherit hash;
    };
in
{
  cli = pkgs.stdenvNoCC.mkDerivation {
    pname = "openshell";
    inherit version;
    src = release "openshell-x86_64-unknown-linux-musl" "sha256-fraRcoUzGgnjMAJmoFWGFkgaXpknyuJhLqB8QEW23W8=";
    sourceRoot = ".";
    dontConfigure = true;
    dontBuild = true;
    installPhase = ''
      install -Dm755 openshell "$out/bin/openshell"
    '';
    meta.mainProgram = "openshell";
  };
  gateway = pkgs.stdenvNoCC.mkDerivation {
    pname = "openshell-gateway";
    inherit version;
    src = release "openshell-gateway-x86_64-unknown-linux-gnu" "sha256-IY2IeEWzoCCrdTXJmF65xmbWk48UQESVf4uCtCiSqts=";
    sourceRoot = ".";
    nativeBuildInputs = [ pkgs.autoPatchelfHook ];
    buildInputs = [ pkgs.glibc ];
    dontConfigure = true;
    dontBuild = true;
    installPhase = ''
      install -Dm755 openshell-gateway "$out/bin/openshell-gateway"
    '';
    meta.mainProgram = "openshell-gateway";
  };
}
