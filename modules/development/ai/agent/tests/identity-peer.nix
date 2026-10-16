# Bounded distinct-UID transport/broker proof; OpenShell/Podman/backend are doubles.
{ pkgs }:
let
  lib = pkgs.lib;
  script = pkgs.writeText "identity-peer.py" (builtins.readFile ./identity-peer.py);
  transport = pkgs.writeText "identity-transport.py" (builtins.readFile ../identity-transport.py);
  setup = pkgs.writeText "identity-setup.py" (builtins.readFile ../identity-setup.py);
  idle = pkgs.writeShellScriptBin "identity-readiness-double" ''
    exec ${pkgs.coreutils}/bin/sleep infinity
  '';
in pkgs.testers.runNixOSTest {
  name = "phoenix-identity-peer";
  globalTimeout = 150;
  nodes.machine = { config, lib, ... }:
    let
      workspace = "/home/operator/workspace";
      descriptor = pkgs.writeText "identity-peer.json" (builtins.toJSON {
        inherit workspace setup;
        python = "${pkgs.python3}/bin/python3";
        setpriv = "${pkgs.util-linux}/bin/setpriv";
        setfacl = "${pkgs.acl}/bin/setfacl";
        admin = "${config.system.build.phoenixAdminClient}/bin/phoenix-admin";
        operatorUid = 1000;
        agentUid = config.phoenix.agent.identity.uid;
        agentGid = config.phoenix.agent.identity.gid;
      });
      served = pkgs.writeText "identity-peer-transport.json" (builtins.toJSON {
        operatorUid = 1000;
        socket = "/run/phoenix-agent/launch.sock";
        workspaces = [ workspace ];
        command = [ "${pkgs.python3}/bin/python3" "-I" (toString script) (toString descriptor) "backend" ];
        environment = { HOME = "/var/lib/phoenix-agent/home"; PATH = "/nonexistent"; };
      });
    in {
      imports = [ ../identity.nix ../broker.nix ];
      options.phoenix.agent = {
        workspaces = lib.mkOption { type = lib.types.listOf lib.types.str; default = [ workspace ]; };
        reservations.enable = lib.mkOption { type = lib.types.bool; default = false; };
      };
      config = {
        _module.args = {
          user = { name = "operator"; homeDirectory = "/home/operator"; repoDirectory = workspace; };
          phoenixAgentLauncherConfig = pkgs.writeText "unused-openshell-config.json" "{}";
          phoenixAgentPackages.gateway = idle;
        };
        virtualisation = { memorySize = 2048; cores = 2; };
        users.users.operator = { isNormalUser = true; uid = 1000; };
        # Deliberately DAC-admitted to broker: kernel UID must still deny execution.
        users.users.outsider = { isNormalUser = true; uid = 1001; extraGroups = [ "phoenix-authorization" ]; };
        phoenix.agent.identity.enable = true;
        environment.etc."identity-peer.json".source = descriptor;
        environment.systemPackages = [ pkgs.python3 pkgs.util-linux ];
        systemd.services.phoenix-agent-podman.serviceConfig.ExecStart = lib.mkForce "${idle}/bin/identity-readiness-double";
        systemd.services.phoenix-agent-gateway.serviceConfig = {
          ExecStart = lib.mkForce "${idle}/bin/identity-readiness-double";
          ExecStartPre = lib.mkForce [ ];
          ExecStartPost = lib.mkForce [ ];
        };
        # Preserve actual service identity, ProtectHome, binds, socket activation
        # and cgroup lifetime. Only post-transport backend is a fixed guest probe.
        systemd.services."phoenix-agent-launch@".serviceConfig.ExecStart = lib.mkForce
          "${pkgs.python3}/bin/python3 -I ${transport} --serve ${served}";
      };
    };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("${pkgs.python3}/bin/python3 -I ${script} /etc/identity-peer.json driver", timeout=60)
    machine.succeed("journalctl -t phoenix-admin --output=cat --no-pager > /tmp/identity-peer-audit")
    machine.succeed("grep -F '\"uid\": 980' /tmp/identity-peer-audit && grep -F '\"outcome\": \"allowed\"' /tmp/identity-peer-audit")
    machine.succeed("grep -F '\"uid\": 1000' /tmp/identity-peer-audit | grep -F '\"outcome\": \"denied\"'")
    machine.succeed("grep -F '\"uid\": 1001' /tmp/identity-peer-audit | grep -F '\"outcome\": \"denied\"'")
    machine.copy_from_vm("/tmp/identity-peer-proof.json", "evidence")
    machine.copy_from_vm("/tmp/identity-peer-audit", "evidence")
  '';
}
