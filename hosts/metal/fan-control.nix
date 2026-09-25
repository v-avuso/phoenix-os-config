{ config, lib, pkgs, ... }:

{
  options.phoenix.hardware.fanControl.nct6687dPackage = lib.mkOption {
    type = lib.types.package;
    default = config.boot.kernelPackages.nct6687d;
    defaultText = lib.literalExpression "config.boot.kernelPackages.nct6687d";
    description = ''
      Kernel-matched NCT6687D driver package. Override this together with
      boot.kernelPackages when using a different kernel package set.
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
