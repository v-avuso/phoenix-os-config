# Based on the fresh installation's generated snapshot, inspected 2026-10-23.
# Native identity and outstanding live-USB checks: ../storage-migration/README.md.
{ config, lib, modulesPath, ... }:
{
  imports = [ (modulesPath + "/installer/scan/not-detected.nix") ];

  boot.initrd.availableKernelModules = [ "nvme" "xhci_pci_prom21" "ahci" "xhci_pci" "usb_storage" "usbhid" "sd_mod" ];
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ "kvm-amd" ];
  boot.extraModulePackages = [ ];

  boot.initrd.luks.devices = {
    "luks-d9756988-1532-4903-b6d9-6e89735248f7".device = "/dev/disk/by-uuid/d9756988-1532-4903-b6d9-6e89735248f7";
    "luks-8c5388a9-cb79-4c29-8de1-65cf542437e1".device = "/dev/disk/by-uuid/8c5388a9-cb79-4c29-8de1-65cf542437e1";
  };

  fileSystems."/" = {
    device = "/dev/mapper/luks-d9756988-1532-4903-b6d9-6e89735248f7";
    fsType = "btrfs";
    options = [ "subvolid=5" ];
  };
  fileSystems."/home" = {
    device = "/dev/mapper/luks-d9756988-1532-4903-b6d9-6e89735248f7";
    fsType = "btrfs";
    options = [ "subvol=home" ];
  };
  fileSystems."/nix" = {
    device = "/dev/mapper/luks-d9756988-1532-4903-b6d9-6e89735248f7";
    fsType = "btrfs";
    options = [ "subvol=nix" ];
  };
  fileSystems."/boot" = {
    device = "/dev/disk/by-uuid/B4E3-63E5";
    fsType = "vfat";
    options = [ "fmask=0077" "dmask=0077" ];
  };
  swapDevices = [ { device = "/dev/mapper/luks-8c5388a9-cb79-4c29-8de1-65cf542437e1"; } ];

  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
  hardware.cpu.amd.updateMicrocode = lib.mkDefault config.hardware.enableRedistributableFirmware;
}
