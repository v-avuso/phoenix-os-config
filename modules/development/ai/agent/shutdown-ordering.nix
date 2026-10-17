{
  config,
  lib,
  pkgs,
  user,
  inputs,
  ...
}:
let
  cfg = config.phoenix.agent.shutdownOrdering;
  images = import ./shutdown/images.nix {
    inherit pkgs;
    rustOverlay = inputs.timewall.inputs.rust-overlay;
  };
  importerConfig = pkgs.writeText "phoenix-openshell-image-import.json" (builtins.toJSON {
    podman = "${pkgs.podman}/bin/podman";
    socket = "/run/user/1000/phoenix-openshell-podman.sock";
    home = user.homeDirectory;
    runtimeDirectory = "/run/user/1000";
    manifest = toString images.manifest;
  });
  containers = pkgs.writeText "phoenix-openshell-containers.conf" ''
    [containers]
    cgroups = "no-conmon"
    annotations = ["org.systemd.property.Before=['phoenix-openshell-gateway.service']"]
  '';
in
{
  options.phoenix.agent.shutdownOrdering.enable =
    lib.mkEnableOption "experimental matched OpenShell shutdown images and gateway-first ordering";
  # Atomic opt-in: images and ordering were validated together; no helper toggles.
  # Keep Podman's 45-second stop deadline as the final fallback.
  config = lib.mkIf cfg.enable {
    assertions = [ {
      assertion = !config.phoenix.agent.identity.enable;
      message = "shutdownOrdering currently supports operator identity only; protected identity needs separate service acceptance";
    } ];
    system.build.phoenixOpenShellShutdownManifest = images.manifest;
    # Addition to the same private rootless store only. No lifecycle lock here:
    # launch.py holds launch.lock while synchronously starting this service.
    # Add the importer's one 20s budget to the existing 30s gateway startup bound.
    home-manager.users.${user.name}.systemd.user.services = {
      phoenix-openshell-gateway.Service = {
        TimeoutStartSec = lib.mkForce "50s";
        ExecStartPre = lib.mkBefore [ "${pkgs.python3}/bin/python3 -I ${./shutdown/backend.py} import ${importerConfig}" ];
      };
      phoenix-openshell-podman.Service.Environment = [ "CONTAINERS_CONF_OVERRIDE=${containers}" ];
    };
  };
}
