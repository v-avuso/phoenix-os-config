{ inputs, pkgs, ... }:
let
  policy = builtins.fromJSON (builtins.readFile ../../../config/updates.json);
  hold = policy.holds.codex-cli or null;
  source = policy.packageSources.codex-cli;
  selectedNixpkgs = if hold != null then
    builtins.getFlake "github:NixOS/nixpkgs/${hold.pin}"
  else if source == "nixpkgs" then inputs.nixpkgs
  else if source == "nixpkgs-unstable" then inputs.nixpkgs-unstable
  else throw "updates.json has an unsupported Codex CLI source";
  base = assert builtins.elem source [ "nixpkgs" "nixpkgs-unstable" ];
    selectedNixpkgs.legacyPackages.${pkgs.stdenv.hostPlatform.system}.codex;
  fix = (policy.patches or {}).codex-cli or null;
  selectedPackage = if fix == null then base else base.overrideAttrs (old: {
    patches = (old.patches or []) ++ map (path: ../../../. + "/${path}") fix.patchFiles;
  });
  # Nixpkgs 0.160.0 wrapped the launcher; the inspected 0.162.1 recipe
  # installs the ELF directly for Codex daemon executable validation. Keep
  # older holds compatible and verify the exact identity below: version is a
  # layout prediction, never permission to admit a different executable.
  networkExecutableName = if pkgs.lib.versionAtLeast selectedPackage.version "0.162.1"
    then "codex" else ".codex-wrapped";
  package = selectedPackage.overrideAttrs (old: {
    passthru = (old.passthru or {}) // {
      phoenixNetworkExecutable = "${package}/bin/${networkExecutableName}";
      phoenixNetworkExecutableCheck = pkgs.runCommand "codex-network-executable-check" {
        nativeBuildInputs = [ pkgs.python3 ];
      } ''
        python3 ${./agent/tests/codex-executable.py} \
          ${package}/bin/codex ${package.phoenixNetworkExecutable}
        touch "$out"
      '';
    };
  });
in {
  # User CLI follows its selected Nixpkgs source. The protected deployment
  # reviewer has an independent immutable recipe and version in agent/.
  _module.args.codexCliPackage = package;
}
