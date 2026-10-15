# On-demand, zero-AI root checkpoint trial; never enable/activate this config.
{ flake }:
let
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  lib = pkgs.lib;
  on = (flake.nixosConfigurations.metal.extendModules {
    modules = [ { services.phoenixDeployment.securityReview.enable = true; } ];
  }).config;
  parts = lib.splitString " " on.systemd.services.phoenix-deploy.serviceConfig.ExecStart;
  reviewer = pkgs.callPackage ../reviewer-codex.nix { };
  gate = mode: executable: pkgs.writeShellScript "review-trial-${mode}" ''
    exec ${pkgs.python3}/bin/python3 -I ${./review-call-gate.py} ${mode} ${executable} "$@"
  '';
  gateBwrap = gate "bwrap" "${pkgs.bubblewrap}/bin/bwrap";
  gateCodex = gate "codex" "${reviewer}/bin/codex";
  offlineNix = pkgs.writeShellScript "review-trial-offline-nix" ''
    exec ${pkgs.nix}/bin/nix --offline --max-jobs 0 --option builders "" "$@"
  '';
  descriptor = pkgs.writeText "checkpoint-trial-descriptor.json" (builtins.toJSON {
    inherit gateBwrap gateCodex offlineNix;
    controller = builtins.elemAt parts 2;
    config = builtins.elemAt parts 3;
  });
  helper = pkgs.writeShellScriptBin "phoenix-review-checkpoint-trial" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./review-checkpoint.py} ${descriptor}
  '';
  dryRun = pkgs.writeShellScriptBin "phoenix-review-checkpoint-trial-dry-run" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./review-checkpoint.py} ${descriptor} --dry-run
  '';
  integrationEntry = name: mode: pkgs.writeShellScriptBin name ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./review-checkpoint.py} ${descriptor} ${mode}
  '';
in
assert builtins.length parts == 5;
assert builtins.elemAt parts 1 == "-I" && builtins.elemAt parts 4 == "serve";
assert on.services.phoenixDeployment.securityReview.model == "gpt-6-luna";
assert on.services.phoenixDeployment.securityReview.effort == "high";
pkgs.symlinkJoin {
  name = "phoenix-review-checkpoint-trial";
  paths = [ helper dryRun
    (integrationEntry "phoenix-review-integration-trial" "--integration")
    (integrationEntry "phoenix-review-integration-trial-dry-run" "--integration-dry-run")
    (integrationEntry "phoenix-review-integration-prebuild-plan" "--prebuild-plan")
    (integrationEntry "phoenix-review-pending-trial" "--pending-override")
    (integrationEntry "phoenix-review-pending-trial-dry-run" "--pending-override-dry-run")
  ];
}
