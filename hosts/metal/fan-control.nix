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
    programs.coolercontrol.enable = true;
    systemd.services.coolercontrold.preStart = ''
      ${provisionPolicy}
    '';

    environment.systemPackages = [ pkgs.lm_sensors ];

    boot.extraModulePackages = [
      config.phoenix.hardware.fanControl.nct6687dPackage
    ];

    boot.kernelModules = [ "nct6687" ];
  };
}
