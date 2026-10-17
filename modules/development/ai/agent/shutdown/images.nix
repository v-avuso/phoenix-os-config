# Closed source-built candidates. This file enables no host option or image pull.
{ pkgs, rustOverlay }:
let
  candidates = import ./packages.nix { inherit pkgs rustOverlay; };
  specs = {
    supervisor = {
      imageName = "ghcr.io/nvidia/openshell/supervisor";
      imageDigest = "sha256:d7b5264bb6bc56f4796e6fa3617b8e4a8d785be0b7293542efd8cc250b0fb67a";
      transportHash = "sha256-ow0si2093kTv4GFhR5zIvUU+7xxcFnCMlkBHpLkU/1M=";
      configID = "494b86855b51987cd68e205aa1b08d67592d4ea7b989f94c66e7179e17a97388";
      executable = "openshell-supervisor";
      mode = "0755";
      package = candidates.supervisor;
    };
    runtime = {
      imageName = "ghcr.io/nvidia/openshell/sandbox";
      imageDigest = "sha256:bf4797b6c511f2d8ba02955dbba4bf76c1f0dd6d83531420c5408d5f1fb9d72f";
      transportHash = "sha256-Vlefx/uNpdkgVKYZ75HI+LJljyexmvgcNSlJ3ui3NMk=";
      configID = "e7a78d2e2c9c7d6ffc801e429a3304b51ffd65a84692530f2bbceea11e6e1558";
      executable = "openshell-sandbox";
      mode = "0555";
      package = candidates.runtime;
    };
  };
  bases = builtins.mapAttrs (_: spec: pkgs.dockerTools.pullImage {
    inherit (spec) imageName imageDigest;
    sha256 = spec.transportHash;
    os = "linux";
    arch = "amd64";
    finalImageTag = "0.1.2";
  }) specs;
  build = role: spec:
    let
      base = bases.${role};
      # Config is immutable upstream metadata, never a caller-supplied override.
      baseConfig = pkgs.runCommand "shutdown-${role}-verified-base-config.json" {
        nativeBuildInputs = [ pkgs.gnutar pkgs.jq ];
      } ''
        config=$(tar -xOf ${base} manifest.json | jq -er '.[0].Config')
        tar -xOf ${base} "$config" > base-config.json
        test "$(sha256sum base-config.json | cut -d' ' -f1)" = ${spec.configID}
        jq -e '.config' base-config.json > "$out"
      '';
    in (pkgs.dockerTools.buildImage {
      name = "phoenix-openshell-${role}";
      tag = "0.1.2-phoenix.1";
      fromImage = base;
      # buildImage already prepends base Env; retain all other config exactly.
      config = builtins.removeAttrs (builtins.fromJSON (builtins.readFile baseConfig)) [ "Env" ];
      extraCommands = ''
        install -m${spec.mode} ${spec.package}/bin/${spec.executable} ${spec.executable}
      '';
    }).overrideAttrs (old: {
      passthru = (old.passthru or { }) // {
        inherit base;
        binary = "${spec.package}/bin/${spec.executable}";
        expectedBaseConfigID = spec.configID;
      };
    });
  builtImages = {
    supervisor = build "supervisor" specs.supervisor;
    runtime = build "runtime" specs.runtime;
  };
in
{
  inherit bases candidates;
  inherit (builtImages) supervisor runtime;
  # Derive exact archive/config/binary bindings at build time, not evaluation.
  manifest = pkgs.runCommand "phoenix-openshell-shutdown-images.json" { } ''
    ${pkgs.python3}/bin/python3 -I ${./backend.py} metadata \
      ${builtImages.runtime} ${builtImages.supervisor} \
      ${builtImages.runtime.binary} ${builtImages.supervisor.binary} "$out"
  '';
}
