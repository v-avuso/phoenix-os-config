# On-demand factory only; no installed grant, daemon, policy or activation.
{ pkgs, descriptor, name ? "phoenix-source-recovery" }:
let
  settings = pkgs.writeText "phoenix-source-recovery.json" (builtins.toJSON descriptor);
  entry = name: suffix: pkgs.writeShellScriptBin name ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./source-bootstrap.py} ${settings} ${suffix}
  '';
in pkgs.symlinkJoin {
  inherit name;
  paths = [
    (entry name "")
    (entry "${name}-inspect" "--inspect")
  ];
}
