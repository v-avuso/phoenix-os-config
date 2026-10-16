# Default protected Podman gate; explicit gateway mode adds real OpenShell, never model/migration.
{ pkgs, workload, mode ? "podman", runtime ? null, supervisor ? null, healthCheckInterval ? null }:
let
  lib = pkgs.lib;
  packages = import ../packages.nix { inherit pkgs; };
  script = pkgs.writeText "identity-openshell.py" (builtins.readFile ./identity-openshell.py);
  transport = pkgs.writeText "identity-transport.py" (builtins.readFile ../identity-transport.py);
  gateway = (pkgs.formats.toml {}).generate "identity-gateway.toml" {
    openshell = {
      version = 2;
      gateway = { name = "openshell"; bind_address = "127.0.0.1:17670"; health_bind_address = "127.0.0.1:17671"; compute_driver = "podman"; log_level = "info"; };
      drivers.podman = {
        socket_path = "/run/phoenix-agent/private/podman.sock";
        host_gateway_ip = "127.0.0.1"; default_image = "sha256:${workload.id}";
        image_pull_policy = "never";
        sandbox_runtime_image = "sha256:${runtime.id}";
        supervisor_image = "sha256:${supervisor.id}";
        userns = "keep-id:uid=1000,gid=1000";
        allow_driver_config = true; enable_bind_mounts = true;
        resource_admission.enabled = false; sandbox_pids_limit = 512;
      } // lib.optionalAttrs (healthCheckInterval != null) {
        # Explicit opt-in reproducer; default gateway mode matches production.
        health_check_interval_secs = healthCheckInterval;
      };
    };
  };
  policy = pkgs.writeText "identity-policy.yaml" (builtins.toJSON {
    version = 1;
    filesystem_policy = {
      include_workdir = false;
      read_only = [ "/bin" "/usr" "/etc" "/proc" "/sys" "/dev" "/nix" "/run/phoenix-admin" ];
      read_write = [ "/sandbox" "/tmp" "/dev/null" "/dev/pts" "/home/operator/workspace" ];
    };
    landlock.compatibility = "hard_requirement";
    process = { run_as_user = "1000"; run_as_group = "1000"; };
    network_policies = {};
  });
  mounts = pkgs.writeText "identity-mounts.json" (builtins.toJSON { podman.mounts = map (path: {
    type = "bind"; source = path; target = path; read_only = path != "/home/operator/workspace";
  }) [ "/home/operator/workspace" "/run/phoenix-admin" "/nix/store" ]; });
  setup = pkgs.writeText "identity-setup.py" (builtins.readFile ../identity-setup.py);
