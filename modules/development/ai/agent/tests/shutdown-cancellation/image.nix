# Two fixed validation overlays, not reproducible source packages or production images.
{ pkgs, binary, role ? "supervisor" }:
let
  specs = {
    supervisor = {
      archive = "/nix/store/zalazb059fm32a2ng1b8pngw2qylapwf-phoenix-openshell-supervisor.docker.tar";
      archiveSha256 = "b77c8746e6228799e00bddb5b751f9155244c7e7f0b8f28f8eefaf936609e2c2";
      binarySha256 = "14c412633c65c57a2c20fc2f3c093c6a181238f25628a854ffe95abd43f88f8c";
      executable = "openshell-supervisor";
      mode = "0755";
    };
    runtime = {
      archive = "/nix/store/k52bijkxlmw9ifq5fwdgzz4b4j9z5i40-phoenix-openshell-runtime.docker.tar";
      archiveSha256 = "ff175171aa978b7232ec5ca938162b95c825b8c387c42cc380d53421d8c886aa";
      binarySha256 = "745245e8f79e6a5050a78570a79b24ac3488c50dd3636ec5c8409755ec418d94";
      executable = "openshell-sandbox";
      mode = "0555";
    };
  };
  spec = specs.${role};
  base = builtins.storePath spec.archive;
  # buildImage inherits only base Env automatically. Preserve the entire existing
  # container config explicitly, including entrypoint/user/working directory.
  baseConfig = pkgs.runCommand "shutdown-${role}-base-config.json" {
    nativeBuildInputs = [ pkgs.gnutar pkgs.jq ];
  } ''
    config=$(tar -xOf ${base} manifest.json | jq -er '.[0].Config')
    tar -xOf ${base} "$config" | jq -e '.config' > "$out"
  '';
in
assert builtins.elem role [ "supervisor" "runtime" ];
assert builtins.hashFile "sha256" base == spec.archiveSha256;
assert pkgs.lib.hasPrefix "/nix/store/" (toString binary);
assert builtins.hashFile "sha256" binary == spec.binarySha256;
pkgs.dockerTools.buildImage {
  name = "phoenix-shutdown-cancellation-${role}";
  tag = "validation";
  fromImage = base;
  # buildImage prepends the base Env itself; passing it twice would duplicate it.
  config = builtins.removeAttrs (builtins.fromJSON (builtins.readFile baseConfig)) [ "Env" ];
  extraCommands = ''
    cp ${binary} ${spec.executable}
    chmod ${spec.mode} ${spec.executable}
  '';
}
