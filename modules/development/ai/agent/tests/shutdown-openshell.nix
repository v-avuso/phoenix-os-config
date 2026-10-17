# Explicit first slice: actual OpenShell ordinary stop, ordering OFF.
# Image arguments are public immutable archives plus independently verified IDs/hash.
{ pkgs, runtime, supervisor, workload, probeCreateOnly ? false, stopMode ? "ordinary", containersConfig ? null, acceptanceScope ? "full" }:
let
  lib = pkgs.lib;
  packages = import ../packages.nix { inherit pkgs; };
  images = { inherit runtime supervisor workload; };
  valid = image:
    lib.hasPrefix "/nix/store/" (toString image.archive)
    && builtins.match "[a-f0-9]{64}" image.id != null
    && builtins.hashFile "sha256" image.archive == image.sha256;
  state = "/home/fixture/.local/state/phoenix-openshell";
  gateway = (pkgs.formats.toml { }).generate "shutdown-gateway.toml" {
    openshell = {
      version = 2;
      gateway = {
        name = "openshell";
        bind_address = "127.0.0.1:17670";
        health_bind_address = "127.0.0.1:17671";
        compute_driver = "podman";
        log_level = "info";
      };
      drivers.podman = {
        socket_path = "/run/user/1000/phoenix-openshell-podman.sock";
        host_gateway_ip = "127.0.0.1";
        default_image = "sha256:${workload.id}";
        image_pull_policy = "never";
        sandbox_runtime_image = "sha256:${runtime.id}";
        supervisor_image = "sha256:${supervisor.id}";
        stop_timeout_secs = 45;
        userns = "keep-id:uid=1000,gid=1000";
        allow_driver_config = true;
        enable_bind_mounts = true;
        resource_admission.enabled = false;
        sandbox_pids_limit = 512;
      };
    };
  };
  policy = pkgs.writeText "shutdown-policy.yaml" (builtins.toJSON {
    version = 1;
    filesystem_policy = {
      include_workdir = false;
      read_only = [ "/bin" "/usr" "/etc" "/proc" "/sys" "/dev" "/nix" ];
      read_write = [ "/sandbox" "/tmp" "/dev/null" "/dev/pts" ];
    };
    landlock.compatibility = "hard_requirement";
    process = { run_as_user = "1000"; run_as_group = "1000"; };
    network_policies = { };
  });
in
assert containersConfig == null || (lib.hasPrefix "/nix/store/" (toString containersConfig) && builtins.pathExists containersConfig);
assert builtins.elem acceptanceScope [ "full" "terminal-delivery" ];
assert acceptanceScope != "terminal-delivery" || (stopMode == "ordinary" && !probeCreateOnly);
assert builtins.elem stopMode [ "ordinary" "transaction" "manager" ];
assert builtins.all valid (builtins.attrValues images);
pkgs.testers.runNixOSTest {
  name = "phoenix-shutdown-openshell";
  globalTimeout = 300;
  nodes.machine = { ... }: {
    virtualisation = {
      cores = 2;
      memorySize = 4096;
      diskSize = 8192;
      podman.enable = true;
    };
    users.users.fixture = { isNormalUser = true; uid = 1000; autoSubUidGidRange = true; };
    services.journald.extraConfig = "Storage=persistent";
    environment.systemPackages = [ packages.cli pkgs.procps pkgs.curl pkgs.util-linux pkgs.bash ];
    systemd.user.services.phoenix-openshell-podman = {
      description = "Disposable rootless OpenShell API";
      environment = lib.optionalAttrs (containersConfig != null) {
        CONTAINERS_CONF_OVERRIDE = toString containersConfig;
      };
      unitConfig.ConditionUser = "fixture";
      serviceConfig = {
        ExecStart = "${pkgs.podman}/bin/podman system service --time=0 unix:%t/phoenix-openshell-podman.sock";
        UMask = "0077";
      };
    };
    systemd.user.services.phoenix-openshell-gateway = {
      description = "Disposable OpenShell 0.1.2 gateway";
      unitConfig.ConditionUser = "fixture";
      requires = [ "phoenix-openshell-podman.service" ];
      after = [ "phoenix-openshell-podman.service" ];
      environment = {
        OPENSHELL_LOCAL_TLS_DIR = "${state}/tls";
        OPENSHELL_GATEWAY_CONFIG = toString gateway;
        XDG_STATE_HOME = state;
      };
      serviceConfig = {
        ExecStartPre = [
          "${packages.gateway}/bin/openshell-gateway config preflight"
          "${packages.gateway}/bin/openshell-gateway generate-certs --output-dir ${state}/tls --server-san 127.0.0.1 --server-san localhost --server-san host.openshell.internal"
        ];
        ExecStart = "${packages.gateway}/bin/openshell-gateway";
        ExecStartPost = "${pkgs.curl}/bin/curl --fail --silent --show-error --output /dev/null --max-time 3 --retry 5 --retry-connrefused --retry-max-time 20 http://127.0.0.1:17671/readyz";
        TimeoutStartSec = "30s";
        UMask = "0077";
      };
    };
  };
  testScript = ''
    import json
    images = json.loads("""${builtins.toJSON (builtins.mapAttrs (_: image: image // { archive = toString image.archive; }) images)}""")
    probe_create_only = ${if probeCreateOnly then "True" else "False"}
    ordering_configured = ${if containersConfig != null then "True" else "False"}
    stop_mode = "${stopMode}"
    acceptance_scope = "${acceptanceScope}"
    policy = "${policy}"
  '' + builtins.readFile ./shutdown-openshell.py;
}
