{
  config,
  lib,
  pkgs,
  user,
  ...
}:
let
  cfg = config.phoenix.agent.shutdownOrdering;
  containers = pkgs.writeText "phoenix-openshell-containers.conf" ''
    [containers]
    cgroups = "no-conmon"
    annotations = ["org.systemd.property.Before=['phoenix-openshell-gateway.service']"]
  '';
in
{
  options.phoenix.agent.shutdownOrdering.enable =
    lib.mkEnableOption "experimental gateway-first OpenShell shutdown ordering";
  # Deliberately opt-in until actual OpenShell workload/log-stream acceptance.
  # Keep Podman's 45-second stop deadline as the final fallback.
  config = lib.mkIf cfg.enable {
    home-manager.users.${user.name}.systemd.user.services.phoenix-openshell-podman.Service.Environment =
      [
        "CONTAINERS_CONF_OVERRIDE=${containers}"
      ];
  };
}
