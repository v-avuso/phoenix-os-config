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
  # OpenShell identifies /proc/exe after the Nixpkgs binary wrapper execs.
  package = selectedPackage.overrideAttrs (old: {
    passthru = (old.passthru or {}) // {
      phoenixNetworkExecutable = "${package}/bin/.codex-wrapped";
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
