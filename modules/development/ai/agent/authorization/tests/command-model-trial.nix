# Fixed controlled real-review/root-id trial; never activate this candidate.
{ flake }:
let
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  lib = pkgs.lib;
  production = flake.nixosConfigurations.metal.config;
  on = (flake.nixosConfigurations.metal.extendModules {
    modules = [ {
      services.phoenixDeployment.securityReview.enable = true;
      phoenix.authorization.commands = {
        enable = true;
        entries = lib.mkForce {
          identity-review = {
            executable = "${pkgs.coreutils}/bin/id";
            arguments = [ "-u" ];
            rationale = "Read the executor UID only; no external input, mutation, credential access or delegated execution.";
            mode = "review";
            timeout = 10;
          };
        };
      };
    } ];
  }).config;
  parts = lib.splitString " " on.systemd.services.phoenix-deploy.serviceConfig.ExecStart;
  reviewer = pkgs.callPackage ../../reviewer-codex.nix { };
  gate = mode: executable: pkgs.writeShellScript "command-trial-${mode}" ''
    exec ${pkgs.python3}/bin/python3 -I ${../../tests/review-call-gate.py} ${mode} ${executable} "$@"
  '';
  gateBwrap = gate "bwrap" "${pkgs.bubblewrap}/bin/bwrap";
  gateCodex = gate "codex" "${reviewer}/bin/codex";
  publication = on.environment.etc."phoenix-authorization/command-authority.json".source;
  trialAuthority = pkgs.writeText "command-trial-authority.json" (builtins.toJSON {
    registry = on.phoenix.authorization.commands;
    candidate = toString publication;
    instrumentation = { inherit gateBwrap gateCodex; callLimit = 1; };
    helper = builtins.hashString "sha256" (builtins.readFile ./command-model-trial.py);
  });
  descriptor = pkgs.writeText "command-model-trial.json" (builtins.toJSON {
    version = 1;
    inherit gateBwrap gateCodex trialAuthority;
    controller = builtins.elemAt parts 2;
    config = builtins.elemAt parts 3;
    executable = "${pkgs.coreutils}/bin/id";
    provider = "${reviewer}/bin/codex";
    operatorUid = on.users.users.${(import ../../../../../../config/user.nix { inherit lib; }).name}.uid;
  });
  entry = name: mode: pkgs.writeShellScriptBin name ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./command-model-trial.py} ${descriptor} ${mode}
  '';
in
assert builtins.length parts == 5;
assert builtins.elemAt parts 1 == "-I" && builtins.elemAt parts 4 == "serve";
assert !production.phoenix.authorization.commands.enable;
assert on.services.phoenixDeployment.securityReview.model == "gpt-6-luna";
assert on.services.phoenixDeployment.securityReview.effort == "high";
pkgs.symlinkJoin {
  name = "phoenix-command-model-trial";
  paths = [
    (entry "phoenix-command-model-trial" "")
    (entry "phoenix-command-model-trial-dry-run" "--dry-run")
  ];
  passthru = { inherit descriptor; };
}
