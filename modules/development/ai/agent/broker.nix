{
  config,
  lib,
  pkgs,
  user,
  ...
}:
let
  cfg = config.phoenix.agent;
  admin = pkgs.writeShellScriptBin "phoenix-admin" ''
    exec ${pkgs.python3}/bin/python3 -I ${./admin.py} "$@"
  '';
  brokerConfig = pkgs.writeText "phoenix-admin.json" (
    builtins.toJSON {
      client_uid = config.users.users.${user.name}.uid;
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
    }
  );
in
{
  options.phoenix.agent.wakeupDevices = lib.mkOption {
    type = lib.types.listOf (lib.types.strMatching "[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\\.[0-7]");
    default = [ ];
    description = "Explicit xHCI PCI addresses permitted for reversible wakeup diagnostics.";
  };

  config = {
    users.users.${user.name}.uid = lib.mkDefault 1000;
    _module.args.phoenixAdminPackage = admin;
    environment.systemPackages = [ admin ];
    systemd.sockets.phoenix-admin = {
      description = "Phoenix bounded diagnostic broker";
      wantedBy = [ "sockets.target" ];
      socketConfig = {
        ListenStream = "/run/phoenix-admin/socket";
        SocketUser = user.name;
        SocketMode = "0600";
        DirectoryMode = "0755";
        RemoveOnStop = true;
      };
    };
    systemd.services.phoenix-admin = {
      description = "Phoenix bounded diagnostic broker";
      requires = [ "phoenix-admin.socket" ];
      after = [ "phoenix-admin.socket" ];
      serviceConfig = {
        ExecStart = "${admin}/bin/phoenix-admin --serve ${brokerConfig}";
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
        ReadWritePaths = map (address: "-/sys/bus/pci/devices/${address}/power/wakeup") cfg.wakeupDevices;
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
