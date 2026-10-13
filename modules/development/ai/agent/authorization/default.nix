{ config, lib, pkgs, user, ... }:
let
  # A declarative account owner avoids policy -> ExecStart -> policy recursion.
  updaterName = config.phoenix.authorization.updaterUser;
  updaterUid = config.users.users.${updaterName}.uid;
  names = [ "kernel-journal" "dmesg" "trace-summary" "trace-format" "service-status" "wakeup-get" "wakeup-set" ];
  policy = pkgs.writeText "phoenix-authorization-policy.json" (builtins.toJSON {
    version = 1;
    securityReviewEnabled = config.services.phoenixDeployment.securityReview.enable;
    clientUid = if config.phoenix.agent.identity.enable then config.phoenix.agent.identity.uid else config.users.users.${user.name}.uid;
    operatorUid = config.users.users.${user.name}.uid;
    inherit updaterUid;
    target = if config.networking.hostName == "phoenix-vm" then "vm" else "metal";
    diagnostics = lib.listToAttrs (map (name: { name = "admin.${name}"; value = config.phoenix.authorization.diagnostics.${name}; }) names);
    wakeupDevices = config.phoenix.agent.wakeupDevices;
    statusServices = [ "coolercontrold.service" "clamav-daemon.service" "clamav-clamonacc.service" "opensnitchd.service" "NetworkManager.service" ];
  });
in {
  imports = [ ../security-review.nix ];
  options.phoenix.authorization.updaterUser = lib.mkOption {
    type = lib.types.str;
    default = user.name;
    description = "Static account shared by the update service and its operation-specific authorization role.";
  };
  options.phoenix.authorization.diagnostics = lib.mkOption {
    type = lib.types.submodule { options = lib.listToAttrs (map (name: {
      inherit name;
      value = lib.mkOption { type = lib.types.enum [ "automatic" "human" "denied" ]; default = "automatic";
        description = "Installed authorization for the bounded ${name} diagnostic."; };
    }) names); };
    default = { };
    description = "Closed named diagnostic policy; deployment decisions derive from securityReview.enable.";
  };
  options.phoenix.authorization.explanation.enable = lib.mkOption {
    type = lib.types.bool;
    default = false;
    description = "Experimental native explanation before Polkit for ai-broker human requests; enable after isolated GUI acceptance.";
  };
  config.system.build.phoenixAuthorizationPresentation = pkgs.writeText "phoenix-authorization-presentation.json"
    (builtins.toJSON (if config.phoenix.authorization.explanation.enable then {
      module = toString (pkgs.writeText "phoenix-authorization-presentation.py" (builtins.readFile ./presentation.py));
      program = "${pkgs.zenity}/bin/zenity";
    } else null));
  config.users.groups.phoenix-authorization.members = lib.unique [ user.name updaterName ];
  config.system.build.phoenixAuthorizationPolicy = policy;
  config.system.build.phoenixAuthorizationLibrary = pkgs.writeText "phoenix-authorization.py" (builtins.readFile ./request.py);
}
