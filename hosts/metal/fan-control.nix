{ config, lib, pkgs, ... }:

let
  upstreamNct6687d =
    config.boot.kernelPackages.nct6687d.overrideAttrs (_old: {
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
    # Fan curves and Windows reference channels are documented separately;
    # bind Linux channels only after bare-metal hwmon discovery.
    programs.coolercontrol.enable = true;

    environment.systemPackages = [ pkgs.lm_sensors ];

    boot.extraModulePackages = [
      config.phoenix.hardware.fanControl.nct6687dPackage
    ];

    boot.kernelModules = [ "nct6687" ];
  };
}
