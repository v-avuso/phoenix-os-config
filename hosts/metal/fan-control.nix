{
  config,
  lib,
  pkgs,
  ...
}:

let
  coolerControlPolicy = {
    version = 1;
    nctDeviceName = "nct6687";
    channels = {
      fan1 = "CPU Fan";
      fan2 = "Pump Fan";
      fan3 = "System Fan #1";
      fan4 = "System Fan #2";
      fan5 = "System Fan #3";
      fan6 = "System Fan #4";
      fan7 = "System Fan #5";
      fan8 = "System Fan #6";
    };
    cpuDeviceName = "AMD Ryzen 9 9950X3D 16-Core Processor";
    cpuTempName = "temp1";
    gpuDeviceName = "NVIDIA GeForce RTX 5090";
    gpuTempName = "GPU Temp";
    function = {
      uid = "phoenix-case-standard-v1";
      name = "Phoenix case fan response";
      response_delay = 1;
      deviance = 2.0;
      threshold_hopping = true;
    };
    profiles = [
      {
        uid = "phoenix-case-cpu-v1";
        name = "Phoenix CPU case staircase";
        p_type = "Graph";
        temp_source = "cpu";
        speed_profile = [
          [
            20.0
            20
          ]
          [
            69.9
            20
          ]
          [
            70.2
            50
          ]
          [
            85.0
            50
          ]
          [
            85.1
            81
          ]
          [
            120.0
            81
          ]
        ];
      }
      {
        uid = "phoenix-case-gpu-v1";
        name = "Phoenix GPU case staircase";
        p_type = "Graph";
        temp_source = "gpu";
        speed_profile = [
          [
            20.0
            20
          ]
          [
            60.0
            20
          ]
          [
            60.1
            40
          ]
          [
            70.0
            40
          ]
          [
            70.1
            60
          ]
          [
            80.0
            60
          ]
          [
            80.1
            80
          ]
          [
            120.0
            80
          ]
        ];
      }
      {
        uid = "phoenix-case-maximum-v1";
        name = "Phoenix CPU/GPU maximum";
        p_type = "Mix";
        member_profile_uids = [
          "phoenix-case-cpu-v1"
          "phoenix-case-gpu-v1"
        ];
        mix_function_type = "Max";
      }
      {
        uid = "phoenix-pump-fixed-v1";
        name = "Phoenix pump fixed 80%";
        p_type = "Fixed";
        speed_fixed = 80;
      }
      {
        uid = "phoenix-bottom-stopped-v1";
        name = "Phoenix bottom fan stopped temporarily";
        p_type = "Fixed";
        speed_fixed = 0;
      }
    ];
    assignments = {
      fan1 = "phoenix-case-maximum-v1";
      fan2 = "phoenix-pump-fixed-v1";
      fan3 = "phoenix-case-maximum-v1";
      fan4 = "phoenix-case-maximum-v1";
      fan5 = "phoenix-case-maximum-v1";
      fan6 = "phoenix-bottom-stopped-v1";
    };
  };
  # nixos-26.05 still packages 4.3.0 and nixpkgs-unstable has moved to 5.x.
  # Reuse the locked nixpkgs build recipes and pin only CoolerControl's 4.3.1
  # source/dependency hashes, keeping the rest of the system inputs unchanged.
  coolerControl431Overlay =
    final: prev:
    let
      version = "4.3.1";
      src = final.fetchFromGitLab {
        owner = "coolercontrol";
        repo = "coolercontrol";
        tag = version;
        hash = "sha256-nFlaiQtc4r3FBmdhErUAucG3SQ1GWQX9ClnZXGVWjbc=";
      };
      packageRoot = prev.path + "/pkgs/applications/system/coolercontrol";
      meta = prev.coolercontrol.coolercontrold.meta // {
        description = "Monitor and control your cooling devices";
      };
      # These hashes are consumed while the Nixpkgs build functions are
      # evaluated, so replace the 4.3.0 literals before calling those functions.
      uiPackage = builtins.toFile "coolercontrol-ui-data-4.3.1.nix" (
        builtins.replaceStrings
          [ "sha256-fWsksBQCwHHWYE82NG0Vf/f+Hk02YMCUaGMHFGhGx2U=" ]
          [ "sha256-zolbx5ROiFzNhPGcOnJjEiY3W2IXI24wLKPj3wRSLXU=" ]
          (builtins.readFile (packageRoot + "/coolercontrol-ui-data.nix"))
      );
      daemonPackage = builtins.toFile "coolercontrold-4.3.1.nix" (
        builtins.replaceStrings
          [ "sha256-f0SsTwriUo2rD97L+Z/bq7UahOSLjYjH8bbXg/Hx5qE=" ]
          [ "sha256-DE1m/odw90epyR8U9H1pxyJXariIHLXwk+mVYi8cu5A=" ]
          (builtins.readFile (packageRoot + "/coolercontrold.nix"))
      );
      packages = rec {
        coolercontrol-ui-data = (final.callPackage uiPackage { }) {
          inherit version src meta;
        };
        coolercontrold =
          (final.callPackage daemonPackage {
            coolercontrol = packages;
          })
            {
              inherit version src meta;
            };
        coolercontrol-gui = (final.callPackage (packageRoot + "/coolercontrol-gui.nix") { }) {
          inherit version src meta;
        };
      };
    in
    {
      coolercontrol = packages;
    };

  policyFile = pkgs.writeText "phoenix-coolercontrol-policy.json" (
    builtins.toJSON coolerControlPolicy
  );
  policyPython = pkgs.python3.withPackages (pythonPackages: [ pythonPackages.tomlkit ]);
  provisionPolicy = pkgs.writeShellScript "phoenix-coolercontrol-policy" ''
    exec ${policyPython}/bin/python3 ${./coolercontrol-policy.py} \
      --policy ${policyFile} \
      --config /etc/coolercontrol/config.toml \
      --sysfs-root /sys/class/hwmon \
      --nvidia-smi ${config.hardware.nvidia.package.bin}/bin/nvidia-smi
  '';
  watchdogKeeper = pkgs.writeShellScript "phoenix-nct6687-watchdog" ''
    exec ${pkgs.python3}/bin/python3 ${./nct6687-watchdog.py} \
      --sysfs-root /sys/class/hwmon
  '';

  watchdogSleepPrepare = pkgs.writeShellScript "phoenix-nct6687-watchdog-sleep-prepare" ''
    exec ${pkgs.python3}/bin/python3 ${./nct6687-watchdog.py} \
      --sysfs-root /sys/class/hwmon \
      --prepare-sleep
  '';

  upstreamNct6687d = config.boot.kernelPackages.nct6687d.overrideAttrs (_old: {
    version = "0-unstable-2026-09-03";
    src = pkgs.fetchFromGitHub {
      owner = "Fred78290";
      repo = "nct6687d";
      rev = "33d7bde2fcd7fd922baebadd30337b8d58b8ee7b";
      hash = "sha256-pqH62197Vkf5/DI0QgVJO6DAcrT2uzs+RrCD+vC/pUg=";
    };
  });
