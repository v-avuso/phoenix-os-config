# Explicit on-demand packaging only; neither closure is activated by evaluation/build.
{ flake, offClosure, onClosure }:
let
  pkgs = flake.inputs.nixpkgs.legacyPackages.x86_64-linux;
  descriptor = pkgs.writeText "review-window.json" (builtins.toJSON {
    off = builtins.storePath offClosure;
    on = builtins.storePath onClosure;
    busctl = "${pkgs.systemd}/bin/busctl";
    systemctl = "${pkgs.systemd}/bin/systemctl";
    systemdRun = "${pkgs.systemd}/bin/systemd-run";
    python = "${pkgs.python3}/bin/python3";
    script = ./review-window.py;
  });
  entry = name: mode: pkgs.writeShellScriptBin name ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./review-window.py} ${descriptor} ${mode}
  '';
in pkgs.symlinkJoin {
  name = "phoenix-controlled-review-window";
  paths = [
    (entry "phoenix-review-window-setup" "setup")
    (entry "phoenix-review-window-recover" "recover")
    (entry "phoenix-review-window-dry-run" "dry-run")
  ];
}
