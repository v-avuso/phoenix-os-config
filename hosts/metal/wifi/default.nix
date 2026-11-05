{
  config,
  lib,
  pkgs,
  user,
  ...
}:

let
  collector = pkgs.writeShellApplication {
    name = "phoenix-wifi-diagnostics";
    runtimeInputs = [
      pkgs.python3
      pkgs.systemd
      pkgs.networkmanager
      pkgs.iw
      pkgs.iproute2
      pkgs.iputils
      pkgs.coreutils
    ];
    text = ''exec python3 ${./diagnostics.py} "$@"'';
  };
in
{
  # Experimental backport; do not silently carry it onto a different driver.
  assertions = [
    {
      assertion = config.boot.kernelPackages.kernel.version == "7.3";
      message = "Reassess the WCN7850 RX-buffer backport before changing kernel 7.3.";
    }
  ];

  # Enable observability without changing driver/firmware or graphics versions.
  boot.kernelPatches = [
    {
      name = "ath12k-wifi7-replenish-rx-buffers";
      patch = ./replenish-rx-buffers.patch;
      structuredExtraConfig = with lib.kernel; {
        ATH12K_DEBUG = yes;
        ATH12K_DEBUGFS = yes;
        ATH12K_TRACING = yes;
        ATH12K_COREDUMP = yes;
      };
    }
  ];

  users.groups.phoenix-wifi-diagnostics = { };
  users.users.${user.name}.extraGroups = [ "phoenix-wifi-diagnostics" ];
  system.build.phoenixWifiDiagnostics = collector;

  systemd.services.phoenix-wifi-diagnostics = {
    description = "Bounded WCN7850 diagnostic capture";
    wantedBy = [ "multi-user.target" ];
    after = [
      "NetworkManager.service"
    ];
    wants = [
      "NetworkManager.service"
    ];
    unitConfig.ConditionPathExists = "/sys/module/ath12k/parameters/debug_mask";
    serviceConfig = {
      Type = "simple";
      ExecStart = "${collector}/bin/phoenix-wifi-diagnostics";
      ExecStopPost = "${collector}/bin/phoenix-wifi-diagnostics cleanup";
      User = "root";
      Group = "phoenix-wifi-diagnostics";
      StateDirectory = "phoenix-wifi-diagnostics";
      StateDirectoryMode = "0750";
      RuntimeDirectory = "phoenix-wifi-diagnostics";
      RuntimeDirectoryMode = "0700";
      UMask = "0027";
      RuntimeMaxSec = "24h";
      TimeoutStopSec = "30s";
      MemoryMax = "192M";
      CPUQuota = "20%";
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      PrivateTmp = true;
      ReadWritePaths = [
        "/sys/kernel/tracing"
      ];
    };
  };
}
