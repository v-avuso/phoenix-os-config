# Source-built candidates only; importing this file enables no host feature.
{ pkgs, rustOverlay }:
let
  inherit (pkgs) lib;
  version = "0.1.2-phoenix.1";
  sourceRevision = "6648bd0c290efbc41ba131ee9831ee45cd431f94";
  src = pkgs.fetchurl {
    url = "https://github.com/NVIDIA/OpenShell/archive/refs/tags/v0.1.2.tar.gz";
    sha256 = "0ea7e81c5980680d4e65ad292a77ed3fc992a3cf5414bb99669f5c57d9ceb551";
  };
  patches = [ ./supervisor.patch ./runtime-classification.patch ./log-drain.patch ];
  # One shared, fixed Cargo.lock import; no release compilation to obtain it.
  vendor = pkgs.rustPlatform.fetchCargoVendor {
    name = "openshell-0.1.2-cargo-deps";
    inherit src;
    hash = "sha256-zQo6Z62V4n1vQU59fD2Rx3y0nMQuD2Q6A9lzsRyaswI=";
  };
  # Reuse the already-locked transitive overlay; do not add/update flake inputs.
  toolchainPkgs = pkgs.extend rustOverlay.overlays.default;
  toolchain = toolchainPkgs.rust-bin.stable."1.95.0".minimal.override {
    targets = [ "x86_64-unknown-linux-musl" ];
  };
  platform = pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; };
  build = role: platform: target: binary:
    platform.buildRustPackage {
      pname = "phoenix-openshell-${role}";
      inherit version src patches;
      cargoDeps = vendor;
      auditable = false;
      doCheck = false; # Focused source tests and real VM acceptance are separate gates.
      dontStrip = true;
      dontPatchELF = true; # Images require upstream ABI, not Nix loader/RPATH rewriting.
      nativeBuildInputs = with pkgs; [ cargo-zigbuild zig cmake perl pkg-config ];
      env = {
        OPENSHELL_GIT_VERSION = version;
        GIT_DIR = "/nonexistent";
        CARGO_NET_OFFLINE = "true";
        CARGO_NET_RETRY = "0";
        CARGO_INCREMENTAL = "0";
      };
      postPatch = ''
        test "$(sha256sum Cargo.lock | cut -d' ' -f1)" = ea10e2922eece4077a2c1be17cac83214aa5f79f39fd6c5cc830e1a2cf9d459a
        patchShebangs tasks/scripts/setup-zig-cc-wrapper.sh
      '';
      buildPhase = ''
        runHook preBuild
        export HOME="$TMPDIR/home"
        mkdir -p "$HOME"
        export ZIG=${lib.getExe pkgs.zig}
        export ZIG_GLOBAL_CACHE_DIR="$TMPDIR/zig-global-cache"
        export ZIG_LOCAL_CACHE_DIR="$TMPDIR/zig-local-cache"
        export CMAKE_BUILD_PARALLEL_LEVEL=2 RAYON_NUM_THREADS=2
        ${lib.optionalString (role == "supervisor") ''
          # Exact upstream wrapper binds C/C++ dependencies to the GNU2.28 floor.
          eval "$(bash tasks/scripts/setup-zig-cc-wrapper.sh ${target} ${target} "$TMPDIR/zig-cc")"
          patchShebangs "$TMPDIR/zig-cc"
        ''}
        cargo zigbuild --offline --locked --release --target ${target} -j2 \
          -p ${binary} --bin ${binary}
        runHook postBuild
      '';
      installPhase = ''
        runHook preInstall
        install -Dm${if role == "runtime" then "555" else "755"} \
          target/${if role == "supervisor" then "x86_64-unknown-linux-gnu" else target}/release/${binary} \
          "$out/bin/${binary}"
        runHook postInstall
      '';
      passthru = { inherit sourceRevision vendor toolchain; };
      meta.platforms = [ "x86_64-linux" ];
    };
in
{
  inherit src vendor toolchain;
  supervisor = build "supervisor" platform "x86_64-unknown-linux-gnu.2.28" "openshell-supervisor";
  runtime = build "runtime" platform "x86_64-unknown-linux-musl" "openshell-sandbox";
}
