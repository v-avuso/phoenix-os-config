{
  config,
  lib,
  pkgs,
  user,
  phoenixReservationSettings ? null,
  ...
}:
let
  cfg = config.phoenix.agent;
  authorizationPolicy = toString config.system.build.phoenixAuthorizationPolicy;
  substitutions = {
    reservationAdapter = toString ./reservation-client.py;
    authorizationLibrary = toString config.system.build.phoenixAuthorizationLibrary;
  };
  operatorScript = pkgs.replaceVars ./admin.py (substitutions // { authorizationClientConfig = ""; });
  adminScript = pkgs.replaceVars ./admin.py (substitutions // { authorizationClientConfig = toString clientConfig; });
  admin = pkgs.writeShellScriptBin "phoenix-admin" ''
    exec ${pkgs.python3}/bin/python3 -I ${adminScript} "$@"
  '';
  diagnosticHelper = pkgs.writeShellScript "phoenix-diagnostic-authorize" ''
    if [ "$#" -ne 0 ]; then exit 2; fi
    exec ${pkgs.python3}/bin/python3 -I ${operatorScript} --operator ${brokerConfig}
  '';
  clientConfig = pkgs.writeText "phoenix-authorization-client.json" (builtins.toJSON {
    inherit authorizationPolicy;
    operatorCommand = [ "/run/wrappers/bin/pkexec" "--disable-internal-agent" (toString diagnosticHelper) ];
  });
  brokerConfig = pkgs.writeText "phoenix-admin.json" (
    builtins.toJSON ({
      inherit authorizationPolicy;
      client_uid = if cfg.identity.enable then cfg.identity.uid else config.users.users.${user.name}.uid;
      wakeup_devices = cfg.wakeupDevices;
      status_services = [
        "coolercontrold.service"
        "clamav-daemon.service"
        "clamav-clamonacc.service"
        "opensnitchd.service"
        "NetworkManager.service"
      ];
      journalctl = "${pkgs.systemd}/bin/journalctl";
      systemctl = "${pkgs.systemd}/bin/systemctl";
      dmesg = "${pkgs.util-linux}/bin/dmesg";
    } // lib.optionalAttrs cfg.reservations.enable { reservations = phoenixReservationSettings; })
  );
in
{
  imports = [ ./authorization ];
  options.phoenix.agent.wakeupDevices = lib.mkOption {
    type = lib.types.listOf (lib.types.strMatching "[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\\.[0-7]");
    default = [ ];
    description = "Explicit xHCI PCI addresses permitted for reversible wakeup diagnostics.";
  };

  config = {
    users.users.${user.name}.uid = lib.mkDefault 1000;
    _module.args.phoenixAdminPackage = admin;
    system.build.phoenixAdminClient = admin;
    environment.systemPackages = [ admin ];
    environment.etc."polkit-1/actions/org.phoenix.diagnostic.policy".text = ''
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN" "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
      <policyconfig><action id="org.phoenix.diagnostic.authorize">
        <description>Authorize a bounded Phoenix diagnostic</description>
        <message>Phoenix requests one installed diagnostic. Read the operation and reason in the terminal before authenticating.</message>
        <icon_name>dialog-information</icon_name>
        <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>auth_admin</allow_active></defaults>
        <annotate key="org.freedesktop.policykit.exec.path">${diagnosticHelper}</annotate>
      </action></policyconfig>
    '';
    systemd.sockets.phoenix-admin = {
      description = "Phoenix bounded diagnostic broker";
      wantedBy = [ "sockets.target" ];
      socketConfig = {
        ListenStream = "/run/phoenix-admin/socket";
        SocketUser = if cfg.identity.enable then "phoenix-agent" else user.name;
        SocketMode = "0660";
        SocketGroup = "phoenix-authorization";
        DirectoryMode = "0755";
        RemoveOnStop = true;
      };
    };
    systemd.services.phoenix-admin = {
      description = "Phoenix bounded diagnostic broker";
      requires = [ "phoenix-admin.socket" ];
      after = [ "phoenix-admin.socket" ];
      serviceConfig = {
        ExecStart = "${pkgs.python3}/bin/python3 -I ${operatorScript} --serve ${brokerConfig}";
        Restart = "on-failure";
        User = "root";
        Group = "root";
        UMask = "0077";
        NoNewPrivileges = true;
        CapabilityBoundingSet = [ "CAP_SYSLOG" ];
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        PrivateDevices = true;
        ProtectKernelTunables = true;
        ReadWritePaths = map (address: "-/sys/bus/pci/devices/${address}/power/wakeup") cfg.wakeupDevices
          ++ lib.optionals cfg.reservations.enable [ "/var/lib/phoenix-reservations" ];
        ProtectKernelModules = true;
        ProtectKernelLogs = false; # dmesg is an intentional read capability.
        ProtectControlGroups = true;
        ProtectClock = true;
        ProtectHostname = true;
        ProtectProc = "invisible";
        RestrictAddressFamilies = [ "AF_UNIX" ];
        RestrictNamespaces = true;
        RestrictSUIDSGID = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        SystemCallArchitectures = "native";
        SystemCallFilter = [
          "@system-service"
          "syslog"
          "~@mount"
          "~@reboot"
          "~@module"
        ];
        MemoryMax = "128M";
        TasksMax = 16;
      };
    };
  };
}
