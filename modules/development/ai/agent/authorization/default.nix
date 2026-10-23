{ config, lib, pkgs, user, ... }:
let
  # A declarative account owner avoids policy -> ExecStart -> policy recursion.
  updaterName = config.phoenix.authorization.updaterUser;
  updaterUid = config.users.users.${updaterName}.uid;
  # Each automatic default is a fixed typed operation, not arbitrary root execution.
  rationale = {
    kernel-journal = "Bounded kernel journal read; no state mutation.";
    dmesg = "Bounded kernel ring-buffer read; no clear or write operation.";
    trace-summary = "Bounded summary of the fixed trace source; no state mutation.";
    trace-format = "Reads fixed trace format metadata; no tracing configuration writes.";
    service-status = "Reads status only for installed allowlisted services; cannot control units.";
    wakeup-get = "Reads wakeup state only for explicitly configured PCI devices.";
    wakeup-set = "Reversible wakeup toggle only for explicitly configured PCI devices and typed values.";
  };
  names = builtins.attrNames rationale;
  policy = pkgs.writeText "phoenix-authorization-policy.json" (builtins.toJSON {
    version = 1;
    securityReviewEnabled = config.services.phoenixDeployment.securityReview.enable;
    clientUid = if config.phoenix.agent.identity.enable then config.phoenix.agent.identity.uid else config.users.users.${user.name}.uid;
    operatorUid = config.users.users.${user.name}.uid;
    inherit updaterUid;
    target = config.phoenix.target;
    diagnostics = lib.listToAttrs (map (name: { name = "admin.${name}"; value = config.phoenix.authorization.diagnostics.${name}; }) names);
    wakeupDevices = config.phoenix.agent.wakeupDevices;
    statusServices = [ "coolercontrold.service" "clamav-daemon.service" "clamav-clamonacc.service" "opensnitchd.service" "NetworkManager.service" ];
  });
in {
  imports = [ ../security-review.nix ./commands.nix ];
  options.phoenix.authorization.updaterUser = lib.mkOption {
    type = lib.types.str;
    default = user.name;
    description = "Static account shared by the update service and its operation-specific authorization role.";
  };
  options.phoenix.authorization.automaticDiagnostics.enable = lib.mkOption {
    type = lib.types.bool;
    default = true;
    description = "Allow deterministic automatic diagnostics; disabled defaults to native human authentication and rejects explicit automatic decisions.";
  };
  options.phoenix.authorization.diagnostics = lib.mkOption {
    type = lib.types.submodule { options = lib.listToAttrs (map (name: {
      inherit name;
      value = lib.mkOption { type = lib.types.enum [ "automatic" "human" "denied" ]; default = if config.phoenix.authorization.automaticDiagnostics.enable then "automatic" else "human";
        description = "Installed authorization for ${name}. ${rationale.${name}}"; };
    }) names); };
    default = { };
    description = "Closed named diagnostic policy; deployment decisions derive from securityReview.enable.";
  };
  options.phoenix.authorization.explanation.enable = lib.mkOption {
    type = lib.types.bool;
    default = false;
    description = "Experimental native explanation before Polkit for ai-broker human requests; enable after isolated GUI acceptance.";
  };
  config.assertions = [ {
    assertion = config.phoenix.authorization.automaticDiagnostics.enable
      || builtins.all (name: config.phoenix.authorization.diagnostics.${name} != "automatic") names;
    message = "phoenix.authorization.automaticDiagnostics.enable=false forbids explicit automatic diagnostic decisions; select human or denied.";
  } ];
  config.system.build.phoenixAuthorizationPresentation = pkgs.writeText "phoenix-authorization-presentation.json"
    (builtins.toJSON (if config.phoenix.authorization.explanation.enable then {
      module = toString (pkgs.writeText "phoenix-authorization-presentation.py" (builtins.readFile ./presentation.py));
      program = "${pkgs.zenity}/bin/zenity";
    } else null));
  config.users.groups.phoenix-authorization.members = lib.unique [ user.name updaterName ];
  config.system.build.phoenixAuthorizationPolicy = policy;
  config.system.build.phoenixAuthorizationLibrary = pkgs.writeText "phoenix-authorization.py" (builtins.readFile ./request.py);
}