in
{
  options.phoenix.hardware.fanControl.nct6687dPackage = lib.mkOption {
    type = lib.types.package;
    default = upstreamNct6687d;
    description = ''
      Kernel-matched NCT6687D driver at a pinned upstream revision with
      Linux 7.2 compatibility fixes.
    '';
  };

  config = {
    # The reconciler verifies the live device UID and fan labels before changing
    # the mutable CoolerControl config; coolercontrold applies settings on boot.
    nixpkgs.overlays = [ coolerControl431Overlay ];
    programs.coolercontrol.enable = true;
    systemd.services.coolercontrold.preStart = ''
      ${provisionPolicy}
    '';

    # A running daemon does not reread its mutable config when NixOS activation
    # changes it. Reconcile in coolercontrold.preStart, then restart only at a
    # system switch/test so the declared baseline is reapplied without tying
    # cooling to desktop-session lifecycle or continuously overwriting UI edits.
    system.activationScripts.phoenixCoolerControlBaseline = {
      deps = [ "etc" ];
      text = ''
        case "''${NIXOS_ACTION:-}" in
          switch|test)
            ${pkgs.systemd}/bin/systemctl daemon-reload
            if ${pkgs.systemd}/bin/systemctl is-active --quiet coolercontrold.service; then
              ${pkgs.systemd}/bin/systemctl stop phoenix-nct6687-watchdog.service
              ${pkgs.systemd}/bin/systemctl restart coolercontrold.service
              ${pkgs.systemd}/bin/systemctl start phoenix-nct6687-watchdog.service
            fi
            ;;
        esac
      '';
    };

    boot.blacklistedKernelModules = [ "nct6683" ];
    boot.extraModprobeConfig = ''
      options nct6687 msi_fan_brute_force=1
    '';

    # Require a verified firmware fallback before any sleep action. On the
    # return path ExecStop queues the keeper without blocking CoolerControl's
    # logind wake notification; the keeper waits for live profiles before arming.
    systemd.services.phoenix-nct6687-sleep = {
      description = "Restore NCT6687 firmware fan control around system sleep";
      requiredBy = [ "sleep.target" ];
      before = [ "sleep.target" ];
      partOf = [ "sleep.target" ];
      path = [ pkgs.systemd ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${watchdogSleepPrepare}";
        ExecStop = "${pkgs.systemd}/bin/systemctl --no-block start phoenix-nct6687-watchdog.service";
      };
    };

    systemd.services.phoenix-nct6687-watchdog = {
      description = "Refresh the NCT6687D MSI fan-control safety lease";
      wantedBy = [ "multi-user.target" ];
      # Run independently as the recovery supervisor. It stops renewing on a
      # failure, confirms firmware fallback, then restarts CoolerControl so
      # apply_on_boot reclaims channels before a new lease is issued.
      after = [ "coolercontrold.service" ];
      path = [ pkgs.systemd ];
      serviceConfig = {
        Type = "simple";
        User = "root";
        ExecStart = "${watchdogKeeper}";
        Restart = "no";
      };
    };

    environment.systemPackages = [ pkgs.lm_sensors ];

    boot.extraModulePackages = [
      config.phoenix.hardware.fanControl.nct6687dPackage
    ];

    boot.kernelModules = [ "nct6687" ];
  };
}