in
assert healthCheckInterval == null || (builtins.isInt healthCheckInterval && healthCheckInterval > 0);
assert builtins.elem mode [ "podman" "gateway" ];
assert mode != "gateway" || builtins.all (image:
  lib.hasPrefix "/nix/store/" (toString image.archive) && builtins.hashFile "sha256" image.archive == image.sha256
) [ runtime supervisor ];
assert mode != "gateway" || (runtime.id == "e7a78d2e2c9c7d6ffc801e429a3304b51ffd65a84692530f2bbceea11e6e1558" && runtime.sha256 == "ff175171aa978b7232ec5ca938162b95c825b8c387c42cc380d53421d8c886aa" && supervisor.id == "494b86855b51987cd68e205aa1b08d67592d4ea7b989f94c66e7179e17a97388" && supervisor.sha256 == "b77c8746e6228799e00bddb5b751f9155244c7e7f0b8f28f8eefaf936609e2c2");
assert lib.hasPrefix "/nix/store/" (toString workload.archive);
assert workload.sha256 == "b3083cbcb26bef5871ed25bc2bb519b28093db80a81500d97985d1537df6ac26";
assert workload.id == "38d1a6283d8dc515251c132471b416da81a803035b41dc2316d41805729323cd";
assert builtins.hashFile "sha256" workload.archive == workload.sha256;
pkgs.testers.runNixOSTest {
  name = "phoenix-identity-openshell-${mode}-gate";
  globalTimeout = 360;
  nodes.machine = { config, lib, ... }: {
    imports = [ ../identity.nix ] ++ lib.optional (mode == "gateway") ../broker.nix;
    options.phoenix.agent.workspaces = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "/home/operator/workspace" ];
    };
    options.phoenix.agent.reservations.enable = lib.mkOption { type = lib.types.bool; default = false; };
    config = {
      _module.args = {
        user = { name = "operator"; homeDirectory = "/home/operator"; repoDirectory = "/home/operator/workspace"; };
        phoenixAgentPackages = packages;
        phoenixAgentGatewayConfig = if mode == "gateway" then gateway else pkgs.writeText "unused-gateway-config.toml" "";
        phoenixAgentLauncherConfig = pkgs.writeText "unused-launcher-config.json" "{}";
      };
      virtualisation = { memorySize = 4096; cores = 2; diskSize = 8192; podman.enable = true; };
      users.users.operator = { isNormalUser = true; uid = 1000; };
      phoenix.agent.identity.enable = true;
      users.users.outsider = { isNormalUser = true; uid = 1001; extraGroups = lib.optional (mode == "gateway") "phoenix-authorization"; };
      environment.etc."phoenix-openshell/gateway.toml" = lib.mkIf (mode == "gateway") { source = gateway; };
      # Only Codex/history launcher semantics are replaced, not transport/service hardening.
      systemd.services = lib.optionalAttrs (mode == "gateway") {
        "phoenix-agent-launch@".serviceConfig.ExecStart = lib.mkForce
          "${pkgs.python3}/bin/python3 -I ${transport} --serve ${pkgs.writeText "identity-test-bridge.json" (builtins.toJSON {
            operatorUid = 1000; socket = "/run/phoenix-agent/launch.sock";
            workspaces = [ "/home/operator/workspace" ];
            command = [ "${pkgs.python3}/bin/python3" "-I" (toString script) "/etc/identity-openshell.json" "bridge" ];
            environment = config.systemd.services.phoenix-agent-podman.environment;
          })}";
      };
      # Representative desktop unit: real production exclusion must skip it.
      systemd.user.services.speech-dispatcher = {
        # Guest has no packaged desktop base unit; materialize this synthetic one.
        overrideStrategy = lib.mkForce "asDropinIfExists";
        wantedBy = [ "default.target" ];
        serviceConfig.ExecStart = "${pkgs.coreutils}/bin/touch /tmp/unexpected-agent-desktop";
      };
      environment.systemPackages = [ pkgs.python3 pkgs.util-linux ];
      environment.etc."identity-openshell.json".source = pkgs.writeText "identity-openshell.json" (builtins.toJSON {
        phase = if mode == "gateway" then "gateway-gate" else "podman-keepid-gate";
        inherit policy mounts healthCheckInterval;
        images = lib.optionalAttrs (mode == "gateway") {
          runtime = runtime // { archive = toString runtime.archive; };
          supervisor = supervisor // { archive = toString supervisor.archive; };
        };
        gatewayConfig = if mode == "gateway" then toString gateway else "";
        gatewayEnvironment = config.systemd.services.phoenix-agent-gateway.environment;
        cli = "${packages.cli}/bin/openshell";
        admin = if mode == "gateway" then "${config.system.build.phoenixAdminClient}/bin/phoenix-admin" else "";
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
        systemdRun = "${pkgs.systemd}/bin/systemd-run";
        systemdAnalyze = "${pkgs.systemd}/bin/systemd-analyze";
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
        machine.succeed("${pkgs.python3}/bin/python3 -I ${script} /etc/identity-openshell.json", timeout=300)
    finally:
        machine.execute("journalctl -u phoenix-agent-podman.service -u phoenix-agent-gateway.service -t phoenix-admin --no-pager > /tmp/identity-openshell-journal", timeout=10)
        machine.copy_from_vm("/tmp/identity-openshell-journal", "evidence")
        machine.copy_from_vm("/tmp/identity-openshell-evidence", "evidence")
  '';
}
