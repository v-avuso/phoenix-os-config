{ config, lib, pkgs, user, ... }:
let
  names = [ "kernel-journal" "dmesg" "trace-summary" "trace-format" "service-status" "wakeup-get" "wakeup-set" ];
  policy = pkgs.writeText "phoenix-authorization-policy.json" (builtins.toJSON {
    version = 1;
    securityReviewEnabled = config.services.phoenixDeployment.securityReview.enable;
    clientUid = if config.phoenix.agent.identity.enable then config.phoenix.agent.identity.uid else config.users.users.${user.name}.uid;
    operatorUid = config.users.users.${user.name}.uid;
    target = if config.networking.hostName == "phoenix-vm" then "vm" else "metal";
    diagnostics = lib.listToAttrs (map (name: { name = "admin.${name}"; value = config.phoenix.authorization.diagnostics.${name}; }) names);
    wakeupDevices = config.phoenix.agent.wakeupDevices;
    statusServices = [ "coolercontrold.service" "clamav-daemon.service" "clamav-clamonacc.service" "opensnitchd.service" "NetworkManager.service" ];
  });
in {
  imports = [ ../security-review.nix ];
  options.phoenix.authorization.diagnostics = lib.mkOption {
    type = lib.types.submodule { options = lib.listToAttrs (map (name: {
      inherit name;
      value = lib.mkOption { type = lib.types.enum [ "automatic" "human" "denied" ]; default = "automatic";
        description = "Installed authorization for the bounded ${name} diagnostic."; };
    }) names); };
    default = { };
    description = "Closed named diagnostic policy; deployment decisions derive from securityReview.enable.";
  };
  config.users.groups.phoenix-authorization.members = [ user.name ];
  config.system.build.phoenixAuthorizationPolicy = policy;
  config.system.build.phoenixAuthorizationLibrary = ./request.py;
}
