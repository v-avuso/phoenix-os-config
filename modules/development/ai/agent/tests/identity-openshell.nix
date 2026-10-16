# First stop/go gate only: real protected Podman service, no gateway/model/migration.
{ pkgs, workload }:
let
  lib = pkgs.lib;
  packages = import ../packages.nix { inherit pkgs; };
  script = pkgs.writeText "identity-openshell.py" (builtins.readFile ./identity-openshell.py);
  setup = pkgs.writeText "identity-setup.py" (builtins.readFile ../identity-setup.py);
in
assert lib.hasPrefix "/nix/store/" (toString workload.archive);
assert workload.sha256 == "b3083cbcb26bef5871ed25bc2bb519b28093db80a81500d97985d1537df6ac26";
assert workload.id == "38d1a6283d8dc515251c132471b416da81a803035b41dc2316d41805729323cd";
assert builtins.hashFile "sha256" workload.archive == workload.sha256;
pkgs.testers.runNixOSTest {
  name = "phoenix-identity-openshell-podman-gate";
  globalTimeout = 300;
  nodes.machine = { config, lib, ... }: {
    imports = [ ../identity.nix ];
    options.phoenix.agent.workspaces = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "/home/operator/workspace" ];
    };
    config = {
      _module.args = {
        user = { name = "operator"; homeDirectory = "/home/operator"; repoDirectory = "/home/operator/workspace"; };
        phoenixAgentPackages = packages;
        phoenixAgentLauncherConfig = pkgs.writeText "unused-launcher-config.json" "{}";
      };
      virtualisation = { memorySize = 4096; cores = 2; diskSize = 8192; podman.enable = true; };
      users.users.operator = { isNormalUser = true; uid = 1000; };
      phoenix.agent.identity.enable = true;
      environment.systemPackages = [ pkgs.python3 pkgs.util-linux ];
      environment.etc."identity-openshell.json".source = pkgs.writeText "identity-openshell.json" (builtins.toJSON {
        phase = "podman-keepid-gate";
        inherit setup;
        workload = workload // { archive = toString workload.archive; };
        uid = config.phoenix.agent.identity.uid;
        gid = config.phoenix.agent.identity.gid;
        operatorUid = 1000;
        workspace = "/home/operator/workspace";
        environment = config.systemd.services.phoenix-agent-podman.environment;
        python = "${pkgs.python3}/bin/python3";
        podman = "${pkgs.podman}/bin/podman";
        setpriv = "${pkgs.util-linux}/bin/setpriv";
        setfacl = "${pkgs.acl}/bin/setfacl";
        systemctl = "${pkgs.systemd}/bin/systemctl";
      });
      # No service overrides: actual identity.nix User/environment/ProtectHome,
      # narrow BindPaths/Delegate and mapping helpers are the defining boundary.
    };
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    try:
        machine.succeed("${pkgs.python3}/bin/python3 -I ${script} /etc/identity-openshell.json", timeout=180)
    finally:
        machine.execute("journalctl -u phoenix-agent-podman.service --no-pager > /tmp/identity-openshell-journal", timeout=10)
        machine.copy_from_vm("/tmp/identity-openshell-journal", "evidence")
        machine.copy_from_vm("/tmp/identity-openshell-evidence", "evidence")
  '';
}
