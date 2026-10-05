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
  package = if fix == null then base else base.overrideAttrs (old: {
    patches = (old.patches or []) ++ map (path: ../../../. + "/${path}") fix.patchFiles;
  });
in {
  # User CLI follows its selected Nixpkgs source. The protected deployment
  # reviewer has an independent immutable recipe and version in agent/.
  _module.args.codexCliPackage = package;
}
