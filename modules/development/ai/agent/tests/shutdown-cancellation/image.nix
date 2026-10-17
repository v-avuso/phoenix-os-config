# Validation overlay, not a reproducible source package or production image.
{ pkgs, binary }:
let
  base = builtins.storePath "/nix/store/zalazb059fm32a2ng1b8pngw2qylapwf-phoenix-openshell-supervisor.docker.tar";
  # buildImage inherits only base Env automatically. Preserve the entire existing
  # container config explicitly, including entrypoint/user/working directory.
  baseConfig = pkgs.runCommand "shutdown-supervisor-base-config.json" {
    nativeBuildInputs = [ pkgs.gnutar pkgs.jq ];
  } ''
    config=$(tar -xOf ${base} manifest.json | jq -er '.[0].Config')
    tar -xOf ${base} "$config" | jq -e '.config' > "$out"
  '';
in
assert builtins.hashFile "sha256" base == "b77c8746e6228799e00bddb5b751f9155244c7e7f0b8f28f8eefaf936609e2c2";
assert pkgs.lib.hasPrefix "/nix/store/" (toString binary);
assert builtins.hashFile "sha256" binary == "112a50bafdc5b94998cf4d3c403efad3f96b3f0cf637f7cd096c301ec7c88654";
pkgs.dockerTools.buildImage {
  name = "phoenix-shutdown-cancellation-supervisor";
  tag = "validation";
  fromImage = base;
  # buildImage prepends the base Env itself; passing it twice would duplicate it.
  config = builtins.removeAttrs (builtins.fromJSON (builtins.readFile baseConfig)) [ "Env" ];
  extraCommands = ''
    cp ${binary} openshell-supervisor
    chmod 0755 openshell-supervisor
  '';
}
