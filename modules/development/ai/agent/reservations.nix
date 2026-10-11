{ config, lib, pkgs, user, ... }:
let
  cfg = config.phoenix.agent.reservations;
  mapping = builtins.listToAttrs (map (name: { name = "deployment.${name}"; value = "system-testing"; })
    [ "test" "switch" "boot" "update" "override" "rollback" ]);
  settings = {
    engine = toString ./reservations.py;
    adapter = toString ./reservation-client.py;
    state = "/var/lib/phoenix-reservations";
    socket = "/run/phoenix-admin/socket";
    operator_uid = config.users.users.${user.name}.uid;
    inherit (cfg) mapping;
    bounds = {
      lease_seconds = cfg.leaseSeconds;
      max_renew = cfg.maxRenewSeconds;
      max_total = cfg.maxTotalSeconds;
      wait_seconds = cfg.waitSeconds;
      ticket_live = cfg.ticketLiveSeconds;
      queue_limit = cfg.queueLimit;
      uid_queue_limit = cfg.uidQueueLimit;
    };
  };
  helperConfig = pkgs.writeText "phoenix-reservation-operator.json" (builtins.toJSON settings);
  helper = pkgs.writeShellScript "phoenix-reservation-operator" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./reservation-client.py} ${helperConfig} --authenticated-helper
  '';
  recoveryHelper = pkgs.writeShellScript "phoenix-reservation-recovery" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${./reservation-client.py} ${helperConfig} --authenticated-recovery
  '';
  clientConfig = pkgs.writeText "phoenix-reservation-client.json" (builtins.toJSON (settings // {
    helper = toString helper;
    recovery_helper = toString recoveryHelper;
    pkexec = "/run/wrappers/bin/pkexec";
  }));
  client = pkgs.writeShellScriptBin "phoenix-reservation" ''
    exec ${pkgs.python3}/bin/python3 -I ${./reservation-client.py} ${clientConfig} "$@"
  '';
  bounded = default: maximum: lib.mkOption {
    type = lib.types.ints.between 1 maximum;
    inherit default;
  };
in {
  options.phoenix.agent.reservations = {
    enable = lib.mkEnableOption "experimental exclusive testing reservations and deployment enforcement";
    mapping = lib.mkOption {
      type = lib.types.attrsOf (lib.types.strMatching "[a-z][a-z0-9-]{0,127}");
      default = mapping;
      description = "Exact qualified semantic command to resource mapping; never executable dispatch.";
    };
    leaseSeconds = bounded 900 900;
    maxRenewSeconds = bounded 3600 3600;
    maxTotalSeconds = bounded 14400 14400;
    waitSeconds = bounded 3600 3600;
    ticketLiveSeconds = bounded 30 30;
    queueLimit = bounded 64 256;
    uidQueueLimit = bounded 4 16;
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = lib.all (name: (cfg.mapping.${"deployment.${name}"} or null) == (cfg.mapping."deployment.test" or ""))
          [ "switch" "boot" "update" "override" "rollback" ] && builtins.hasAttr "deployment.test" cfg.mapping;
        message = "Deployment, rollback and override must share the configured testing resource."; }

      { assertion = cfg.mapping != {} && builtins.length (builtins.attrNames cfg.mapping) <= 64 &&
          lib.all (name: builtins.match "[a-z][a-z0-9-]*\\.[a-z][a-z0-9-]*" name != null) (builtins.attrNames cfg.mapping);
        message = "Reservations require 1..64 exact qualified semantic commands."; }
      { assertion = builtins.hasAttr "phoenix-agent/activated-source" config.environment.etc;
        message = "Reservation management requires deployment activated-source provenance."; }
      { assertion = cfg.ticketLiveSeconds >= 25;
        message = "Reservation ticket liveness must cover the existing broker diagnostic and polling margin (25..30 seconds)."; }
    ];
    _module.args.phoenixReservationSettings = settings;
    environment.systemPackages = [ client ];
    systemd.tmpfiles.rules = [ "d /var/lib/phoenix-reservations 0700 root root -" ];
    environment.etc."polkit-1/actions/org.phoenix.reservation.policy".text = ''
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
      <policyconfig>
        <action id="org.phoenix.reservation.manage">
          <description>Manage Phoenix testing reservations</description>
          <message>Authenticate this bounded Phoenix reservation management operation.</message>
          <icon_name>dialog-warning</icon_name>
          <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
          <annotate key="org.freedesktop.policykit.exec.path">${helper}</annotate>
        </action>
        <action id="org.phoenix.reservation.recover">
          <description>Force recovery of a Phoenix testing reservation</description>
          <message>CRITICAL: Revoke the selected reservation owner generation and its queue. Verify the generation and reason hash displayed by the native client. This does not stop running work or roll back the system.</message>
          <icon_name>dialog-warning</icon_name>
          <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
          <annotate key="org.freedesktop.policykit.exec.path">${recoveryHelper}</annotate>
        </action>
      </policyconfig>
    '';
  };
}
